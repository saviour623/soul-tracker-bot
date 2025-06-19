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
import threading

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
    "Registered {name} successfully ({time.asctime})"
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
    __nretry = 3
    __totalTask     = 0 # buffer
    __completed = 0 # counter

    _START           = 0b1000000
    _PAGE_LOAD       = 0b1100000
    _AUTH_SUCCESS    = 0b1010000
    _DATA_READY      = 0b1001000
    _DATA_DONE       = 0b1000100
    _RETRY           = 0b1000010
    _CONNECT_SUCCESS = 0b1000001
    _STOP            = 0b0

    def __init__(self, setup):
        options = Driver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--display=:1")
        options.add_argument("--disable-auto-reload")
        options.add_argument("--headless") if setup.get("headless") else True
        options.add_argument("--disable-link-features=AutomationControlled")
        options.add_experimental_option(
            'excludeSwitches', ['enable-logging', 'enable-authomation'])
        options.add_experimental_option('useAutomationExtension', False)
        self.options = options
        self.setup   = setup
        self.__register: list = []
        self.logger  = logging.getLogger(__name__)
        self.animate = True
        self.status  = self._START

    def __enter__(self):
        '''
            Start session (contextManager)
        '''
        return self

    def __exit__(self, exc_Type, exc_Msg, exc_Trace):
        '''
            End session (contextManager)
        '''
        self.closePage(None, exc_Type, exc_Msg, exc_Trace)

    def __notify(self, status):
        '''
            Signal a/all thread(s). Signals are appended (excluding the STOP signal) rather than being overriden, in order to prevent race condition
        '''
        self.status = self.status | status if status != self._STOP else status

    def __isnotify(self, sig):
        '''
            Assert if a signal was notified
        '''
        return self.status and ((self.status & sig) == sig)

    def __wait(self, status):
        '''
            Wait for a signal
        '''
        while (self.status and not self.__isnotify(status)):
            pass
        return self.__isnotify(status)

    def run(self):
        '''
            Execute the bot
        '''
        import concurrent.futures
        events = [
            self.loadPage, self.refreshPage, self.getRegistrationData,
            self.authenticateUser, self.register
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(events)) as execr:
            futures = [execr.submit(event) for event in events]
            isTupleCompleted = concurrent.futures.wait(
                futures, timeout=None, return_when=concurrent.futures.FIRST_EXCEPTION)
            self.__notify(self._STOP)  # STOP waiting threads
            for i in range(len(isTupleCompleted.done)):
                # All threads finished either completely or by an exception
                # Allow the exception to be reraised if there was any
                isTupleCompleted.done.pop().result()

    def refreshPage(self):
        timeout = self.setup.get("refresh")
        gateway, tcpport = "8.8.8.8", 53
        net = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        net.settimeout(5)

        def refresh():
            if timeout < 1:
                # Disable refreshing if it wasn't set up
                self.__nretry = 0
            for loop in range(self.__nretry):
                try:
                    net.connect((gateway, tcpport))
                except socket.error:
                    self.driver.refresh()
                else:
                    self.status &= ~self._RETRY  # Turn off
                    return self.__notify(self._CONNECT_SUCCESS)
                time.sleep(timeout)
            net.close()
            self.__notify(self._STOP)

        while (self.status):
            if self.__wait(self._RETRY):
                refresh()
    def __ui(self):
        col, row, tmpcol, T, pgld, auts = (0, 0, 0, 0, 0, 0)

        while (self.status):
            termsz = os.get_terminal_size()
            col, row = termsz.columns, termsz.lines

            if (col != tmpcol):
                tmpcol = col
                '''
                    percentage-div2 = 20% of column size div 2
                    page-load = percentage-div2.qoutient + percentage-div2.remainder
                    auth-success = percentage-div2.qoutient
                '''
                pctg = divmod(0.2 * col, 2)
                pgld = int(pctg[0] + pctg[1])
                auts = int(pctg[0])

                T = 0 # Allow redraw

            if (not T and (self.status & self._PAGE_LOAD)):
                T = 1
                for i in range(pgld):
                    print("#", end="", flush=True)
                    time.sleep(0.1)
            if ((T == 1) and (self.status & self._AUTH_SUCCESS)):
                T = -1
                for i in range(pgld):
                    time.sleep(0.1)
                    print("#", end="", flush=True)
            _divmodadd = lambda d, x: (d / x) + (d % x)
            if (self.__totalTask > 0):
                colpctg = (_divmodadd(self.__totalTask, 0.8 * col) * 0.1)
                dpctg = _divmodadd(self.__completed, self.__totalTask)
                if (dpctg > colpctg or dpctg == colpctg):
                    print("#", end="", flush=True)
                    time.sleep(.1)

    def __msg(self, msg, **kwargs):
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

    def loadPage(self):
        '''
            Load the url into a new window or none (headless)
        '''
        try:
            self.driver = Driver.Chrome(options=self.options)
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: ()=> undefined})")
            self.driver.set_page_load_timeout(self.setup.get("page-timeout"))
            self.driver.get(self.setup.get("url"))
        except exceptions.WebDriverException as exc:
            self.__notify(self._RETRY)  # Retry connection
            if not self.__wait(self._CONNECT_SUCCESS):
                raise ConnectionError from exc
        self.__notify(self._PAGE_LOAD)

    def authenticateUser(self):
        timeout = self.setup.get("response-timeout")
        id = self.setup.pop("username")
        passwd = self.setup.pop("password")
        if id == "" or passwd == "":
            self.__notify(self._STOP)

        # wait until page ready is notified
        if not self.__wait(self._PAGE_LOAD):
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
                Wait for next page to load
            '''
            WebDriverWait(self.driver, timeout).until(
                EC.title_is(self.request("home-page-title")))
        except exceptions.TimeoutException:
            self.__notify(self._RETRY)
            if not self.__wait(self._CONNECT_SUCCESS):
                raise
        except Exception as exc:
            raise exc from None
        self.__notify(self._AUTH_SUCCESS)

    def getRegistrationData(self):
        '''
            Collect and process the registration data, updating to a data structure (list(dict))

            For a collected group of data sharing similar attribute such as gender, phone or email
            it can be easy, if we declare these attributes globally.
            Global attributes are declared as:

                GLOBAL * X           [x = M|F, 0-9, *@*.com],

            and comes before the group of data. This takes precedence, if such attribute is missing otherwise it is overwritten

            TODO: Add a limit (literal) for global declaration search, as such, declared as:
                GLOBAL * X[0..N]
        '''
        from collections import namedtuple
        dstruct = namedtuple('dstruct', ['name', 'gender', 'phone', 'email', 'address'])

        template = lambda td: dstruct (
            name    = td[0],
            gender  = td[1],
            phone   = td[2],
            email   = td[3],
            address = td[4]
        )

        with open("AutoRegList.txt", "r") as data:
            buffer = data.read() # Read raw data (rather than readlines())
            LINES = buffer.splitlines()
            self.__totalTask = len(LINES) - len(re.findall(r'\n+\s+\n+|\n+\n+', buffer)) # Total non blank lines

            recmpl = re.compile(
                r'(\b[MF]{1}\b|\b\d{10,11}\b|\w+@{1}\w+\.{1}\w+\b)')
            empty = ''
            globalSearch = True  # search first line for global identifiers
            # global var, name, address, gender, phone, email
            gb, nm, adr, g, p, e = empty, empty, empty, empty, empty, empty

            for __dat in LINES:
                self.status &= ~self._DATA_READY  # Turn off Signal: DATA_READY
                # Check for a global declaration of attributes (only gender is supported for now)
                if (__dat.isspace()):
                    globalSearch = True
                    continue
                elif globalSearch:
                    # Overwrite old -> New
                    g = re.fullmatch(
                        r'\s*?GLOBAL\s+?\*\s*?([?P<>MF])\s*$', __dat)
                    globalSearch = False
                    if not (g is None):
                        gb = g = g.group(1)  # Save New
                        continue
                    g = gb  # Restore old

                # Get Name and Address
                nmadr = re.split(r'\s*;\s*', re.sub(recmpl, ';', __dat))
                nm, adr = nmadr[0].strip(
                ), nmadr[-1].strip() if len(nmadr) > 1 else None

                # Get gender, phone number and  email
                gpe = recmpl.findall(__dat)
                for j in gpe:
                    # Fix the order if unordered
                    if j in ('M', 'F'):
                        g = j
                    elif j.isdigit():
                        p = j
                    else:
                        e = j
                # Verify completeness
                if g is empty or (p is empty and e is empty):
                    self.logger.warning(
                        f"Invalid format: '<name> <gender> <phone> or <email> <address>' is required but only '{f'{nm} {g} {p} {e} {adr}'.strip()}' was provided")
                    continue
                # Update register
                self.__register.append(template([nm, g, p, e, adr]))
                self.__notify(self._DATA_READY)
        # Completed
        self.__completed += 1
        self.__notify(self._DATA_DONE)

    def register(self):
        while (self.status):
            # Stop, if signal is never recieved or all data has been consumed
            if (not self.__wait(self._AUTH_SUCCESS | self._DATA_READY)) or (self.__isnotify(self._DATA_DONE) and not len(self.__register)):
                break
            dstruct   = self.__register.pop()
            name      = dstruct.name.split(None, 1)
            othername = name[-1] if len(name) > 1 else ""
            firstname = name[0]
            gender    = dstruct.gender
            phone     = dstruct.phone
            address   = dstruct.address
            email     = dstruct.email

            '''
                Manipulate DOM objects
            '''
            self.__sendKeyActionToDOMObj(self.__getDOMObjectById(
                self.request("user-first-name")), firstname)
            self.__sendKeyActionToDOMObj(self.__getDOMObjectById(
                self.request("user-other-name")), othername)
            self.__sendKeyActionToDOMObj(self.__getDOMObjectById(
                self.request("city")), self.setup.get("city"))
            self.__sendKeyActionToDOMObj(self.__getDOMObjectById(
                self.request("phone-number")), phone)
            # TODO: ADD email and address
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
            except exceptions.NoSuchElementException:
                error = self.driver.find_element(By.CSS_SELECTOR, self.request("feedbackerror")).get_property("innerText")
                self.logger.warning(error)
            except exceptions.TimeoutException:
                self.__notify(self._RETRY)
                if not self.__wait(self._CONNECT_SUCCESS):
                    raise
            except Exception as exc:
                raise exc from None

    def closePage(self, cp_info, exc_Type, exc_Msg, exc_Trace):
        # Quit browser + driver
        try:
            self.driver.quit()
        except:
            pass
        # TODO: print an exit log
        if exc_Type is not None:
            print(exc_Type.__name__, exc_Trace)
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
                        default=30, help='enable automatic page refresh after timeout')
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

    # ************** RUN BOT ***************

    with AutoRegister(setup) as register:
        register.run()

    # **************************************


if __name__ == "__main__":
    __main__()
