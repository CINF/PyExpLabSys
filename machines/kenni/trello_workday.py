"""log workday status to database and live sockets"""

import sys
import json
from time import sleep
import datetime
import traceback
from operator import itemgetter
from collections import defaultdict, Counter
from pprint import pprint
import requests
import credentials_hall

from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.database_saver import ContinuousDataSaver


EXPORT_ADDRESS = 'https://trello.com/b/3OmA20Pp.json'


def organize_comments(actions):
    """Return the comments for a card"""
    # The data comes out of the export as normalized "actions", so we
    # need to associate the only the comments to the card ids
    comments = defaultdict(list)
    for action in actions:
        if action['type'] != 'commentCard':
            continue
        card_id = action['data']['card']['id']
        comments[card_id].append(action['data']['text'])
    return comments


def time_line_to_float(line):
    """Return time as float from time line"""
    line = line.lower().replace('estimate', '').replace('spent', '').lstrip(': ')
    hours, minutes = [c.strip(' mh') for c in line.split(':')]    
    return float(hours) + float(minutes) / 60


def get_duration_from_card(card, comments_for_all_cards, done=False):
    """Return the estimate or actual time consumption of a card"""
    # Look for estimate line in description
    for line in card['desc'].split('\n'):
        if line.lower().startswith('estimate'):
            estimate = time_line_to_float(line)
            break
    else:
        raise ValueError('No estimate in card')

    # If the task is done, additionally look for updates on spent time
    if done:
        comments = comments_for_all_cards[card['id']]
        # Look though all lines in the comments
        for comment in comments:
            for line in comment.split('\n'):
                if line.lower().startswith('spent'):
                    spent = time_line_to_float(line)
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
        if list_title.startswith('ToDo'):
            cards['ToDo'].append(card)
        elif list_title == 'In Progress':
            cards['In Progress'].append(card)
        elif list_title == 'Done':
            cards['Done'].append(card)

    # Organize comments
    comments_for_all_cards = organize_comments(board['actions'])

    # Sum up the times
    card_counts = {key: len(value) for key, value in cards.items()}
    times = Counter()
    for category, cards in cards.items():
        done = category == 'Done'
        for card in cards:
            # FIXME
            try:
                duration = get_duration_from_card(
                    card,
                    comments_for_all_cards,
                    done=done
                )
                times[category] += duration
            except Exception:
                print('EXCEPTION DURING GET DURATION:', card['name'])
                traceback.print_exc(file=sys.stdout)

    # Calculate highscore
    floormanagers = {"4f6218048dda41741ca9a15f", "5413dab58ec329d97290155f"}
    scores = Counter()
    for card in board['cards']:
        print("CARD", card['name'])
        list_title = list_id_to_title[card['idList']]
        if list_title == 'Done':
            ids = [id_ for id_ in card['idMembers'] if id_ not in floormanagers]
            estimate = get_duration_from_card(card, comments_for_all_cards, done=False)
            spent = get_duration_from_card(card, comments_for_all_cards, done=True)
            if spent > estimate:
                to_split = spent
            else:
                to_split = estimate
            for id_ in ids:
                scores[id_] += to_split / len(ids)

    # Translate highscore as function of full name
    for id_, score in scores.copy().items():
        for member in board['members']:
            if id_ == member['id']:
                name = member['fullName']
                break
        else:
            name = 'Not available'
        scores[name] = scores.pop(id_)

    sorted_scores = list(reversed(sorted(scores.items(), key=itemgetter(1))))
    print(sorted_scores)

    return card_counts, times, sorted_scores


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
    livesocket = LiveSocket('workday', codenames)
    livesocket.start()

    try:
        while True:
            # Get board status
            card_counts, times, high_scores = get_board_status()
            print('Card counts')
            pprint(card_counts)
            print('\nTimes')
            pprint(times)
            print('\nHigh Scores')
            pprint(high_scores)

            # format highscore
            highscore_str = 'High Score\n----------'
            if high_scores:
                largest_name = max(len(name) for name, value in high_scores)
            for name, value in high_scores:
                highscore_str += '\n{{: <{}}}: {{:.2f}}'.format(largest_name).format(name, value)

            # Total work 80 and 10 people
            total_work = 66.33
            estimate = max(total_work - since_9am() * 10, 0)
            batch = {
                'work_estimate': estimate,
                'work_left': times['ToDo'] + times['In Progress'],
                'work_left_minus_started': times['ToDo'],
                'work_completed': times['Done'],
                'work_total': sum(times.values()),
                'work_highscore': highscore_str,
            }
            # Send to live socket and database
            print('\n##########\nbatch')
            pprint(batch)
            livesocket.set_batch_now(batch)

            batch.pop('work_highscore')
            for codename, value in batch.items():
                logger.save_point_now(codename, value)

            print('Sent', datetime.datetime.now())
            sleep(600)
    except KeyboardInterrupt:
        livesocket.stop()
        logger.stop()

main()
