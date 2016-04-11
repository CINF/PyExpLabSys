# -*- coding: utf-8 -*-
# pylint: disable=too-many-arguments

"""The bar database module"""

try:
    import MySQLdb
except ImportError:
    import pymysql as MySQLdb
import time


class BarDatabase(object):
    """Class for comunicating with database

    NOTE: The underlying database connection is made aware of the database string encoding
    of utf8 but does not convert to unicode, it lets the utf8 encoded strings through.

    """
    def __init__(self, host='servcinf-sql', port=3306, use_unicode=False):
        self.connection = MySQLdb.connect(host=host, user='fridays',
                                          passwd='fridays', db='cinfdata',
                                          port=port, charset='utf8',
                                          use_unicode=use_unicode)
        self.connection.autocommit(True)
        self.cursor = self.connection.cursor()

    def insert_item(self, barcode, price, name, alc, volume=None,
                    energy_content=None, beer_description=None, brewery=None):
        """ cursor insert statement with data
        args:
            barcode (int): Barcode of item ( mostly beer or wine)
            price (int): Price of item in DKK. Always in positive
                intigers, most often rounded up to nearest 5
            name (str): Name of beer
            alc (float): alcohol percentage in vol. %
            volume (float): Beer volume in liters
            energy_content (float): Energy content pr. 100 g in kJ
            beer_description (str): Desciption of beer. Be creative!
            brewery (str): Name the brewery.
        """
        values = (barcode, price, name, alc, volume, energy_content,
                  beer_description, brewery, None, True)
        with self.connection:
            self.cursor.execute("INSERT INTO fridays_items "
                                "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                values)

    def replace_item(self, barcode, field, value):
        """cursor replace one or more statements with data"""
        print field, value
        with self.connection:
            query = "UPDATE fridays_items SET {}=%s WHERE barcode=%s".format(field)
            try:
                self.cursor.execute(query, (value, barcode))
            except Exception as exception:
                print exception.message

    def replace_items(self, barcode, **kwargs):
        """Replace a number of fields for barcode"""
        print kwargs
        for key, value in kwargs.items():
            self.replace_item(barcode, key, value)

    def get_item(self, barcode, statement=None):
        """Return all columns, or the one given by statement, for a barcode"""
        with self.connection:
            if statement is None:
                self.cursor.execute(
                    "SELECT * FROM fridays_items WHERE barcode=%s OR alternative_barcode=%s",
                    (barcode, barcode)
                )
                row = self.cursor.fetchall()
                out = row[0]
            elif statement in ("price", "name", "alc", "volume", "energy_content",
                               "beer_description", "brewery", "barcode"):
                self.cursor.execute(
                    "SELECT {} FROM fridays_items WHERE "
                    "barcode=%s OR alternative_barcode=%s".format(statement),
                    (barcode, barcode)
                )
                row = self.cursor.fetchall()
                out = row[0][0]
            else:
                print "Statement not found in fridays_item"
            #print out
        return out

    def insert_user(self, user_id, name):
        """cursor insert statement with data"""
        raise NotImplementedError()

    def get_user(self, user_barcode):
        """Gets user name from user barcode

        Args:
            user_barcode (str): The users barcode

        Returns:
            tuple: (Name (str), id (int)) tuple
        """
        with self.connection:
            self.cursor.execute("SELECT name, id FROM fridays_user WHERE user_barcode=%s",
                                (user_barcode,))
            row = self.cursor.fetchall()
            print row[0]
        return row[0]

    def insert_log(self, user_id, user_barcode, transaction_type, amount, item=None):
        """Cursor insert statement with data. Transactions are either
        "deposit" for depositing into your account (positive amount) or
        "purchase" for buying item (negative amount)"""

        if transaction_type not in ("deposit", "purchase"):
            print "Is transaction a deposit or purchase?"
        else:
            if transaction_type == "purchase":
                amount = -abs(amount)
            else:
                amount = abs(amount)
            values = (user_barcode, time.time(), amount, item, user_id)
            with self.connection:
                self.cursor.execute("INSERT INTO fridays_transactions (user_barcode,"
                                    " time, amount, item_barcode, user_id) VALUES "
                                    "(%s, from_unixtime(%s), %s, %s, %s)", values)

    def get_log(self, user_id):
        """ Returns user purchase log """
        raise NotImplementedError()

    def sum_log(self, user_id):
        """ Sums over all elements in amount with given user_id """
        with self.connection:
            self.cursor.execute("SELECT sum(amount) FROM fridays_transactions "
                                "WHERE user_id=%s", (user_id,))

            row = self.cursor.fetchall()
            print 'amount sum:', row[0][0]
        return row[0][0]

    def insert_review(self, user_id, item, review):
        """Insert review"""
        raise NotImplementedError
        # if review not in range(1, 7):
        #     print "Give from 1 to 6 stars"
        # else:
        #     values = (user_id, item, review)
        #     with self.connection:
        #         self.cursor.execute("INSERT INTO fridays_reviews "
        #                             "VALUES(%s, %s, %s)", values)

    def get_review(self, item):
        """Get review"""
        raise NotImplementedError
        # with self.connection:
        #     self.cursor.execute("SELECT count(review) FROM fridays_reviews "
        #                         "WHERE item=%s", (item,))
        #     count = self.cursor.fetchall()

        #     self.cursor.execute("SELECT avg(review) FROM fridays_reviews "
        #                         "WHERE item=%s", (item,))
        #     grade = self.cursor.fetchall()
        #     print count, grade
        # return count, grade

    def get_type(self, barcode):
        """Returns type of barcode"""
        if barcode in ("50", "100", "200", "500", "1000"):
            return "deposit_amount"
        self.cursor.execute("SELECT count(*) FROM fridays_items WHERE "
                            "barcode=%s OR alternative_barcode=%s", (barcode, barcode))
        if self.cursor.fetchall()[0][0] == 1:
            return "beer"
        self.cursor.execute("SELECT count(*) FROM fridays_user WHERE user_barcode=%s",
                            (barcode,))
        if self.cursor.fetchall()[0][0] == 1:
            return "user"
        else:
            return "invalid"

def module_test():
    """Run the module test"""
    try:
        # Assume office PC and just try and connect to db
        database = BarDatabase("servcinf-sql", 3306)
        through_tunnel = False
    except MySQLdb.OperationalError:
        # If not, try and create a tunnel
        from ssh_tunnel import create_tunnel, close_tunnel
        create_tunnel()
        time.sleep(1)
        database = BarDatabase("127.0.0.1", 9000)
        through_tunnel = True


    #DATABASE.insert_user(1234567890128,"test2")

    username, id_ = database.get_user('test')
    print "For barcode 'test' fetch name '{}' and id '{}'".format(username, id_)

    print "For id {} fetch sum {}".format(id_, database.sum_log(id_))

    database.cursor.execute('select * from fridays_items')
    for line in database.cursor.fetchall():
        print line

    if through_tunnel:
        close_tunnel()
        time.sleep(1)




if __name__ == "__main__":
    module_test()
