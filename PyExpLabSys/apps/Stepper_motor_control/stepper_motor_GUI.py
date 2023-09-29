# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets
from stepper_motor_GUI_design import stepper_motor_ui
import sys
import threading
import time
import socket
import json
from datetime import datetime


# The update_GUI function is a threaded function updating the GUI with some chosen parameters
# The data is received from the motor drivers through a socket running on a raspberry pi
# It will also check if a update is finished to signal the table_update function to write to the tables
class update_GUI(QtCore.QThread):
    data_update = QtCore.pyqtSignal(object)

    def __init__(self):
        QtCore.QThread.__init__(self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.update_check = False

    def run(self):
        command = 'json_wn'
        host_port = ('rasppi134', 9000)
        while True:
            self.sock.sendto(command.encode('ascii'), host_port)
            received = json.loads(self.sock.recv(2048).decode())
            self.update_check = received['update_check'][1]
            self.data_update.emit(received)
            time.sleep(0.2)


# The GUI class is where changes to the GUI are performed
# The GUI layout is loaded in from the script stepper_motor_GUI_design
class stepper_motor_GUI(object):
    def __init__(self):
        super(stepper_motor_GUI, self).__init__()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.MainWindow = QtWidgets.QMainWindow()
        self.gui = stepper_motor_ui()
        self.gui.setupUi(self.MainWindow)
        self.gui.pushButton.clicked.connect(lambda: self.confirmation_box('home'))
        self.gui.pushButton_2.clicked.connect(lambda: self.confirmation_box('ISS'))
        self.gui.pushButton_3.clicked.connect(lambda: self.confirmation_box('Mg_XPS'))
        self.gui.pushButton_14.clicked.connect(lambda: self.confirmation_box('Al_XPS'))
        self.gui.pushButton_11.clicked.connect(lambda: self.confirmation_box('SIG'))
        self.gui.pushButton_4.clicked.connect(lambda: self.confirmation_box('HPC'))
        self.gui.pushButton_15.clicked.connect(lambda: self.confirmation_box('Baking'))
        self.gui.pushButton_6.clicked.connect(lambda: self.send_command('stop'))
        self.gui.pushButton_5.clicked.connect(self.move_command)
        self.gui.pushButton_7.clicked.connect(lambda: self.send_command('reset_alarms'))
        self.gui.pushButton_8.clicked.connect(
            lambda: self.alarm_record('show_alarm_record')
        )
        self.gui.pushButton_10.clicked.connect(
            lambda: self.alarm_record('clear_alarm_record')
        )
        self.gui.pushButton_9.clicked.connect(lambda: self.send_command('clear_ETO'))
        self.gui.pushButton_12.clicked.connect(lambda: self.update_trigger('update'))
        self.gui.pushButton_13.clicked.connect(lambda: self.update_trigger('save'))

        self.constant_update = update_GUI()
        self.constant_update.data_update.connect(
            self.update,
        )
        self.constant_update.start()
        self.table_update()
        self.update_start = False
        self.save_start = False
        self.message = ''

    # The update function is threaded and update certain status and location information
    def update(self, data):
        Mg_XPS = data['Mg_XPS']
        Al_XPS = data['Al_XPS']
        ISS = data['ISS']
        SIG = data['SIG']
        HPC = data['HPC']
        Baking = data['Baking']

        color = ['red', 'green']
        self.gui.label_6.setStyleSheet(
            "background-color: {}".format(color[data['status'][0]])
        )
        self.gui.label_7.setStyleSheet(
            "background-color: {}".format(color[data['status'][1]])
        )
        self.gui.label_8.setStyleSheet(
            "background-color: {}".format(color[data['status'][2]])
        )
        self.gui.label_9.setStyleSheet(
            "background-color: {}".format(color[data['status'][3]])
        )
        if data['move'] == [0, 0, 0]:
            self.gui.label_14.setStyleSheet("background-color: {}".format(color[1]))
        else:
            self.gui.label_14.setStyleSheet("background-color: {}".format(color[0]))
        if data['command_position'] == [0, 0, 0]:
            self.gui.label_15.setStyleSheet("background-color: {}".format(color[1]))
        else:
            self.gui.label_15.setStyleSheet("background-color: {}".format(color[0]))
        if data['command_position'] == ISS:
            self.gui.label_16.setStyleSheet("background-color: {}".format(color[1]))
        else:
            self.gui.label_16.setStyleSheet("background-color: {}".format(color[0]))
        if data['command_position'] == Mg_XPS:
            self.gui.label_17.setStyleSheet("background-color: {}".format(color[1]))
        else:
            self.gui.label_17.setStyleSheet("background-color: {}".format(color[0]))
        if data['command_position'] == Al_XPS:
            self.gui.label_31.setStyleSheet("background-color: {}".format(color[1]))
        else:
            self.gui.label_31.setStyleSheet("background-color: {}".format(color[0]))
        if data['command_position'] == HPC:
            self.gui.label_23.setStyleSheet("background-color: {}".format(color[1]))
        else:
            self.gui.label_23.setStyleSheet("background-color: {}".format(color[0]))
        if data['command_position'] == SIG:
            self.gui.label_29.setStyleSheet("background-color: {}".format(color[1]))
        else:
            self.gui.label_29.setStyleSheet("background-color: {}".format(color[0]))
        if data['command_position'] == Baking:
            self.gui.label_33.setStyleSheet("background-color: {}".format(color[1]))
        else:
            self.gui.label_33.setStyleSheet("background-color: {}".format(color[0]))
        self.gui.label_19.setText("X: {} mm".format(data['command_position'][0]))
        self.gui.label_20.setText("Y: {} mm".format(data['command_position'][1]))
        self.gui.label_21.setText("Z: {} mm".format(data['command_position'][2]))
        # Calls the table update and save function if the buttons are pressed on the GUI
        if self.update_start == True:
            self.table_update()
            self.update_start = False
        if self.save_start == True:
            self.table_save()
            self.save_start = False
        # Reads the current message from the socket and checks if it is a new message
        # If alarm_record is received the 10 latest alarms will be displayed in the list widget
        # If a different message is received it is displayed in the list widget
        new_message = (
            '['
            + str(datetime.fromtimestamp(data['message'][0]))[11:19]
            + ']: '
            + str(data['message'][1])
        )
        if new_message != self.message and new_message != '[01:00:00]: 0.0':
            self.message = new_message
            if self.message[-14:-2] == 'alarm_record':
                alarm_record = data['message'][1]
                alarm_type = {
                    '0': 'No alarm',
                    '10': 'Excessive position deviation',
                    '20': 'Overcurrent',
                    '21': 'Main circuit overheat',
                    '22': 'Overvoltage (AC/DC power input driver)',
                    '23': 'Main power supply OFF',
                    '25': 'Undervoltage',
                    '26': 'Motor overheat',
                    '28': 'Sensor error',
                    '2A': 'ABZO sensor communication error',
                    '30': 'Overload',
                    '31': 'Overspeed',
                    '33': 'Absolute position error',
                    '34': 'Command pulse error',
                    '41': 'EEPROM error',
                    '42': 'Sensor error at power on',
                    '43': 'Rotation error at power on',
                    '44': 'Encoder EEPROM error',
                    '45': 'Motor combination error',
                    '4A': 'Return-to-home incomplete',
                    '51': 'Regeneration unit overheat (only AC power input driver)',
                    '53': 'Emergency stop circuit error',
                    '60': '±LS both sides active',
                    '61': 'Reverse ±LS connection',
                    '62': 'Return-to-home operation error',
                    '63': 'No HOMES',
                    '64': 'TIM, Z, SLIT signal error',
                    '66': 'Hardware overtravel',
                    '67': 'Software overtravel',
                    '68': 'Emergency stop',
                    '6A': 'Return-to-home operation offset error',
                    '6D': 'Mechanical overtravel',
                    '70': 'Operation data error',
                    '71': 'Electronic gear setting error',
                    '72': 'Wrap setting error',
                    '81': 'Network bus error',
                    '83': 'Communication switch setting error',
                    '84': 'RS-485 communication error',
                    '85': 'RS-485 communication timeout',
                    '8E': 'Network converter error',
                    'F0': 'CPU error',
                }
                for i in range(10):
                    alarm_record[i] = (
                        alarm_record[i] + ' ' + alarm_type[alarm_record[i]]
                    )
                self.gui.listWidget.addItem(
                    "Motor {} alarm record:".format(alarm_record[-2])
                )
                for i in range(10):
                    item = 'Alarm {}: {}'.format(i + 1, alarm_record[i])
                    self.gui.listWidget.addItem("{}".format(item))
            else:
                self.gui.listWidget.addItem("{}".format(self.message))

    # The confirmation_box function is called when a location button is hit
    # Displays a pop-out window with an okay and a cancel button
    # If okay is pressed the send_command function is called
    def confirmation_box(self, command):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)

        msg.setText("Move to {}".format(command))
        msg.setWindowTitle("Confirmation box")
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)

        value = msg.exec_()
        if value == QtWidgets.QMessageBox.Ok:
            command = 'move_' + command
            self.send_command(command)

    # Sends a command to the push socket that is then executed on the raspberry pi
    def send_command(self, command):
        host_port = ('rasppi134', 8500)
        message = (
            'raw_wn#command:str:'
            + '['
            + str(datetime.fromtimestamp(time.time()))[11:19].replace(':', '-')
            + '] '
            + command
        )
        self.sock.sendto(message.encode('ascii'), host_port)

    # The move_command function is called when the free movement button is pressed
    # Displays a pop-out window with an okay and cancel button
    # If okay is pressed the send_command function is called
    def move_command(self):
        mot_number = self.gui.comboBox_2.currentText()
        operation_type = self.gui.comboBox.currentText()
        position = self.gui.lineEdit.text()

        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText(
            "{} of motor {}: {} mm".format(operation_type, mot_number, position)
        )
        msg.setWindowTitle("Confirmation box")
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)

        value = msg.exec_()
        if value == QtWidgets.QMessageBox.Cancel:
            return

        if operation_type == 'Relative movement':
            command = 'relative' + str(mot_number) + str(position)
        if operation_type == 'Absolute movement':
            command = 'absolute' + str(mot_number) + str(position)
        self.send_command(command)

    # The alarm_record function sends a command to the raspberry pi to show or clear the alarm record
    # The raspberry pi sends its answer through the pull socket
    def alarm_record(self, command):
        if command == 'show_alarm_record':
            mot_number = self.gui.comboBox_4.currentText()
            command = command + str(mot_number)
        if command == 'clear_alarm_record':
            mot_number = self.gui.comboBox_5.currentText()
            command = command + str(mot_number)
        self.send_command(command)

    # The update_trigger function will call the table_update or table_save functions without calling them directly
    # This is done as to alow the screen to become opaque when the functions are being run
    # PyQt will not update the main GUI layout undtil a given function has been completed
    # Therefore the functions has to be called via a signal to the threaded update function
    def update_trigger(self, command):
        self.MainWindow.setWindowOpacity(0.9)
        if command == 'update':
            self.update_start = True
        if command == 'save':
            self.save_start = True

    # The table_update function pdates the table widgets with parameters and locations.
    # As this functions takes some time for the raspberry pi the function will wait for the pi to send a signal that it is done
    # Then the function writes the new data into the tables
    def table_update(self):
        self.send_command('table_update')

        while self.constant_update.update_check == False:
            time.sleep(0.1)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        command = 'json_wn'
        host_port = ('rasppi134', 9000)
        self.sock.sendto(command.encode('ascii'), host_port)
        data = json.loads(self.sock.recv(2048).decode())
        parameterlist = [
            'operating_speed',
            'starting_speed',
            'starting_changing_rate',
            'stopping_deceleration',
            'operating_current',
            'positive_software_limit',
            'negative_software_limit',
            'electronic_gear_A',
            'electronic_gear_B',
            'zhome_operating_speed',
            'zhome_starting_speed',
            'zhome_acceleration_deceleration',
            'group_id',
        ]
        for i in range(4):
            for n in range(13):
                item = QtWidgets.QTableWidgetItem(
                    '{}'.format(data[parameterlist[n]][i])
                )
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.gui.tableWidget.setItem(n, i, item)

        parameterlist = ['ISS', 'Mg_XPS', 'Al_XPS', 'SIG', 'HPC', 'Baking']

        for i in range(3):
            for n in range(6):
                item = QtWidgets.QTableWidgetItem(
                    '{}'.format(data[parameterlist[n]][i])
                )
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.gui.tableWidget_2.setItem(n, i, item)

        self.MainWindow.setWindowOpacity(1)

    # The table_save function reads the data in the tables and sends it to the raspberry pi where it is writen onto the motor drivers
    def table_save(self):
        parameterdic = {
            'command': '['
            + str(datetime.fromtimestamp(time.time()))[11:19].replace(':', '-')
            + '] '
            + 'table_save',
            'operating_speed': [0, 0, 0, 0],
            'starting_speed': [0, 0, 0, 0],
            'starting_changing_rate': [0, 0, 0, 0],
            'stopping_deceleration': [0, 0, 0, 0],
            'operating_current': [0, 0, 0, 0],
            'positive_software_limit': [0, 0, 0, 0],
            'negative_software_limit': [0, 0, 0, 0],
            'electronic_gear_A': [0, 0, 0, 0],
            'electronic_gear_B': [0, 0, 0, 0],
            'zhome_operating_speed': [0, 0, 0, 0],
            'zhome_starting_speed': [0, 0, 0, 0],
            'zhome_acceleration_deceleration': [0, 0, 0, 0],
            'group_id': [0, 0, 0, 0],
            'ISS': [0, 0, 0],
            'Mg_XPS': [0, 0, 0],
            'Al_XPS': [0, 0, 0],
            'SIG': [0, 0, 0],
            'HPC': [0, 0, 0],
            'Baking': [0, 0, 0],
        }
        item = self.gui.tableWidget.item(0, 0)
        for i in range(4):
            for n in range(1, 14):
                item = self.gui.tableWidget.item(n - 1, i)
                parameterdic[list(parameterdic.items())[n][0]][i] = float(item.text())

        for i in range(3):
            for n in range(14, 20):
                item = self.gui.tableWidget_2.item(n - 14, i)
                parameterdic[list(parameterdic.items())[n][0]][i] = float(item.text())
        message = 'json_wn#' + json.dumps(parameterdic)
        host_port = ('rasppi134', 8500)
        self.sock.sendto(message.encode('ascii'), host_port)
        self.MainWindow.setWindowOpacity(1)


# Runs the stepper_motor_GUI class when the scripts is opened
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    runapp = stepper_motor_GUI()
    runapp.MainWindow.show()
    sys.exit(app.exec_())
