# -*- coding: utf-8 -*-

import sqlite3

class BeerClass(object):

    def __init__(self):
        dbpath = "Beerdb"
        self.connection = sqlite3.connect(dbpath)
        self.cursor = self.connection.cursor()

    def create_tables(self):
        create_statements = [
            'CREATE TABLE b_items (barcode integer, price integer, name text, alc real, volume real default null, energy_content real default null, beer_description blop default null, brewery text default null)',
            'CREATE TABLE b_users (user_id text, name text)',
            'CREATE TABLE b_log (user_id text, time text, type text, amount float, item integer default null)',
            'CREATE TABLE b_reviews (user_id text, item integer, review integer)',
        ]
        for create in create_statements:
            self.cursor.execute(create)
        self.connection.commit()

    def insert_item(self, barcode, price, name, alc, volume=None, energy_content=None, beer_description=None, brewery=None):
        # cursor insert statement with data
        values = (barcode, price, name, alc, volume, energy_content, beer_description, brewery)
        with self.connection:
            self.cursor.execute("INSERT INTO b_items VALUES(?, ?, ?, ?, ?, ?, ?, ?)", values)
    
    def replace_item(self, barcode, field, value):
        # cursor replace one or more statements with data
        print field, value
        values = (barcode, value)
        with self.connection:
            query="UPDATE b_items SET {}=? WHERE barcode=?".format(field)
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
                self.cursor.execute("SELECT * FROM b_items WHERE barcode=?", (barcode,))
                row = self.cursor.fetchall()
                out =row[0]
            elif statement in ("price", "name", "alc", "volume", "energy_content", "beer_description", "brewery"):
                self.cursor.execute("SELECT " + statement + " FROM b_items WHERE barcode=?", (barcode,))
                row = self.cursor.fetchall()
                out = row[0][0]
            else:
                print "Statement not found in b_item"
            
            
            print out
        return out
        

    def insert_user(self, user_id, name):
        # cursor insert statement with data
        values = (user_id, name)
        with self.connection:
            self.cursor.execute("INSERT INTO b_users VALUES(?, ?)", values)
            
    def get_user(self, user_id):
        
        with self.connection:
            self.cursor.execute("SELECT * FROM b_users WHERE user_id=?", (user_id,))
            
            row = self.cursor.fetchall()
            print row[0]
        return row[0]
    
    def insert_log(self, user_id, transaction_type, amount, item=None):
        ''' cursor insert statement with data. Transactions are either
        "deposit" for depositing into your account (positive amount) or
        "purchase" for buying item (negative amount)'''
        if transaction_type not in ("deposit", "purchase"):
            print "Is transaction a deposit or purchase?"
        else:
            if transaction_type == "purchase":
                amount = -abs(amount)
            else:
                amount = abs(amount)
            values = (user_id, transaction_type, amount, item)
            with self.connection:
                self.cursor.execute("INSERT INTO b_log VALUES(?, datetime(), ?, ?, ?)", values)
    
    def get_log(self, user_id):
        
        with self.connection:
            self.cursor.execute("SELECT * FROM b_log WHERE user_id=?", (user_id,))
            
            row = self.cursor.fetchall()
            print row
        return row[0]
    
    def sum_log(self, user_id):
        # sums over all elements in amount with given user_id
        with self.connection:
            self.cursor.execute("SELECT sum(amount) FROM b_log WHERE user_id=?", (user_id,))
            
            row = self.cursor.fetchall()
            print 'amount sum:', row[0][0]
        return row[0][0]
        pass
    
    def insert_review(self, user_id, item, review):
        if review not in range(1,7):
            print "Give from 1 to 6 stars"
        else:
            values = (user_id, item, review)
            with self.connection:
                self.cursor.execute("INSERT INTO b_reviews VALUES(?, ?, ?)", values)
    
    def get_review(self, item):
        with self.connection:
            self.cursor.execute("SELECT count(review) FROM b_reviews WHERE item=?", (item,))
            count = self.cursor.fetchall()
            
            self.cursor.execute("SELECT avg(review) FROM b_reviews WHERE item=?", (item,))
            grade = self.cursor.fetchall()
            print count, grade
        return count, grade
        

bc = BeerClass()

try:
    bc.create_tables()
    print "New database created"
except:
    print "Database exist already"

bc.insert_item(126, 10, "Test øl".decode('utf-8'), 4.5, volume=0.5, brewery="Carlsberg")
bc.get_item(126)

bc.replace_items(126, brewery="Tuborg".decode('utf-8'), volume=1.0)
bc.get_item(126)

#bc.insert_user(102030, "Jakob")
#bc.get_user(102030)

bc.insert_log(202030, "purchase", bc.get_item(126, "price"))
#bc.get_log(102030)
bc.sum_log(202030)
bc.insert_review(102030, 126, 7)
bc.get_review(126)
