#pylint: disable=too-many-branches

"""Script that logs Trello stats to the database"""

from collections import defaultdict
import json

import requests


def what(obj):
    """JSON helper"""
    print(type(obj))
    if isinstance(obj, dict):
        print(obj.keys())
    elif isinstance(obj, list):
        print(len(obj))


def extract_lists(data):
    """Extract lists"""
    lists = {}
    for list_ in data['lists']:
        if list_['closed']:
            continue
        lists[list_['id']] = list_['name']
    return lists


def extract_checklists(data):
    """Extract the checklists"""
    checklists = {checklist['id']: checklist for checklist in data['checklists']}
    return checklists


def extract_email(card):
    """Extract an email line form cards that have an email"""
    for plugin_data in card['pluginData']:
        if plugin_data['idPlugin'] == '56d5e249a98895a9797bebb9':
            value = json.loads(plugin_data['value'])
            try:
                return value['fields']['FR8Fr5IC-yjCfmY']
            except KeyError:
                pass
    return None

# pylint: disable=too-few-public-methods
class Missing:
    """Class that represents a checklist items that is missing with
    several people

    """
    def __init__(self):
        self.missing = 0
        self.total = 0
        # Names of all that is missing this point
        self.names = []
        # Names of the ones we have email for
        self.email_names = []
        # The email
        self.emails = []
        self.no_email = set()


def main():
    """Log stats from Trello to database"""
    request = requests.get('https://trello.com/b/FR8Fr5IC.json')
    data = request.json()
    #with open('emp', 'rb') as file_:
    #    data = load(file_)

    # Extract users
    lists = extract_lists(data)
    checklists = extract_checklists(data)

    # Filter cards, we only want active cards from the lists that start with Current
    cards = []
    for card in data['cards']:
        if card['closed']:
            continue

        # Check the list
        if not lists[card['idList']].startswith('Current'):
            continue

        cards.append(card)

    missing_items = defaultdict(Missing)
    # Collect missing checklist items
    for card in cards:
        email = extract_email(card)

        # Find the Introduction plan if there is one and of not continue
        for checklist_id in card['idChecklists']:
            checklist = checklists[checklist_id]
            if checklist['name'] == 'Introduction plan':
                break
        else:
            continue

        # Gather data for incomplete Introduction plan items
        for check_item in checklist['checkItems']:
            missing = missing_items[check_item['name']]
            missing.total += 1
            if check_item['state'] == 'incomplete':
                missing.missing += 1
                missing.names.append(card['name'])
                if email is not None:
                    missing.email_names.append(card['name'].split(' ')[0])
                    missing.emails.append(email)
                else:
                    missing.no_email.add(card['name'])

    print("########## Summary ###")
    max_length_name = max(len(name) for name in missing_items)
    for name in sorted(missing_items):
        missing = missing_items[name]
        print(" * {{: <{}}} ({{: >2}} out of {{: >2}} complete, "
              "{{: >2}} missing)".format(max_length_name).format(
                  name,
                  missing.total - missing.missing,
                  missing.total,
                  missing.missing
              )
             )

    print('\n########## Details ###', sep='')
    print("The following are details about which people are missing for each of the items\n")
    for name in sorted(missing_items):
        missing = missing_items[name]
        print("###", name, "###")
        print("{} out of {} are missing this part".format(
            missing.missing,
            missing.total
        ))
        for person in missing.names:
            print(" *", person)
        print()
        print("We have emails for {} out of the {} that is missing".format(
            len(missing.emails),
            missing.missing
        ))
        print("Namelist for email:", ", ".join(missing.email_names))
        print("\nEmail list        :", "; ".join(missing.emails), sep='')
        print("\nEmail list        :", ", ".join(missing.emails), sep='')
        print("\nWe have no email for:", ", ".join(missing.no_email), sep='')
        print()



if __name__ == '__main__':
    main()
