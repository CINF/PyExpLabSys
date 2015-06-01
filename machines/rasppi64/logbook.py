# pylint: disable=E1103
import cv
import MySQLdb
from PyExpLabSys.common.utilities import get_logger
#from PyExpLabSys.drivers.vivo_technologies import BlockingBarcodeReader

LOGGER = get_logger('Picture_Logbook')

class PictureLogbook(object):
    """ Handle login and logout of users """

    def __init__(self):
        LOGGER.info('Started Picture Logbook')
        self.logged_in_user = None
        self.camera = cv.CaptureFromCAM(0)
        cv.SetCaptureProperty(self.camera, cv.CV_CAP_PROP_FRAME_WIDTH, 320)
        cv.SetCaptureProperty(self.camera, cv.CV_CAP_PROP_FRAME_HEIGHT, 240)
        self.database = MySQLdb.connect(host='servcinf', user='picturelogbook',
                                        passwd='picturelogbook', db='cinfdata')

    def acquire_image(self):
        """ Take an image and return it as a string
        :return: jpg image represented as a string
        :rtype: string
        """
        frame = cv.QueryFrame(self.camera)
        picture = cv.EncodeImage(".jpg", frame).tostring()
        #open("encode_image.jpg", "w").write(picture) 
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
        print '-'
        query = 'select id from binary_data order by id desc limit 1'
        cursor.execute(query)
        id_number = cursor.fetchone()
        id_number = id_number[0]
        return id_number

    def update_logged_in_user(self, user):
        """ Perfom a login on the lab station.
        If the user is already logged in, the user will be logged out.
        If another user is logged in, the login attempt will fail
        return: True if login or logut is succesfull, otherwise false
        rtype: bool
        """
        if self.logged_in_user is None:
            self.logged_in_user = user
            print('login')
        elif user == self.logged_in_user:
            self.logged_in_user = None
            print('logout')
        
    def login(self, user):
        """ Perform a login or logout
        On login, take a picture, update database
        On logout, clear logged in user, update database
        """
        # Here we should take a picture and update databases
        pass

if __name__ == '__main__':
    logbook = PictureLogbook()
    logbook.update_logged_in_user('roje')
    logbook.update_logged_in_user('roje')
    logbook.update_logged_in_user('roje')

