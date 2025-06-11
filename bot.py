import json
import logging
import re
import getpass
import os
import platform
import pathlib
import argparse
import asyncio
import time
import socket
import random
from __autopath__ import path as path
from cryptography.fernet import Fernet
import selenium.webdriver as Driver
from selenium.webdriver import ActionChains
import selenium.webdriver.common.keys as Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common import exceptions as exceptions
import sys

EVENTS = {
    "critical error",
    "error generated"
    "Warning",
    "Info"
}
MESSAGES = [
    "Authentication Failed with error:",
    "Unable to load page, check your internet connection/rerun program",
    "Slow network",
    "Error processing input from file:",
    "An unexpected error occured"
]

'''
    Convert cmdline type to dict ('[key1: value1, ...]' -> {key1: value1, ...})
'''


class update(argparse.Action, path):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs is required disabled")
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        _Attribute = {}
        if re.match(r'^\[.*\]*$', str(values)) is None:
            parser.error(f"'{values}' doesn't follow pattern [M: N, ...]")
        for i in re.split(r',\s*', str(values)[1:-1]):
            attr = re.split(r'\s*:\s*', i)
            if len(attr) < 2 or attr.count(""):
                parser.error("In '{}', '{}' is less than required {option}".format(
                    values, attr, option=f"\nrun '{__file__} --help' to see usage of '{option_string}'"))
            _Attribute.update({attr[0]: attr[1]})

        # Verify attributes

        gkeys = set(self.attributes().keys())  # get internal attributes
        '''Any difference in the properties of the 'set' of expected
        	attribute keys when united with a corresponding 'set' of unknown
        	attribute keys, shows that the unknown is an/contasins erroneous value(s)
        '''
        if len(gkeys.union(set(_Attribute.keys()))) != len(gkeys):
            parser.error(
                f"unrecognized attribute key(s) '{list(set(_Attribute.keys()).difference(gkeys))}' in '{str(values)}'\nrun '{__file__} --list-attributes' to see list of available attributes ")

        # update parser with attributes <dict>: var.option_string recieves a new value of value @_Attribute
        setattr(namespace, self.dest, _Attribute)


