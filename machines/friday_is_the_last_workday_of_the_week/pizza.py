"""The pizza payment program"""

from __future__ import print_function
import sys
import time
from functools import partial
from datetime import datetime
import MySQLdb
from PyQt4 import QtGui, QtCore, uic
import credentials

__version__ = '0.1'
PizzaApp = uic.loadUiType("pizza.ui")[0]  # pylint: disable=invalid-name


class PizzaGUI(QtGui.QMainWindow, PizzaApp):
    """The pizza app main class"""

    def __init__(self, parent=None):
        """Initialize the Pizza GUI"""
        self.pizza_core = PizzaCore()

        # Init GUI
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.setWindowTitle('Pizza Payment System version ' + __version__)
        self.text_history.setReadOnly(True)

        # Bind buttons
        self.btn_login.clicked.connect(self.login)
        self.btn_logout.clicked.connect(self.logout)
        self.btn_deposite.clicked.connect(
            partial(self.transaction, 'deposite')
        )
        self.btn_withdraw.clicked.connect(
            partial(self.transaction, 'withdraw')
        )

        # widgets that are supposed to be active of inactive when logged in
        self.active_on_logged_in = (
            'btn_deposite', 'btn_withdraw', 'btn_logout',
            'label_amount', 'label_history', 'label_balance',
            'spinbox_amount',
        )
        self.inactive_on_logged_in = (
            'label_enter_username', 'lineedit_username', 'btn_login',
        )

        # First time setup
        self.set_logged_in(False)
        self.text_history.setPlainText('')
        self.text_history.appendHtml(self.pizza_core.format_todays_status())

        # Setup timeout updater
        self.timeout = 20
        self.login_time = None
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.monitor_timeout)
        self.spinbox_amount.valueChanged.connect(self.report_active)

    def keyPressEvent(self, event):  # pylint: disable=invalid-name
        """Keypress callback method"""
        if event.key() == QtCore.Qt.Key_Return and self.lineedit_username.hasFocus():
            self.login()

    def set_logged_in(self, logged_in):
        """Set the GUI active or inactive depending on logged in status

        Args:
            logged_in (bool): Inidcates whether a user is logged is
        """
        for widget in self.active_on_logged_in:
            getattr(self, widget).setEnabled(logged_in)

        for widget in self.inactive_on_logged_in:
            getattr(self, widget).setEnabled(not logged_in)

    def login(self):
        """Login"""
        username = self.lineedit_username.text()
        try:
            self.pizza_core.login(username)
        except InvalidUsername:
            print('Invalid username')  # Raise info box
            self.show_dialog(
                'Invalid username',
                'The username {} is unknown to the pizza payment system\n\n'\
                'Please ask you pizza payment service provider for help and '\
                'try again'.format(username),
                type_='warning')
            return

        self.set_logged_in(True)
        self.lineedit_username.setText('')
        self.update_balance_and_history()
        self.login_time = time.time()
        self.timer.start(100)

    def logout(self):
        """Logout"""
        self.timer.stop()
        self.login_time = None
        self.lcd_timeout.display(0)
        self.pizza_core.logout()
        self.text_history.setPlainText('')
        self.text_history.appendHtml(self.pizza_core.format_todays_status())
        self.set_balance(0)
        self.spinbox_amount.setValue(0)
        self.set_logged_in(False)
        self.lineedit_username.setFocus(True)

    def transaction(self, transaction_type):
        """Deposite"""
        print('Transaction of type', transaction_type)
        self.report_active()
        amount = self.spinbox_amount.value()
        if amount <= 0:
            self.show_dialog(
                'Bad amount',
                'Always use positive numbers in the amount. Choosing between '\
                'the "Desposite" or "Withdraw" button will determine the sign!'
            )
            return

        if transaction_type == 'withdraw' and \
           amount > self.pizza_core.get_balance():
            self.show_dialog('Insufficient funds', 'Get a job!',
                             type_='warning')
            return

        try:
            success = self.pizza_core.add_transaction(
                amount,
                transaction_type=transaction_type,
            )
        except ValueError:
            success = False

        if success:
            self.spinbox_amount.setValue(0)
            self.update_balance_and_history()
            if transaction_type == 'deposite':
                body = 'You have successfully deposited money'
            else:
                body = 'You have successfully paid for your pizza'
            self.show_dialog('Transaction successful', body)
        else:
            self.show_dialog('Transaction NOT completed',
                             'Something went wrong with your payment, '\
                             'too bad!',
                             type_='warning')
        self.report_active()

    def update_balance_and_history(self):
        """Updates the history window"""
        self.set_balance(self.pizza_core.get_balance())

        text = ['Welcome {}\n\nPlease make a deposite or withdrawal!\n\n'\
                'Transaction history:'.format(self.pizza_core.real_name)]
        for transaction in self.pizza_core.get_history():
            # A transaction is (unixtime, amount)
            unixtime, amount = transaction

            if amount > 0:
                action = 'deposite'
            else:
                action = 'withdraw'

            timestamp = datetime.fromtimestamp(
                unixtime
            ).strftime('%Y-%m-%d %H:%M:%S')

            text.append(
                '{} -- {}: {}'.format(timestamp, action, amount)
            )

        self.text_history.setPlainText('\n'.join(text))

    def show_dialog(self, title, string, type_='information'):
        """Show a dialog"""
        getattr(QtGui.QMessageBox, type_)(self, title, string)

    def set_balance(self, amount=0):
        """Sets the balance label text"""
        self.label_balance.setText(
            '<html><head/><body><p><span style=" font-size:20pt;">'\
            'Balance: {} DKK</span></p></body></html>'.format(amount)
        )

    def monitor_timeout(self):
        """Monitor the timeout and update the timeout indicator"""
        delta = time.time() - self.login_time
        if delta > self.timeout:
            self.logout()
        self.lcd_timeout.display(int(round(self.timeout - delta, 0)))

    def report_active(self, _=None):
        """Reset the logintime on activity"""
        self.login_time = time.time()


