# -*- coding: utf-8 -*-

import MySQLdb


class BarDatabase(object):
    """Class for comunicating with database"""
    def __init__(self):
        dbpath = "Beerdb"
        self.connection = MySQLdb.connect(host='servcinf', user='fridays',
                                          passwd='fridays', db='cinfdata',
                                          port=3306)
        self.cursor = self.connection.cursor()

    def insert_item(self, barcode, price, name, alc, volume=None, energy_content=None, beer_description=None, brewery=None):
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
        values = (barcode, price, name, alc, volume, energy_content, beer_description, brewery)
        with self.connection:
            self.cursor.execute("INSERT INTO fridays_items VALUES(%s, %s, %s, %s, %s, %s, %s, %s)", values)

    def replace_item(self, barcode, field, value):
        # cursor replace one or more statements with data
        print field, value
        values = (barcode, value)
        with self.connection:
            query="UPDATE fridays_items SET {}=%s WHERE barcode=%s".format(field)
            try:
                self.cursor.execute(query, (value, barcode))
            except Exception as exception:
                print exception.message

    def replace_items(self, barcode, **kwargs):
        print kwargs
        for key, value in kwargs.items():
            self.replace_item(barcode, key, value)

    def get_item(self, barcode, statement=None):
        with self.connection:
            if statement==None:
                self.cursor.execute("SELECT * FROM fridays_items WHERE barcode=%s", (barcode,))
                row = self.cursor.fetchall()
                out =row[0]
            elif statement in ("price", "name", "alc", "volume", "energy_content", "beer_description", "brewery"):
                self.cursor.execute("SELECT " + statement + " FROM fridays_items WHERE barcode=%s", (barcode,))
                row = self.cursor.fetchall()
                out = row[0][0]
            else:
                print "Statement not found in fridays_item"
            #print out
        return out

    def insert_user(self, user_id, name):
        # cursor insert statement with data
        raise NotImplementedError
        values = (user_id, name)
        with self.connection:
            self.cursor.execute("INSERT INTO fridays_user VALUES(%s, %s)", values)

    def get_user(self, user_id, statement = None):
        raise NotImplementedError
        with self.connection:
            self.cursor.execute("SELECT * FROM fridays_user WHERE user_id=%s", (user_id,))

            row = self.cursor.fetchall()
            print row[0]
        return row[0]

    def insert_log(self, user_id, transaction_type, amount, item=None):
        ''' cursor insert statement with data. Transactions are either
        "deposit" for depositing into your account (positive amount) or
        "purchase" for buying item (negative amount)'''
        raise NotImplementedError
        if transaction_type not in ("deposit", "purchase"):
            print "Is transaction a deposit or purchase?"
        else:
            if transaction_type == "purchase":
                amount = -abs(amount)
            else:
                amount = abs(amount)
            values = (user_id, transaction_type, amount, item)
            with self.connection:
                self.cursor.execute("INSERT INTO fridays_log VALUES(%s, datetime(), %s, %s, %s)", values)

    def get_log(self, user_id):
        raise NotImplementedError
        with self.connection:
            self.cursor.execute("SELECT * FROM fridays_log WHERE user_id=%s", (user_id,))

            row = self.cursor.fetchall()
            print row
        return row[0]

    def sum_log(self, user_id):
        # sums over all elements in amount with given user_id
        raise NotImplementedError
        with self.connection:
            self.cursor.execute("SELECT sum(amount) FROM fridays_log WHERE user_id=%s", (user_id,))

            row = self.cursor.fetchall()
            print 'amount sum:', row[0][0]
        return row[0][0]
        pass

    def insert_review(self, user_id, item, review):
        raise NotImplementedError
        if review not in range(1,7):
            print "Give from 1 to 6 stars"
        else:
            values = (user_id, item, review)
            with self.connection:
                self.cursor.execute("INSERT INTO fridays_reviews VALUES(%s, %s, %s)", values)

    def get_review(self, item):
        raise NotImplementedError
        with self.connection:
            self.cursor.execute("SELECT count(review) FROM fridays_reviews WHERE item=%s", (item,))
            count = self.cursor.fetchall()

            self.cursor.execute("SELECT avg(review) FROM fridays_reviews WHERE item=%s", (item,))
            grade = self.cursor.fetchall()
            print count, grade
        return count, grade

    def get_type(self, barcode):
        """Returns type of barcode"""
        self.cursor.execute("SELECT count(*) FROM fridays_items WHERE barcode=%s", (barcode,))
        if self.cursor.fetchall()[0][0] == 1:
            return "beer"
        else:
            return "invalid"
