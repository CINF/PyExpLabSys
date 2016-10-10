"""log workday status to database and live sockets"""

import sys
import json
import traceback
from collections import defaultdict, Counter
from pprint import pprint
import requests


EXPORT_ADDRESS = 'https://trello.com/b/3OmA20Pp.json'


def organize_comments(actions):
    """Return the comments for a card"""
    comments = defaultdict(list)
    for action in actions:
        if action['type'] != 'commentCard':
            continue
        card_id = action['data']['card']['id']
        comments[card_id].append(action['data']['text'])
    return comments


def time_line_to_float(line):
    """Return time as float from time line"""
    _, hours, minutes = [c.strip(' MH') for c in line.split(':')]
    return float(hours) + float(minutes) / 60


def get_duration_from_card(card, comments_for_all_cards, done=False):
    """Return the estimate or actual time consumption of a card"""
    for line in card['desc'].split('\n'):
        if line.lower().startswith('estimate'):
            estimate = time_line_to_float(line)
            break
    else:
        raise ValueError('No estimate in card')

    if done:
        comments = comments_for_all_cards[card['id']]
        for comment in comments:
            for line in comment.split('\n'):
                if line.lower().startswith('spent'):
                    spent = time_line_to_float(line)
                    return spent
    else:
        return estimate

    print('missing spent for card:', card['name'])
    return estimate


def get_board_status():
    """Return the sum counts for the board"""
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

    card_counts = {key: len(value) for key, value in cards.items()}
    # Sum up the times
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
                traceback.print_exception(file=sys.stdout)

    return card_counts, times


def main():
    """The main function"""
    card_counts, times = get_board_status()
    pprint(card_counts)
    pprint(times)
    

main()
