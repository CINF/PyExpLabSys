#pylint: disable=too-many-locals

"""Script that logs Trello stats to the database"""

from collections import Counter

from MySQLdb import connect
import requests

from PyExpLabSys.common.supported_versions import python3_only
python3_only(__file__)

import hall_credentials


#'490', 'trello_list_unsorted', 'Trello list Unsorted'
#'491', 'trello_list_down_the_queue', 'Trello list Stuff far down the queue'
#'492', 'trello_list_to_do_pyexplabsys', 'Trello list To Do PyExpLabSys'
#'493', 'trello_list_doing', 'Trello list Doing'
#'494', 'trello_list_to_do_cindata_cinfwiki', 'Trello list To Do Cinfdata and cinfwiki'
#'495', 'trello_list_TODAY', 'Trello list TODAY'
#'496', 'trello_list_on_hold', 'Trello list On Hold'
#'497', 'trello_list_to_do', 'Trello list To Do'
#'498', 'trello_user_kenneth', 'Trello user Kenneth Nielsen'
#'499', 'trello_user_robert', 'Trello user Robert Jensen'
#'500', 'trello_user_brian', 'Trello user Brian'
#'502', 'trello_list_broken_stuff', 'Trello list Broken Stuff'


LIST_ID_TO_DB_ID = {
    '5415edbf842e6c5c9ed5c887': 497,  # To Do
    '5415edbf842e6c5c9ed5c888': 493,  # Doing
    '54167f9453873b69bf6aa077': 491,  # Stuff far down the queue
    '541699af8ec329d972928ea5': 494,  # To Do Cinfdata and cinfwiki
    '5416af066ad205ad9505a370': 492,  # To Do PyExpLabSys
    '5416c831187734dc95e3e683': 490,  # Unsorted - add new stuff here
    '553dfee6e6464cba3e47a53b': 495,  # TODAY
    '553dff5d0a8a0ef3556f3f4e': 496,  # On hold'
    '5b9229ee34b1da2692a589b7': 502,  # 'Broken stuff'
}


USER_ID_TO_DB_ID = {
    '4f6218048dda41741ca9a15f': 498,  # Kenneth Nielsen
    '5413dab58ec329d97290155f': 499,  # Robert Jensen
    '541fe2f9a2907d8506bdde69': 500,  # Brian Knudsen
}
LOG_USERS = USER_ID_TO_DB_ID.keys()


def what(obj):
    """JSON helper"""
    print(type(obj))
    if isinstance(obj, dict):
        print(obj.keys())
    elif isinstance(obj, list):
        print(len(obj))

def extract_users(data):
    """Extracts users"""
    users = {}
    for member in data['members']:
        users[member['id']] = member['fullName']
    return users


def extract_lists(data):
    """Extract lists"""
    lists = {}
    for list_ in data['lists']:
        if list_['closed']:
            continue
        lists[list_['id']] = list_['name']
    return lists


def main():
    """Log stats from Trello to database"""
    request = requests.get('https://trello.com/b/SQ9tbyrA.json')
    data = request.json()

    # Extract users
    users = extract_users(data)
    lists = extract_lists(data)

    # Get active cards
    cards = [card for card in data['cards'] if not card['closed']]

    total_number_of_open_cards = len(cards)
    user_count = Counter()
    list_count = Counter()

    # Collect stats
    for card in cards:
        # Add to list counter
        list_count[card['idList']] += 1
        # Add to user counter
        for member in card.get('idMembers', []):
            user_count[member] += 1

    # Form database connection
    connection = connect(
        host='servcinf-sql',
        user=hall_credentials.USERNAME,
        passwd=hall_credentials.PASSWORD,
        db='cinfdata'
    )
    cursor = connection.cursor()
    query = 'INSERT INTO dateplots_hall (`type`,`value`) VALUES'

    # Log lists
    for list_id, count in list_count.items():
        query += '({},{}),'.format(LIST_ID_TO_DB_ID[list_id], count)
        print(list_id, lists[list_id], count)


    # Log users
    print()
    for user_id, count in user_count.items():
        print(user_id, users[user_id], count)
        if user_id in LOG_USERS:
            query += '({},{}),'.format(USER_ID_TO_DB_ID[user_id], count)

    # Add the total
    query += '({},{});'.format(501, total_number_of_open_cards)

    print('\n', query, sep='')

    cursor.execute(query)


if __name__ == '__main__':
    main()
