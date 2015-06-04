""" Module to run a graphical logbook of a specific area """
import cv
import time
import MySQLdb
from PyExpLabSys.common.utilities import get_logger
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.drivers.vivo_technologies import ThreadedBarcodeReader, detect_barcode_device
import sys

sys.path.append('/home/pi/PyExpLabSys/machines/' + sys.argv[1])
import settings # pylint: disable=F0401

LOGGER = get_logger('Picture_Logbook')

class PictureLogbook(object):
    """ Handle login and logout of users """

    def __init__(self):
        LOGGER.info('Started Picture Logbook')

        dev_ = detect_barcode_device()
        LOGGER.info('Barcode device: ' +  dev_)
        self.tbs = ThreadedBarcodeReader(dev_)
        self.tbs.start()

        self.setup = settings.setup

        self.livesocket = LiveSocket(self.setup + '-Picture Logbook', ['logged_in_user'], 1)
        self.livesocket.start()

        self.force_logout_user = settings.force_logut_user
        self.camera = cv.CaptureFromCAM(0)
        cv.SetCaptureProperty(self.camera, cv.CV_CAP_PROP_FRAME_WIDTH, 320)
        cv.SetCaptureProperty(self.camera, cv.CV_CAP_PROP_FRAME_HEIGHT, 240)
        self.database = MySQLdb.connect(host='servcinf', user='picturelogbook',
                                        passwd='picturelogbook', db='cinfdata')

        query = 'select user, login from picture_logbooks where setup = "'
        query += self.setup + '" order by time desc limit 1'
        cursor = self.database.cursor()
        cursor.execute(query)
        current_state = cursor.fetchone()
        current_login = current_state[1]
        if current_login == 0:
            self.logged_in_user = None
        else:
            self.logged_in_user = current_state[0]
        LOGGER.info('Initially logged in user:' + str(self.logged_in_user))


    def acquire_image(self):
        """ Take an image and return it as a string
        :return: jpg image represented as a string
        :rtype: string
        """
        frame = cv.QueryFrame(self.camera)
        picture = cv.EncodeImage(".jpg", frame).tostring()
        return picture

    def save_image(self, image):
        """ Save an image to the database
        :param image: String enocde image
        :return: Database id of the image
        :rtype: int
        """
        query = 'insert into binary_data set data = "' + image + '"'
        query = '''insert into binary_data (data) VALUES (%s)'''
        cursor = self.database.cursor()
        cursor.execute(query, (image,))
        self.database.commit()

        query = 'select id from binary_data order by id desc limit 1'
        cursor.execute(query)
        id_number = cursor.fetchone()
        id_number = id_number[0]
        return id_number

    def update_logged_in_user(self, user, force_logout=False):
        """ Perfom a login on the lab station.
        If the user is already logged in, the user will be logged out.
        If another user is logged in, the login attempt will fail
        return: 'login' if login, 'logout' of logout, 'failed' if login failed
        rtype: string
        """
        LOGGER.info('User: ' + user + ',  loged in user: ' + str(self.logged_in_user))
        action = None
        if self.logged_in_user is None:
            self.logged_in_user = user
            action = 'login'
        elif (user == self.logged_in_user) or (force_logout is True):
            self.logged_in_user = None
            action = 'logout'
        elif user is not self.logged_in_user:
            action = 'failed'
        assert action is not None
        return action

    def login(self, user, force_logout=False):
        """ Perform a login or logout
        On login, take a picture, update database
        On logout, clear logged in user, update database
        """
        # Here we should take a picture and update databases
        action = self.update_logged_in_user(user, force_logout)
        if not action in ('login', 'logout'): # Login failed
            return None

        image = self.acquire_image()
        id_number = self.save_image(image)
        query = 'insert into picture_logbooks set setup = "' + self.setup + '", '
        query += 'user = "' + user + '", pictureid=' + str(id_number) + ', '
        login = action is 'login'       
        query += 'login = ' + str(login)
        LOGGER.info(query)
        cursor = self.database.cursor()
        cursor.execute(query)
        self.database.commit()

    def main(self):
        """ Main loop """
        while True:
            username = self.tbs.last_barcode_in_queue
            if username is not None:
                username = str(username)
                LOGGER.info('Attempt to login: ' + username)
                force = (username == self.force_logout_user)
                print self.login(username, force_logout=force)
            else:
                print '-'
            time.sleep(2)

if __name__ == '__main__':
    LOGBOOK = PictureLogbook()
    LOGBOOK.main()
