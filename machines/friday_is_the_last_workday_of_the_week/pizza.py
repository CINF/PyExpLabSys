"""The pizza payment program"""

from __future__ import print_function
import sys
from functools import partial
from datetime import datetime
import MySQLdb
from PyQt4 import QtGui, uic  # QtCore
import credentials


PizzaApp = uic.loadUiType("pizza.ui")[0]  # pylint: disable=invalid-name


class PizzaGUI(QtGui.QMainWindow, PizzaApp):
    """The pizza app main class"""

    def __init__(self, parent=None):
        """Initialize the Pizza GUI"""
        self.pizza_core = PizzaCore()

        # Init GUI
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)
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

        # First time setup
        self.set_enabled(False)
        self.greeting = 'Please log in'
        self.text_history.setPlainText(self.greeting)

    def set_enabled(self, enabled):
        """Set the user part of the GUI inactive"""
        self.text_history.setEnabled(enabled)
        self.spinbox_amount.setEnabled(enabled)
        self.label_amount.setEnabled(enabled)
        self.btn_deposite.setEnabled(enabled)
        self.btn_withdraw.setEnabled(enabled)
        self.label_history.setEnabled(enabled)
        self.label_balance.setEnabled(enabled)

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

        self.set_enabled(True)
        self.lineedit_username.setText('')
        self.update_balance_and_history()

    def logout(self):
        """Logout"""
        self.pizza_core.logout()
        self.text_history.setPlainText(self.greeting)
        self.label_balance.setText('Balance: 0 DKK')
        self.spinbox_amount.setValue(0)
        self.set_enabled(False)

    def transaction(self, transaction_type):
        """Deposite"""
        print('Transaction of type', transaction_type)
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

    def update_balance_and_history(self):
        """Updates the history window"""
        self.label_balance.setText(
            'Balance: {:.0f} DKK'.format(self.pizza_core.get_balance())
        )

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


class PizzaCore(object):
    """The core of the pizza app (including db communication)"""

    def __init__(self, dbmodule=MySQLdb):
        """Initialize the pizza core"""
        self.dbmodule = dbmodule
        self.user = None
        self.real_name = None
        connection = dbmodule.connect(
            host='servcinf',
            user=credentials.USERNAME,
            passwd=credentials.PASSWORD,
            db='cinfdata',
            #autocommit=True,
        )
        connection.autocommit(True)
        self.cursor = connection.cursor()

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
    print(core.login('kenni'))


if __name__ == '__main__':
    #test()
    main()
