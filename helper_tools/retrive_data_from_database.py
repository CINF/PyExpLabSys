import tomllib
import pymysql
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

class DatabaseReader():
    def __init__(self):
        self.measurement = None
        with open('db_config.toml', 'rb') as f:
            self.config = tomllib.load(f)

    def _read_from_sql(self, query, parameters):
        connection = pymysql.connect(
            **self.config,
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(query, parameters)
                result = cursor.fetchall()
        return result
        
    def read_measurement(self, setup, timestamp):
        # As of the PyExpLabSys convention, metadata are in measurements_<setup>
        # and the actual data in xy_values_<setup>
        parameters = (timestamp,)
        metadata_query = "select * from `measurements_{}` where `time`=%s".format(setup)
        metadata = self._read_from_sql(metadata_query, parameters)

        self.measurement = {}
        data_query = "select `x`, `y` from `xy_values_{}` where `measurement`=%s".format(setup)
        data_query = data_query.format(setup)
        
        for row in metadata:
            parameters = (row['id'],)
            data = self._read_from_sql(data_query, parameters)
            # Data is returned as a row of dicts, not very usefull....
            # Could also be retrived directly as a list
            x_values = []
            y_values = []
            for data_row in data:
                x_values.append(data_row['x'])
                y_values.append(data_row['y'])
            label = row['label']
            self.measurement[label] = {
                'metadata': row,
                'x_values': x_values,
                'y_values': y_values,
            }
        return True

    def data_summary(self):
        print('Summary of data:')
        first_row = True
        for label, data in self.measurement.items():
            # The comment will typically be the same for all rows
            # Time will always be the same, since is used as key for the measurement
            if first_row:
                print('Comment: {}'.format(data['metadata']['comment']))
                print('Time: {}'.format(data['metadata']['time']))
                print()
                first_row = False
            
            print('{} ({} rows):'.format(label, len(data['x_values'])))
            print('Metadata:')
            for key, value in data['metadata'].items():
                if key in ('time', 'comment', 'type', 'label', 'id'):
                    continue
                if value is None:
                    continue
                print('{}: {}'.format(key, value))
            print()

    def quick_plot(self, left_labels, right_labels=[]):
        # colors = ['b','g','r','c','m','y']
        colors = list(mcolors.XKCD_COLORS)

        fig = plt.figure()
        ax1 = fig.add_subplot(1, 1, 1)
        for label in left_labels:
            ax1.plot(
                self.measurement[label]['x_values'],
                self.measurement[label]['y_values'],
                color=colors.pop(), label=label
            )
        ax1.legend(loc=2, prop={"size": 8})

        if right_labels:
            ax1_2 = ax1.twinx()
            for label in right_labels:
                ax1_2.plot(
                    self.measurement[label]['x_values'],
                    self.measurement[label]['y_values'],
                    color=colors.pop(), label=label
                )
        ax1_2.legend(loc=4, prop={"size": 8})
        plt.show()

            
if __name__ == '__main__':
    DBREADER = DatabaseReader()

    setup = 'probe_station_ii'

    DBREADER.read_measurement(setup, '2026-09-23 13:35:44')
    DBREADER.data_summary()
    DBREADER.quick_plot(['Vtotal', 'Vsource'], ['Current'])
