#!/usr/bin/env python3

"""Command Line Interface for WhereCanIFindStuffAtSurfCat"""

import re
import argparse

import requests

from PyExpLabSys.common.supported_versions import python3_only

python3_only(__file__)


ADDRESS = ('https://cinfwiki.fysik.dtu.dk/cinfwiki/PracticalInformation/'
           'WhereCanIFindStuffAtSurfCat?action=raw')
MAPS = {
    '9': ('https://cinfwiki.fysik.dtu.dk/cinfwiki/PracticalInformation/'
          'WhereCanIFindStuffAtSurfCat?action=AttachFile&do=get&'
          'target=basement.png'),
    '0': ('https://cinfwiki.fysik.dtu.dk/cinfwiki/PracticalInformation/'
          'WhereCanIFindStuffAtSurfCat?action=AttachFile&do=get'
          '&target=groundfloor.png'),
    '1': ('https://cinfwiki.fysik.dtu.dk/cinfwiki/PracticalInformation/'
          'WhereCanIFindStuffAtSurfCat?action=AttachFile&do=get'
          '&target=firstfloor.png'),
    }


def parse_args():
    """Parse command line arguments"""
    description = 'Command line interface to where can I find stuff a surfcat.'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('search_term', help='The term to search for')
    args = parser.parse_args()
    return args


def parse_content():
    """Parse the content from WhereCanIFindStuffAtSurfCat"""
    request = requests.get(ADDRESS)
    items = []
    started = False
    for line in request.text.split('\n'):
        if not started:
            if 'tablewidth' in line:
                started = True
            continue
        if started and '||' not in line:
            break
        items.append(Item.from_wiki(line))
    return items


class Item:
    """A searchable item

    The lines on the wiki looks like this
    || VGA Cables  || VGA-kabler  ||
    {{attachment:DB_many_VGA.jpg|mouse over description|height="100"}}
    || [[#Basement_.28-1.29|900D]]
    """

    location_re_sub = (r'\[\[.*?\|', r'\]\]')
    location_floor_re = re.compile(r'(\d)\d\d[A-Z]{0,2}')

    def __init__(self, english, danish, image, location):
        self.english = english
        self.danish = danish
        self.image = image
        self.location = location
        self.floors = self.location_floor_re.findall(location)
        self.strs = (english, danish)

    @classmethod
    def from_wiki(cls, line):
        """Class method to create Item object from wiki line"""
        split = line.split('||')
        english, danish, image, location = (e.strip() for e in split[1:5])
        # Extract image file name from a string such as:
        # {{attachment:USB_AB_2.jpg|mouse over description|height="100"}}
        image = image.split(':', 1)[1].split('|')[0]
        # Extract a location from a string such as
        # Use from: [[#Ground_floor_.280.29|015WR]] ... REPEAT
        for re_ in cls.location_re_sub:
            location = re.sub(re_, '', location)
        return cls(english, danish, image, location)

    def __repr__(self):
        return 'Item("{}", "{}", "{}", "{}")'.format(
            self.english, self.danish, self.image, self.location
        )

    def in_either(self, search_term, case_sensitive=False):
        """Return if search_term is in either"""
        if case_sensitive:
            return any(search_term in string for string in self.strs)

        search_term = search_term.lower()
        return any(search_term in string.lower() for string in self.strs)


def where():
    """Main where function"""
    # Parse args, gets table items and search
    args = parse_args()
    items = parse_content()
    floors = set()
    found = []
    for item in items:
        if item.in_either(args.search_term):
            floors.update(item.floors)
            found.append(item)

    # Calculate max lengths for print
    maxs = {}
    for key in ('danish', 'english', 'location'):
        maxs[key] = max(len(getattr(item, key)) for item in found)

    # Create output templates
    output_template = (
        '| {{item.english: <{english}}} | {{item.danish: <{danish}}}'
        ' | {{item.location: <{location}}} |'
    ).format(**maxs)
    vline = '+' + '-' * (sum(maxs.values()) + 8) + '+'

    # Print output
    print(vline)
    for item in found:
        print(output_template.format(item=item))
    print(vline)

    # Print maps locations
    print("\nFind floor maps at:")
    for floor in floors:
        print("### {}".format(floor))
        print(MAPS[floor])


where()
