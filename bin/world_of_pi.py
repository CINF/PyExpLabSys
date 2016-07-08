
"""Script to run command on many raspberry pi's at once"""

from os import path
import sys
import math
from pprint import pprint
if sys.version_info[0] < 3:
    raise RuntimeError('World of pi is Python 3 only')


from configobj import ConfigObj


def parse_arguments():
    """Parse the command line arguments"""

def modify_config():
    """Modify the terminator config file"""

    """
    {'child0': {'order': '0',
                'parent': '',
                'position': '65:24',
                'size': ['1855', '1176'],
                'type': 'Window'},
     'child1': {'order': '0',
                'parent': 'child0',
                'position': '592',
                'type': 'VPaned'},
     'child2': {'order': '0',
                'parent': 'child1',
                'position': '933',
                'type': 'HPaned'},
     'child5': {'order': '1',
                'parent': 'child1',
                'position': '933',
                'type': 'HPaned'},
     'terminal3': {'command': 'ps',
                   'group': 'Omnicron',
                   'order': '0',
                   'parent': 'child2',
                   'profile': 'pip',
                   'type': 'Terminal'},
     'terminal4': {'command': 'df -h',
                   'group': 'Omnicron',
                   'order': '1',
                   'parent': 'child2',
                   'profile': 'pip',
                   'type': 'Terminal'},
     'terminal6': {'command': 'ls',
                   'group': 'Omnicron',
                   'order': '0',
                   'parent': 'child5',
                   'profile': 'pip',
                   'type': 'Terminal'},
     'terminal7': {'command': 'pwd;bash',
                   'group': 'Omnicron',
                   'order': '1',
                   'parent': 'child5',
                   'profile': 'pip',
                   'type': 'Terminal'}}
    """

    configpath  = path.join(path.expanduser('~'), '.config', 'terminator', 'config')
    print(configpath)
    config = ConfigObj(configpath)
    #config.filename = config.filename + '_test'
    config['layouts']['world_of_pi'] = {}
    layout = config['layouts']['world_of_pi']

    # Global settings
    x_offset = 100
    y_offset = 100
    terms = 9
    x = 1000
    y = 1000

    # Add base child (window)
    layout['child0'] = {
        'order': '0',
        'parent': '',
        'position': '{}:{}'.format(x_offset, y_offset),
        'size': [str(x), str(y)],
        'type': 'Window'
    }

    # Calculate number of rows and columns
    row_n = int(math.floor(math.sqrt(terms)))
    col_n = [terms // row_n]
    col_n.append(terms - sum(col_n))

    terminal_places = [('child0', '0')]
    last_child_num = 0
    # Make rows
    while len(terminal_places) < row_n:
        new_terminal_places = []
        for place_num, (parent, order) in enumerate(terminal_places):
            remaining = len(terminal_places) - place_num - 1#  + len(new_terminal_places)
            # if the number of proginal slots remaining + the number that will be
            # added is <= row_n
            if remaining + len(new_terminal_places) + 2 <= row_n:
                print('NEW VPANED')
                last_child_num += 1
                new_child_name = 'child' + str(last_child_num)
                place = 100  # FIXME
                layout[new_child_name] = {
                    'order': order,
                    'parent': parent,
                    'position': str(place),
                    'type': 'VPaned'
                }
                new_terminal_places += [(new_child_name, '0'), (new_child_name, '1')]
            else:
                new_terminal_places.append((parent, order))
        pprint(layout)
        terminal_places = new_terminal_places
    print('terminal places after rows', terminal_places)
    

    # Make columns FIXME row_n -> terms
    while len(terminal_places) < terms:
        new_terminal_places = []
        for place_num, (parent, order) in enumerate(terminal_places):
            print(place_num, (parent, order))
            remaining = len(terminal_places) - place_num - 1#  + len(new_terminal_places)
            # if the number of proginal slots remaining + the number that will be
            # added is <= row_n
            print('rem', remaining)
            if remaining + len(new_terminal_places) + 2 <= terms:
                last_child_num += 1
                new_child_name = 'child' + str(last_child_num)
                place = 300  # FIXME
                layout[new_child_name] = {
                    'order': order,
                    'parent': parent,
                    'position': str(place),
                    'type': 'HPaned'
                }
                new_terminal_places += [(new_child_name, '0'), (new_child_name, '1')]
            else:
                new_terminal_places.append((parent, order))
        terminal_places = new_terminal_places
        print(terminal_places)


    #for n in range(row_n - 1):
    #    print(n)

    print()
    print(terminal_places)
    print()

    for n, terminal_place in enumerate(terminal_places):
        layout['terminal' + str(n)] = {
            'command': 'ps;bash',
            'group': 'Omnicron',
            'order': terminal_place[1],
            'parent': terminal_place[0],
            'profile': 'pip',
            'type': 'Terminal'
        }

    

    pprint(layout)

    config.write()
    #pprint(config)
    #print()
    #pprint(config['layouts']['look'])
    #print(type(config['layouts']['look']))


def run():
    """Run terminator"""


def main():
    """The main function"""
    args = parse_arguments()
    modify_config()
    run()


main()
