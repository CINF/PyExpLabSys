"""This script tests whether all the names and breweries in fridays_items and names in
friday_user can be decoded by the four_d_systems to_ascii function
"""

from __future__ import print_function
import MySQLdb
from PyExpLabSys.drivers.four_d_systems import to_ascii


def main():
    """Run the decoding steps"""
    con = MySQLdb.connect('servcinf', 'fridays', 'fridays', 'cinfdata',
                          charset='utf8', use_unicode=True)
    cursor = con.cursor()

    print('\n========= Users ========')
    cursor.execute('select name from fridays_user')
    users = cursor.fetchall()
    for user in users:
        user = user[0]
        norm_user = to_ascii(user)
        try:
            norm_user.encode('ascii')
        except UnicodeDecodeError:
            print('Encoding to ascii failed for this entry')
            print(user)
            raise
        print(u'Name:    {:<30} -> {}'.format(user, norm_user))


    print('\n========= Items ========')
    cursor.execute('select name, brewery from fridays_items')
    items = cursor.fetchall()
    for name, brewery in items:
        print("--------------------")
        norm_name = to_ascii(name)
        try:
            norm_name.encode('ascii')
        except UnicodeDecodeError:
            print('Encoding to ascii failed for this entry')
            print(name)
            raise
        print(u'Name:    {:<30} -> {}'.format(name, norm_name))

        norm_brewery = to_ascii(brewery)
        try:
            norm_brewery.encode('ascii')
        except UnicodeDecodeError:
            print('Encoding to ascii failed for this entry')
            print(brewery)
            raise
        print(u'Brewery: {:<30} -> {}'.format(brewery, norm_brewery))


main()
