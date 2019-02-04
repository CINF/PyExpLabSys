
# pylint: disable=import-error,no-else-return,too-many-locals,too-many-branches

"""log workday status to database and live sockets"""

import sys
from time import sleep
import datetime
import traceback
from operator import itemgetter
from collections import defaultdict, Counter
from pprint import pprint
import requests
import credentials_hall

from PyExpLabSys.common.database_saver import ContinuousDataSaver


EXPORT_ADDRESS = 'https://trello.com/b/MBUFNn7T.json'


# def organize_comments(actions):
#     """Return the comments for a card"""
#     # The data comes out of the export as normalized "actions", so we
#     # need to associate the only the comments to the card ids
#     comments = defaultdict(list)
#     for action in actions:
#         if action['type'] != 'commentCard':
#             continue
#         card_id = action['data']['card']['id']
#         comments[card_id].append(action['data']['text'])
#     return comments


def time_line_to_float(line):
    """Return time as float from time line"""
    line = line.lower().replace('estimate', '').replace('spent', '').lstrip(': ')
    hours, minutes = [c.strip(' mh') for c in line.split(':')]
    return float(hours) + float(minutes) / 60


def get_duration_from_card(card, done=False):
    """Return the estimate or actual time consumption of a card"""
    # Look for estimate line in description
    for custom_field_data in card['customFieldItems']:
        if custom_field_data['idCustomField'] == '5bd04ea096a23c53c9d4c877':
            estimate = float(custom_field_data['value']['number'])
            break
    else:
        #raise Exception("No estimate for card {}".format(card['name']))
        estimate = 0

    # If the task is done, additionally look for updates on spent time
    if done:
        for custom_field_data in card['customFieldItems']:
            if custom_field_data['idCustomField'] == '5bd1c18843e28e6db7e0394b':
                spent = float(custom_field_data['value']['number'])
                msg = 'Returning spent {: >8.2f} for complete card: {}'
                print(msg.format(spent, card['name']))
                return spent
    else:
        print('Returning estimate {: >5.2f} for incomplete card : {}'.\
              format(estimate, card['name']))
        return estimate

    print('Returning estimate {: >5.2f} NOT spent, complete card: {}'.\
          format(estimate, card['name']))
    return estimate


def get_board_status():
    """Return the sum counts for the board"""
    # Get the board data
    request = requests.get(EXPORT_ADDRESS)
    board = request.json()

    # Get the list id to title translation
    list_id_to_title = {}
    for list_ in board['lists']:
        list_id_to_title[list_['id']] = list_['name']

    # Sort cards
    cards = defaultdict(list)
    for card in board['cards']:
        list_title = list_id_to_title[card['idList']]
        if list_title.startswith('Tasks'):
            cards['ToDo'].append(card)
        elif list_title == 'In Progress':
            cards['In Progress'].append(card)
        elif list_title.startswith('Done'):
            cards['Done'].append(card)

    ## Organize comments
    #comments_for_all_cards = organize_comments(board['actions'])

    # Sum up the times
    card_counts = {key: len(value) for key, value in cards.items()}
    print(card_counts)
    times = Counter()
    for category, cards in cards.items():
        done = category == 'Done'
        for card in cards:
            # FIXME
            #try:
            duration = get_duration_from_card(
                card,
                #comments_for_all_cards,
                done=done,
            )
            times[category] += duration
            #except Exception:  # pylint: disable=broad-except
            #    print('EXCEPTION DURING GET DURATION:', card['name'])
            #    traceback.print_exc(file=sys.stdout)

    # Calculate highscore
    # floormanagers = {"4f6218048dda41741ca9a15f", "5413dab58ec329d97290155f"}
    # scores = Counter()
    # for card in board['cards']:
    #     print("CARD", card['name'])
    #     list_title = list_id_to_title[card['idList']]
    #     if list_title == 'Done':
    #         ids = [id_ for id_ in card['idMembers'] if id_ not in floormanagers]
    #         estimate = get_duration_from_card(card, comments_for_all_cards, done=False)
    #         spent = get_duration_from_card(card, comments_for_all_cards, done=True)
    #         if spent > estimate:
    #             to_split = spent
    #         else:
    #             to_split = estimate
    #         for id_ in ids:
    #             scores[id_] += to_split / len(ids)

    # # Translate highscore as function of full name
    # for id_, _ in scores.copy().items():
    #     for member in board['members']:
    #         if id_ == member['id']:
    #             name = member['fullName']
    #             break
    #     else:
    #         name = 'Not available'
    #     scores[name] = scores.pop(id_)

    # sorted_scores = list(reversed(sorted(scores.items(), key=itemgetter(1))))
    # print(sorted_scores)

    return card_counts, times  #, sorted_scores


def since_9am():
    """Return the number of hours since 9am as float"""
    now = datetime.datetime.now()
    if now.hour == 12:
        return 3

    start = now.replace(hour=9, minute=0, second=0, microsecond=0)
    delta = now - start
    hours = delta.total_seconds() / 3600
    hours = max(hours, 0.0)

    if now.hour > 12:
        return hours - 1
    else:
        return hours



def main():
    """The main function"""
    # Setup logger and live socket
    codenames = [
        'work_estimate', 'work_left', 'work_left_minus_started',
        'work_completed', 'work_total'
    ]
    logger = ContinuousDataSaver(
        'dateplots_hall',
        credentials_hall.username,
        credentials_hall.password,
        codenames
    )
    logger.start()

    try:
        while True:
            # Get board status
            #card_counts, times, high_scores = get_board_status()
            card_counts, times = get_board_status()
            print('Card counts')
            pprint(card_counts)
            print('\nTimes')
            pprint(times)

            # Total work 80 and 14 people
            total_work = 66.337
            estimate = max(total_work - since_9am() * 14, 0)
            batch = {
                'work_estimate': estimate,
                'work_left': times['ToDo'] + times['In Progress'],
                'work_left_minus_started': times['ToDo'],
                'work_completed': times['Done'],
                'work_total': sum(times.values()),
            }
            # Send to and database
            print('\n##########\nbatch')
            #pprint(batch)

            for codename, value in batch.items():
                #print(codename, value)
                logger.save_point_now(codename, value)

            print('Sent', datetime.datetime.now())
            sleep(120)
    except (KeyboardInterrupt, ZeroDivisionError):
        print("Done")
        logger.stop()

main()