class AutoRegister(path):
    __globalAsyncNmRefresh = 15
    __googleGateway = '8.8.8.8'

    _PAGE_LOAD = 0x100
    _AUTH_SUCCESS = 0x80
    _DATA_READY = 0x40
    _DATA_DONE = 0x20
    _RETRY = 0x10
    _CONNECT_FAILED = 0x08
    _CONNECT_SUCCESS = 0x04
    _END_RETRY = 0x00

    _EXIT_FAILURE = 0xff

    def __init__(self, setup):
        options = Driver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--display=:1")
        options.add_argument("--disable-auto-reload")
        options.add_argument("--headless") if setup.get("headless") else True
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        self.options = options
        self.setup = setup
        self.__usrGlobalInfo__: dict = {}
        self.logger = logging.getLogger(__name__)
        self.animate = True
        self.status = 0

    def refreshLoop(self):
        timeout = self.setup.get("refresh")
        tcpport = 53
        if (timeout < 1):
            return None
        socket.setdefaulttimeout(5)
        net = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        def refresh():
            for loop in range(self.__globalAsyncNmRefresh):
                print("refreshing")
                try:
                    net.connect((self.__googleGateway, tcpport))
                    return self._CONNECT_SUCCESS
                except Exception:
                    self.driver.refresh()
                time.sleep(10)
            return self._CONNECT_FAILED

        while (True):
            self.__pause(self._RETRY)
            self.status |= refresh()
            if (self.status == self._CONNECT_FAILED):
                # Exceeded loop limit
                socket.socket.close(net)
                break

    def __error(self, msg, **kwargs):
        tm = time.localtime()
        def rj(x): return str(x).rjust(2, '0')
        tm = f'{rj(tm.tm_hour)}:{rj(tm.tm_min)}:{rj(tm.tm_sec)}'
        def termrj(x): return int((os.get_terminal_size().columns - x)/2)
        print(f"{'LOG OUTPUT'.rjust(termrj(10))}\n"
              + f"% Event:   {" "}\n"
              + f"% Trace:   {pathlib.PurePath(__file__).name}:{__name__.strip("_")}-{tm}-<session_id: {self.driver.session_id}>\n"
              + f"% Message: {msg} <{""}>\n"
              + f"% Status:  {'stopped' if self.status else 'running'}")

    def __getDOMObjectById(self, __id: str):
        return self.driver.find_element(By.ID, __id)

    def __animate(self, obj, action: str, /, a=0.05, b=0.15, mean=0.001, pause=0.001):
        time.sleep(pause)
        ActionChains(self.driver).scroll_to_element(obj).perform()
        time.sleep(pause)
        for i in action:
            obj.send_keys(i)
            time.sleep(random.triangular(a, b, mean)
                       ) if i != " " else time.sleep(.3)

    def __sendKeyActionToDOMObj(self, obj, action=""):
        obj.clear()
        self.__animate(
            obj, action) if self.animate is True else obj.send_keys(action)

    def __pause(self, status):
        while (not (self.status & status) and (self.status != self._EXIT_FAILURE)):
            pass
        return self.status

    def loadPage(self):
        try:
            self.driver = Driver.Chrome(options=self.options)
            self.driver.set_page_load_timeout(self.setup.get("page-timeout"))
            self.driver.get(self.setup.get("url"))
        except exceptions.WebDriverException:
            self.logger.error("unable to load page")
            if (self.setup.get("refresh") < 1):
                self.status = self._EXIT_FAILURE
                self.closePage()
            self.status = self._RETRY
            # wait and retry connection
            self.__pause(self._CONNECT_FAILED | self._CONNECT_SUCCESS)
            if self.status & self._CONNECT_FAILED:
                self.status = self._EXIT_FAILURE
                self.closePage()
        self.status = self._PAGE_LOAD

    def authenticateUser(self):
        timeout = self.setup.get("response-timeout")
        id = self.setup.pop("username")
        passwd = self.setup.pop("password")
        if id == "" or passwd == "":
            self.logger.error("[authentication failed] No name or password")
            self.status = self._EXIT_FAILURE
            self.closePage()

        # wait until page source is read
        if (self.__pause(self._PAGE_LOAD) == self._EXIT_FAILURE):
            return
        self.__sendKeyActionToDOMObj(
            self.__getDOMObjectById(self.request("auth-id")), id)
        self.__sendKeyActionToDOMObj(self.__getDOMObjectById(
            self.request("auth-passwd")), passwd)
        self.driver.find_element(By.ID, self.request("auth-action")).click()
        try:
            '''
                Assert if an authentication error occured
            '''
            error = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((By.ID, self.request("auth-feedback"))))
            if error.is_displayed():
                raise exceptions.InvalidArgumentException(error.text)
            '''
                Wait for page to load
            '''
            WebDriverWait(self.driver, timeout).until(
                EC.title_is(self.request("home-page-title")))
        except exceptions.InvalidArgumentException as error:
            self.status = self._EXIT_FAILURE
            self.logger.error(f"Authentication failed: {error}")
            self.closePage()
        except exceptions.TimeoutException:
            # TODO: if we get here, that is error may probably be due to unavailable/slow network and 'refresh' is enabled, refresh browser and try again
            self.logger.warning("Check your internet connection")
            self.status = self._EXIT_FAILURE
            self.closePage()
        self.status = self._AUTH_SUCCESS

    def getRegistrationData(self):
        with open(self.setup.get("input-file"), "r") as data:
            try:
                for __dat in data.readlines():
                    name, contact = re.split(r"\s+?\d", __dat.rstrip("\n"))
                    self.__usrGlobalInfo__.update({name: contact})
                    self.status |= self._DATA_READY
                    print('running', flush=True)
            except Exception as error:
                self.logger.error(error)
            self.status = self._DATA_DONE
            return 0

    def register(self):
        if (self.__pause(self._AUTH_SUCCESS | self._DATA_READY) == self._EXIT_FAILURE):
            return

        while (True):
            if ((self.status == self._DATA_DONE) and not len(self.__usrGlobalInfo__)):
                break
            name, contact = self.__usrGlobalInfo__.popitem()
            gender = "M"
            firstname, lastname = name.split(" ", 1), None
            if not len(firstname[0]):
                self.logger.warning("[skipping] No user name")
                continue
            lastname = firstname if lastname == None else lastname
            if not (contact.isdigit() and [10, 11].count(len(contact))) or (contact == "Nil"):
                contact = self.setup.get("contact")
            '''
                Manipulate DOM objects
            '''
            self.__sendKeyActionToDOMObj(self.__getDOMObjectById(
                self.request("user-first-name")), firstname[0])
            self.__sendKeyActionToDOMObj(self.__getDOMObjectById(
                self.request("user-other-name")), lastname[0])
            self.__sendKeyActionToDOMObj(self.__getDOMObjectById(
                self.request("city")), self.setup.get("city"))
            self.__sendKeyActionToDOMObj(self.__getDOMObjectById(
                self.request("phone-number")), contact)
            Select(self.__getDOMObjectById(
                self.request("gender"))).select_by_value(gender)
            Select(self.__getDOMObjectById(self.request("country"))
                   ).select_by_value(self.setup.get("country"))
            self.__getDOMObjectById(self.request("accept-terms")).click()
            self.__getDOMObjectById(self.request("action")).click()

            try:
                '''
                    A feedback Object pops up if action (submit) is successful. Lets close it!
                '''
                alert = WebDriverWait(self.driver, self.setup.get("response-timeout")).until(EC.any_of(
                    EC.presence_of_element_located(
                        (By.ID, self.request("feedback"))),
                    EC.visibility_of_element_located((By.ID, self.request("feedback")))))
                alert.find_element(
                    By.TAG_NAME, self.request("close-alert")).click()
            except Exception:
                self.logger.warning(
                    "some error occurred which may either be from incomplete or incorrect data")

    def closePage(self):
        # quit ^refresh if enabled
        self.__globalAsyncNmRefresh = 0
        # close browser and driver
        self.driver.quit()
        # TODO: print an exit log
        exit(self.status)


