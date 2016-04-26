"""This script tests whether all the names and breweries in fridays_items and names in
friday_user can be decoded by the four_d_systems to_ascii function
"""

from __future__ import print_function
import MySQLdb
from PyExpLabSys.drivers.four_d_systems import to_ascii_utf8


def main():
    """Run the decoding steps"""
    con = MySQLdb.connect('servcinf-sql', 'fridays', 'fridays', 'cinfdata',
                          charset='utf8', use_unicode=False)
    cursor = con.cursor()

    print('\n========= Users ========')
    cursor.execute('select name from fridays_user')
    users = cursor.fetchall()
    for user in users:
        user = user[0]
        print(type(user))
        norm_user = to_ascii_utf8(user)
        try:
            norm_user.encode('ascii')
        except UnicodeDecodeError:
            print('Encoding to ascii failed for this entry')
            print(user)
            raise
        print('Name:    {:<30} -> {}'.format(user, norm_user))


    print('\n========= Items ========')
    cursor.execute('select name, brewery from fridays_items')
    items = cursor.fetchall()
    for name, brewery in items:
        print("--------------------")
        norm_name = to_ascii_utf8(name)
        try:
            norm_name.encode('ascii')
        except UnicodeDecodeError:
            print('Encoding to ascii failed for this entry')
            print(name)
            raise
        print('Name:    {:<30} -> {}'.format(name, norm_name))

        if brewery is None:
            continue
        norm_brewery = to_ascii_utf8(brewery)
        try:
            norm_brewery.encode('ascii')
        except UnicodeDecodeError:
            print('Encoding to ascii failed for this entry')
            print(brewery)
            raise
        print('Brewery: {:<30} -> {}'.format(brewery, norm_brewery))


main()
