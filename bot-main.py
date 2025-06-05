import json
import logging
import re
import getpass
import os
import platform
import pathlib
import argparse
import asyncio
from __autopath__ import path as path
import selenium.webdriver as Driver
import selenium.webdriver.common.keys as Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common import exceptions as exceptions

EXIT_FAILURE = 1


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
    __usrGlobalInfo__ = {}
    __loopMaximumRefresh = 10
    __googleGateway = '8.8.8.8'

    def __init__(self, *args):
        options = Driver.ChromeOptions()
        options.add_argument("-devtools-flags")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--display=:1")
        options.add_argument("--disable-auto-reload")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        self.driver = Driver.Chrome(options=options)
        self.logger = logging.getLogger(__name__)
        self.status = 0
        super().__init__()

    async def __refresh(self, timeout):
        cliargs = "-n 3 -l 32 -w 3 >" if platform.system() == "Windows" else "-c 4 -W 3 -s 32"
        def isNetworkConnected(): return os.system(
            'ping' + self.__googleGateway + cliargs + '>' + os.devnull)
        for i in range(self.__loopMaximumRefresh):
            await asyncio.sleep(timeout)
            if (not isNetworkConnected()):
                self.driver.refresh()

    def __getDOMObjectById(self, __id: str):
        return self.driver.find_element(By.ID, __id)

    def __sendKeyActionToDOMObj(self, obj, action=""):
        obj.clear()
        obj.send_keys(action)

    def loadPage(self, __url: str, timeout: int):
        self.logger.info(f"Loading page@{__url}")
        self.driver.set_page_load_timeout(timeout)
        try:
            self.driver.get(__url)
        except Exception:
            self.logger.error("unable to load page")
            self.status = EXIT_FAILURE
            self.closePage()
        self.driver.implicitly_wait(10)

    def authenticateUser(self, __id: str, __passwd: str, timeout: int):
        if __id == "" or __passwd == "":
            self.logger.error("[authentication failed] No name or password")
            self.status = EXIT_FAILURE
            self.closePage()

        self.__sendKeyActionToDOMObj(
            self.__getDOMObjectById(self.request("auth-id")), __id)
        self.__sendKeyActionToDOMObj(self.__getDOMObjectById(
            self.request("auth-passwd")), __passwd)
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
            self.status = EXIT_FAILURE
            self.logger.error(f"Authentication failed: {error}")
            self.closePage()
        except exceptions.TimeoutException:
            # TODO: if we get here, that is error may probably be due to unavailable/slow network and 'refresh' is enabled, refresh browser and try again
            self.logger.warning("Check your internet connection")
            self.status = EXIT_FAILURE
            self.closePage()

        # No error

    def getRegistrationData(self, __file: str):
        with open(__file, "r") as data:
            try:
                for __dat in [data.readline()]:
                    name, contact = re.split(r"\s+?\d", __dat.rstrip("\n"))
                    self.__usrGlobalInfo__.update({name: contact})
            except Exception:
                self.logger.error(f"error parsing input@line;{data.tell()}")
                self.status = EXIT_FAILURE
                self.closePage()

    def register(self, default):
        for name, contact in self.__usrGlobalInfo__.items():
            # TODO: page requires a selction of gender [IMPORTANT]
            gender = "M"
            firstname, lastname = name.split(" ", 1), None
            if not len(firstname[0]):
                self.logger.warning("[skipping] No user name")
                continue
            lastname = firstname if lastname == None else lastname
            if not (contact.isdigit() and [10, 11].count(len(contact))) or (contact == "Nil"):
                contact = default.get("contact")
            '''
                Manipulate DOM objects
            '''
            self.__sendKeyActionToDOMObj(self.__getDOMObjectById(
                self.request("user-first-name")), firstname[0])
            self.__sendKeyActionToDOMObj(self.__getDOMObjectById(
                self.request("user-other-name")), lastname[0])
            self.__sendKeyActionToDOMObj(self.__getDOMObjectById(
                self.request("city")), default.get("city"))
            self.__sendKeyActionToDOMObj(self.__getDOMObjectById(
                self.request("phone-number")), contact)
            Select(self.__getDOMObjectById(self.request(
                "gender"))).select_by_value(gender)
            Select(self.__getDOMObjectById(self.request("country"))
                   ).select_by_value(default.get("country"))
            self.__getDOMObjectById(self.request("accept-terms")).click()
            self.__getDOMObjectById(self.request("action")).click()
            try:
                '''
                    A feedback Object pops up if action (submit) is successful. Lets close it!
                '''
                alert = WebDriverWait(self.driver, default.timeout).until(EC.any_of(
                    EC.presence_of_element_located(
                        (By.ID, self.request("feedback"))),
                    EC.visibility_of_element_located((By.ID, self.request("feedback")))))
                alert.find_element(
                    By.TAG_NAME, self.request("close-alert")).click()
            except Exception:
                self.logger.warning(
                    "some error occurred which may either be from incomplete or incorrect data")
                continue

    def closePage(self):
        self.driver.quit()
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
                        type=int, default=60000)
    parser.add_argument('-r', '--response-timeout',
                        metavar="<int>", type=int, default=3000)
    parser.add_argument('-b', '--browser',
                        metavar='<browser>', type=str, default='chrome', help='select browser (default: chrome)')
    parser.add_argument('-n', '--norefresh',
                        metavar="<Bool>", type=bool, default=True, help='disable refreshing page after timeout expires')
    parser.add_argument('--key-path', metavar='<path>', type=str,
                        default='./key.txt", help="alternate location to get key file')
    parser.add_argument('--mouse-action', metavar='<int>', type=int,
                        default=0, help='implemenent mouse action')
    parser.add_argument('--allow-refresh', metavar='<int>', type=int,
                        default=0, help='allow page refresh after subsequent timeouts')

    cli = parser.parse_args()

    try:
        passwd = getpass.getpass(
            "Enter Authentication Token: ") if cli.user is not None else None
    except KeyboardInterrupt:
        exit(EXIT_FAILURE)

    with open("default.json", "r+") as default:
        setup = json.load(default)
        if (cli.update_attributes is not None):
            for attribute, value in cli.update_attributes.items():
                setup.update({attribute: value})
                # TODO: dump update to file

    # lambda
    def choose(case, default, action=None): return case if case is not None else action(
        default) if action else default

    # Add response timeout to attributes just incase it's needed
    setup.update({"timeout": cli.response_timeout})

    action = AutoRegister()
    action.getRegistrationData(setup.get("input-file"))
    action.loadPage(setup.get("url"), cli.page_timeout)
    action.authenticateUser(
        choose(cli.user, "username", setup.get),
        choose(passwd, "password", setup.get),
        cli.response_timeout)
    action.register(setup)
    action.closePage()

    print(action.__usrGlobalInfo__)


if __name__ == "__main__":
    __main__()
    ''' TODO: verify authentication success
        re
    '''