def requires_db(function):
    """Requires db decorator"""

    def inner_function(self, *args, **kwargs):
        """Inner function"""
        now = time.time()

        # Only do the connection check, if it has been more than an
        # hour since the last query
        if now - self.last_query > 3600:
            print("Staying alive")
            try:
                self.cursor.execute("SELECT * FROM pizza_transactions limit 1")
            except self.dbmodule.Error:
                self.init_db()

        self.last_query = now
        return function(self, *args, **kwargs)

    return inner_function


class PizzaCore(object):
    """The core of the pizza app (including db communication)"""

    def __init__(self, dbmodule=MySQLdb):
        """Initialize the pizza core"""
        self.dbmodule = dbmodule
        self.user = None
        self.real_name = None

        # Init db connection
        self.last_query = 0
        self.cursor = None
        self.init_db()

    def init_db(self):
        """Init the database connection"""
        connection = self.dbmodule.connect(
            host='servcinf-sql',
            user=credentials.USERNAME,
            passwd=credentials.PASSWORD,
            db='cinfdata',
            #autocommit=True,
        )
        connection.autocommit(True)
        self.cursor = connection.cursor()

    @requires_db
    def login(self, username):
        """Log a user in

        Args:
            username (str): The user to log in

        Raises:
            InvalidUsername: If the username does not exist
        """
        query = 'SELECT user_barcode, name FROM fridays_user '\
                'WHERE user_barcode=%s'
        self.cursor.execute(query, (username))
        result = self.cursor.fetchall()
        if len(result) != 1:
            message = 'There is not exactly 1 user with username {}'
            raise InvalidUsername(message.format(username))

        self.user, self.real_name = result[0]

    def logout(self):
        """Log the current user out"""
        self.user = None
        self.real_name = None

    def get_history(self, number_of_transactions=10):
        """Return the users history"""
        query = 'SELECT UNIX_TIMESTAMP(time), amount FROM pizza_transactions '\
                'WHERE user_id=%s ORDER BY time desc LIMIT %s'
        self.cursor.execute(query, (self.user, number_of_transactions))
        return self.cursor.fetchall()

    def get_balance(self):
        """Return the current users balance"""
        query = 'select sum(amount) from pizza_transactions where user_id=%s'
        self.cursor.execute(query, (self.user,))
        result = self.cursor.fetchall()
        balance = result[0][0]
        if balance is None:
            balance = 0.0
        return balance

    def add_transaction(self, amount, transaction_type):
        """Add a transaction

        Args:
            mount (float): The amount of the transaction
            transaction_type (str): Either 'deposite' or 'withdraw'

        Return:
            bool: Whether adding the tranaction succeeded

        Raises:
            ValueError: If the amount is not positive or the transaction_type
                is unknown
        """
        if not transaction_type in ['deposite', 'withdraw']:
            message = 'transaction_type must be "deposite" or "withdraw"'
            raise ValueError(message)

        if transaction_type == 'withdraw':
            amount = amount * -1

        query = 'INSERT INTO pizza_transactions (user_id, amount) '\
                'values (%s, %s)'
        try:
            self.cursor.execute(query, (self.user, amount))
            return True
        except self.dbmodule.Error:
            return False

    def format_todays_status(self):
        """Get the transactions of the day"""
        status = '<h1> Ready to log in </h1>'

        status += '<br><h1>Pizza box status</h1>'

        # Add sum of all time
        self.cursor.execute(
            'SELECT sum(amount) FROM pizza_transactions WHERE user_id!="test"'
        )
        all_time_sum = self.cursor.fetchone()[0]
        status += '<p>All time sum (money box balance): <b>{}</b></p>'.format(all_time_sum)
        status += '<br><h2>Todays transactions:</h2>'
        status += '<pre>'
        self.cursor.execute(
            'SELECT * FROM pizza_transactions '
            'WHERE date(time) = date(now()) ORDER BY TIME DESC'
        )
        for transaction in self.cursor.fetchall():
            # A status looks like:
            # (297L, 'kenni', datetime.datetime(2015, 11, 20, 8, 56, 17), -50.0)

            timestamp = transaction[2]
            if timestamp.hour >= 11 and transaction[3] < 0:
                status += 'Uh oh ---> {2:%H:%M:%S}  {1: <10} '\
                          '{3: >7.2f}\n'.format(*transaction)
            else:
                status += '           {2:%H:%M:%S}  {1: <10} '\
                          '{3: >7.2f}\n'.format(*transaction)


        self.cursor.execute(
            'SELECT sum(amount) FROM pizza_transactions WHERE date(time) = date(now())'
        )
        todays_sum = self.cursor.fetchone()[0]
        if todays_sum is None:
            todays_sum = 0
        status += '\nTodays sum....................: '\
                  '{: >7.2f}\n'.format(todays_sum)
        status += '</pre>'

        return status


class InvalidUsername(Exception):
    """Exception used when attempting to log an invalid user in"""


def main():
    """Main function"""
    app = QtGui.QApplication(sys.argv)
    my_window = PizzaGUI(None)
    my_window.show()
    app.exec_()


def test():
    """Test function"""
    core = PizzaCore()
    core.format_todays_status()


if __name__ == '__main__':
    #test()
    main()
