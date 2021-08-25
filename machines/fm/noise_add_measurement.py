import MySQLdb
from credentials import user, passwd, host, port

class DatabaseInterface(object):

    def __init__(self, host='servcinf-sql', port=3306, use_unicode=False):
        self.types = {}
        self.codenames = {}
        self.descriptions = {}
        self.connection = MySQLdb.connect(
            host=host,
            port=port,
            user=user,
            passwd=passwd,
            db='cinfdata',
            charset='utf8',
            use_unicode=use_unicode,
            )
        self.connection.autocommit(True)
        self.cursor = self.connection.cursor()

        self.cursor.execute(
            'select * from dateplots_descriptions where description like "%noise%"'
            )
        for i, row in enumerate(self.cursor.fetchall()):
            self.types[i] = row[0]
            self.codenames[i] = row[1].decode('utf8')
            self.descriptions[i] = row[2].decode('utf8')
        self.items = i + 1

    def get_time(self):
        self.cursor.execute('select now();')
        now = str(self.cursor.fetchall()[0][0])
        user = input('Enter timestamp (leave blank for default: {}):\n'.format(now))
        if user == '':
            return now
        self.cursor.execute('select from_unixtime(unix_timestamp("{}"));'.format(user))
        result = self.cursor.fetchall()[0][0]
        if result is None:
            print('Time "{}" is not a valid timestamp'.format(user))
        return result

    def insert_measurement(self, index, time, value):
        ack = input('Insert ({}, {}) in "{}"? (y/n)\n'.format(time, value, self.descriptions[index]))
        if ack.lower() == 'y':
            self.cursor.execute(
                'INSERT INTO dateplots_noise (time, value, type) VALUES (%s, %s, %s)',
                (time, value, self.types[index]),
            )
            print('Measurement added')
        else:
            print('Measurement aborted')

    def list_items(self):
        """ List the items to choose from in a table """
        print('\nThe you can choose a dataset from following table:')
        # Find maximum width of each column
        width = {}
        width[0] = max([len(str(value)) for value in ['index', *list(range(self.items))]])
        width[1] = max([len(str(value)) for value in ['type', *list(self.types.values())]])
        width[2] = max([len(str(value)) for value in ['codename', *list(self.codenames.values())]])
        width[3] = max([len(str(value)) for value in ['description', *list(self.descriptions.values())]])
        # Define the row separator
        line = ''
        for i in range(4):
            line += '+-'
            line += '-'*(width[i] + 1)
        line += '+'
        
        # Print header
        print(line)
        print((
            '| ' + 'index'.ljust(width[0], ' ') + ' ' +
            '| ' + 'type'.ljust(width[1], ' ') + ' ' +
            '| ' + 'codename'.ljust(width[2], ' ') + ' ' +
            '| ' + 'description'.ljust(width[3], ' ') + ' ' +
            '|'
            )
        )
        # Print contents
        cols = [list(range(self.items)), self.types, self.codenames, self.descriptions]
        for j in range(self.items):
            print(line)
            for i in range(4):
                print('| ' + str(cols[i][j]).ljust(width[i], ' ') + ' ', end='')
            print('|')
        print(line)

if __name__ == '__main__':
    DB = DatabaseInterface(host=host, port=port)

    while True:
        DB.list_items()
        ack = input('Choose dataset by "index" according to\nabove table or (q)uit\n')
        if ack.lower() == 'q':
            break
        try:
            index = int(ack)
        except ValueError:
            continue

        if index < 0 or index >= DB.items:
            print('"{}" not a valid index - Check table!'.format(ack))
        time = DB.get_time()
        if time is None:
            continue
        value = input('Enter noise level in dbA (leave empty to abort)\n')
        if value == '':
            continue
        DB.insert_measurement(index, time, value)
