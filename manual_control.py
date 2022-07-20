# Imports
from bs4 import BeautifulSoup
import requests, time, os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Constants
TWO_WEEKS_SECONDS = 1210000
FIVE_MINUTES_SECONDS = 300
SITE_URL = 'https://prism.andrew.cmu.edu'
LOGIN_URL = 'https://prism.andrew.cmu.edu/accounts/login'
OPEN_URL = 'https://prism.andrew.cmu.edu/door-open'
BUSY_URL = 'https://prism.andrew.cmu.edu/door-busy'
CLOSE_URL = 'https://prism.andrew.cmu.edu/door-close'
with open(os.path.join(BASE_DIR, 'botpassword.txt')) as f:
    PWD = f.read().strip()
PRISM_CERTS = 'prismcert.pem'

# Variables
session_limit = 0
door_limit = 0
rqst = ''
rsp = ''

def change_pin(doorstate):
    # If doorstate starts with 'OPEN'
    if doorstate[0] == 'O':
        high_pin = 'OPN_PIN'
    # If doorstate starts with 'BUSY'
    if doorstate[0] == 'B':
        high_pin = 'BSY_PIN'
    # If doorstate starts with 'CLOSED'
    if doorstate[0] == 'C':
        high_pin = 'CLS_PIN'
    # Reset all pins
    print("OPN_PIN lowered")
    print("BSY_PIN lowered")
    print("CLS_PIN lowered")
    # Set pin corresponding with doorstate high
    print("%s raised" % high_pin)

# Run forever
while True:
    # If more than two weeks have passed since starting session, restart session
    if time.time() > session_limit:
        # Set limit to two weeks from now
        session_limit = time.time() + TWO_WEEKS_SECONDS
        # Create new session
        rqst = requests.session()
        rqst.headers.update({'referer': SITE_URL})
        rsp = rqst.get(LOGIN_URL, verify=PRISM_CERTS)
        token = rsp.cookies['csrftoken']

    # If more than five minutes have passed since last check, get door state again
    if time.time() > door_limit:
        # Set limit to five minutes from now
        door_limit = time.time() + FIVE_MINUTES_SECONDS
        r = rqst.get(SITE_URL, verify=PRISM_CERTS)
        soup = BeautifulSoup(r.content, "html.parser")
        doorState = soup.find(id="door-status").text
        change_pin(doorState)

    # If button pressed, change door state on site (always true for tests)
    if input("\nPress button? y/n: ") == "y":
        # get current door state
        r = rqst.get(SITE_URL, verify=PRISM_CERTS)
        soup = BeautifulSoup(r.content, "html.parser")
        oldState = soup.find(id="door-status").text
        # If room is was open: mark busy
        if oldState[0] == "O":
            rqst.post(BUSY_URL, verify=PRISM_CERTS,
                data = {'csrfmiddlewaretoken': token, 'password': PWD})
            change_pin('BUSY')
        # If room is was busy: mark closed
        elif oldState[0] == "B":
            rqst.post(CLOSE_URL, verify=PRISM_CERTS,
                data = {'csrfmiddlewaretoken': token, 'password': PWD})
            change_pin('CLOSED')
        # If room is was closed: mark open
        elif oldState[0] == "C":
            rqst.post(OPEN_URL, verify=PRISM_CERTS,
                data = {'csrfmiddlewaretoken': token, 'password': PWD})
            change_pin('OPEN')
        # Unknown, attempt to close door
        else:
            print("INVALID INPUT. INPUT WAS: ")
            print(oldState)
            rqst.post(CLOSE_URL, verify=PRISM_CERTS,
                data = {'csrfmiddlewaretoken': token, 'password': PWD})
            change_pin('CLOSED')
    else:
        break
    # Pause before taking new input
    time.sleep(0.25)
