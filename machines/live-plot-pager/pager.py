#!/usr/bin/env python

"""The super fancy presentation system"""

import os
import time
import xml.etree.ElementTree as XML
import socket
from subprocess import call
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains


def get_chromium():
    """Returns a chromium webdriver"""
    chromedriver = '/usr/lib/chromium-browser/chromedriver'
    os.environ["webdriver.chrome.driver"] = chromedriver
    os.environ["LD_LIBRARY_PATH"] = '/usr/lib/chromium-browser/libs/'
    return webdriver.Chrome(chromedriver)


def get_firefox():
    """Returns a Firefox webdriver"""
    return webdriver.Firefox()


def new_tab(driver):
    """Opens a new tab"""
    ActionChains(driver).key_down(Keys.CONTROL).send_keys('t').\
        key_up(Keys.CONTROL).perform()


def close_tab(driver):
    """Opens a new tab"""
    ActionChains(driver).key_down(Keys.CONTROL).send_keys('w').\
        key_up(Keys.CONTROL).perform()


def next_tab(driver):
    """Switches to the next tab"""
    ActionChains(driver).key_down(Keys.CONTROL).send_keys(Keys.PAGE_DOWN).\
        key_up(Keys.CONTROL).perform()


def fullscreen(driver):
    """Send the browser to full screen mode (F11)"""
    ActionChains(driver).send_keys(Keys.F11).perform()


def refresh(driver):
    """Refreshes the browser"""
    driver.refresh()


def typed_element(element):
    """Return the type converted value of an element"""
    if 'type' in element.attrib:
        type_conversion = getattr(__builtins__, element.attrib['type'])
        return type_conversion(element.text)
    else:
        return element.text


def get_settings(root):
    """Returns the settings from the settings files"""
    settings_list = []
    for element in root.find('settings'):
        settings_list.append([element.tag, typed_element(element)])
    return dict(settings_list)


def get_pages(root):
    """Returns the pages from the settings file"""
    pages = []
    for page in root.find('pages'):
        page_list = []
        for element in page:
            page_list.append([element.tag, typed_element(element)])
        page_list.append(['last_update', time.time() - 3300])
        pages.append(dict(page_list))
    return pages


def main():
    """The main method"""
    driver = get_firefox()
    #driver = get_chromium()

    # Read in general and page settings
    pages = os.path.join(
        os.path.split(os.path.realpath(__file__))[0],
        'pages.xml'
    )
    tree = XML.parse(pages)
    root = tree.getroot()
    settings = get_settings(root)
    pages = get_pages(root)
    by_ids = dict([[d['id'], d] for d in pages])

    # Load
    for page in pages:
        new_tab(driver)
        driver.get(page['url'])
        driver.execute_script(
            'document.title = "{}";'.format(page['id'])
        )
    next_tab(driver)
    close_tab(driver)
    print 'fullscreen'
    fullscreen(driver)
    time.sleep(2)
    fullscreen(driver)
    time.sleep(2)
    fullscreen(driver)
    time.sleep(6)
    print 'move mouse'
    #for pos in range(100, 600, 1):
    #    call(['xdotool', 'mousemove', str(pos), str(pos)])
    #    time.sleep(0.01)
    call(['xdotool', 'mousemove', '0', '0'])
    time.sleep(2)
    fullscreen(driver)
    time.sleep(2)
    fullscreen(driver)
    time.sleep(2)

    # Switch
    try:
        while True:
            next_tab(driver)
            last_update = by_ids[driver.title]['last_update']
            if time.time() - last_update > 3600:
                remember_title = driver.title
                print 'refreshing', driver.title
                refresh(driver)
                driver.execute_script(
                    'document.title = "{}";'.format(remember_title)
                    )
                by_ids[driver.title]['last_update'] = time.time()

            waittime = by_ids[driver.title]['show_factor'] *\
                settings['standard_showtime']
            print 'showing:', driver.title, 'for', waittime, 'seconds'
            time.sleep(waittime)
    except KeyboardInterrupt:
        print 'shutting down'
        try:
            driver.close()
        except socket.error:
            return

main()