def __main__():
    # Clear console screen
    os.system("cls" if platform.system() == "Windows" else "clear")

    # Handle command line arguments
    parser = argparse.ArgumentParser(prog="Auto Register Souls", description="Automatically register/update souls information on site",
                                     fromfile_prefix_chars='@')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-v', '--verbose', action='store_true')
    group.add_argument(
        '-q', '--quiet', action='store_true', default='true')
    parser.add_argument('-u', '--user', help='sets authentication user-name',
                        metavar='<str>', type=str, default=None)
    parser.add_argument(
        '-a', '--update-attributes', metavar='<[key: value, ...]>', action=update, help='updates internal defined attributes')
    parser.add_argument('-p', '--page-timeout', metavar="<int>",
                        type=int, default=3000)
    parser.add_argument('-r', '--response-timeout',
                        metavar="<int>", type=int, default=3000)
    parser.add_argument('-b', '--browser',
                        metavar='<browser>', type=str, default='chrome', help='select browser (default: chrome)')
    parser.add_argument('--key-path', metavar='<path>', type=str,
                        default='./key.txt", help="alternate location to get key file')
    parser.add_argument('--animate', metavar='<int>', type=int,
                        default=0, help='enable animation')
    parser.add_argument('--refresh', metavar='<int>', type=int,
                        default=0, help='enable automatic page refresh after timeout')
    parser.add_argument('--headless', metavar='<bool>', type=bool,
                        default=False, help='disable browser window (background mode)')

    cli = parser.parse_args()

    try:
        passwd = getpass.getpass(
            "Enter Authentication Token: ") if cli.user is not None else None
    except KeyboardInterrupt:
        exit(-1)

    with open("default.json", "r+") as default:
        setup = json.load(default)
        if (cli.update_attributes is not None):
            setup.update(cli.update_attributes)
            # TODO: dump update to file

    # choose a case, if untrue perfom a default action
    def choose(case, default, action): return case if case is not None else action(
        default)

    # Add response timeout to attributes just incase it's needed
    setup.update({
        "password": choose(passwd, "password", setup.get),
        "username": choose(cli.user, "username", setup.get),
        "response-timeout": cli.response_timeout,
        "page-timeout": cli.page_timeout,
        "refresh": cli.refresh,
        "browser": cli.browser,
        "animate": cli.animate,
        "headless": cli.headless
    })

    action = AutoRegister(setup)
    try:
        from threading import Thread as Thread

        events = [
            action.loadPage,
            action.getRegistrationData,
            action.refreshLoop,
            action.authenticateUser,
            action.register
        ]
        eventThreadList = [Thread(None, event) for event in events]
        for r_exec in eventThreadList:
            r_exec.start()
        for wait in eventThreadList:
            wait.join()
    except:
        print("error")

    print(action.__usrGlobalInfo__)

if __name__ == "__main__":
    __main__()
