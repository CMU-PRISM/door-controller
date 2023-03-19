# Put this on a rpi, set the username and password for the doorbot account, and have it run as root on startup

# Imports
from bs4 import BeautifulSoup
import requests, time, os
import RPi.GPIO as GPIO

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Constants
TWO_WEEKS_SECONDS = 1210000
FIVE_MINUTES_SECONDS = 300
BTN_PIN = 7
OPN_PIN = 11
BSY_PIN = 13
CLS_PIN = 15
SITE_URL = 'https://prism.andrew.cmu.edu'
LOGIN_URL = 'https://prism.andrew.cmu.edu/accounts/login'
OPEN_URL = 'https://prism.andrew.cmu.edu/door-open'
BUSY_URL = 'https://prism.andrew.cmu.edu/door-busy'
CLOSE_URL = 'https://prism.andrew.cmu.edu/door-close'
with open(os.path.join(BASE_DIR, 'botpassword.txt')) as f:
    PWD = f.read().strip()

# Use physical pin numbering
GPIO.setmode(GPIO.BOARD)
# Set button pin (7) to be an input pin with initial value low (off)
GPIO.setup(BTN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
# Set button pin (11, 13, 15) to be output pins
GPIO.setup(OPN_PIN, GPIO.OUT)
GPIO.setup(BSY_PIN, GPIO.OUT)
GPIO.setup(CLS_PIN, GPIO.OUT)

# Variables
session_limit = 0
door_limit = 0
pause_time = 0
rqst = ''
rsp = ''

def change_pin(doorstate):
    '''
    Changes GPIO pins to HIGH/LOW depending on @doorstate

    :param doorstate: Indicate if room is OPEN, BUSY, or CLOSED
    '''
    print("Doorstate set to %s" % doorstate)
    # If doorstate starts with 'OPEN'
    if doorstate[0] == 'O':
        high_pin = OPN_PIN
    # If doorstate starts with 'BUSY'
    elif doorstate[0] == 'B':
        high_pin = BSY_PIN
    # If doorstate starts with 'CLOSED'
    elif doorstate[0] == 'C':
        high_pin = CLS_PIN
    # Revert to closed if any other state is passed
    else:
        high_pin = CLS_PIN
    # Reset all pins
    GPIO.output(OPN_PIN, GPIO.LOW)
    GPIO.output(BSY_PIN, GPIO.LOW)
    GPIO.output(CLS_PIN, GPIO.LOW)
    # Set pin corresponding with doorstate high
    GPIO.output(high_pin, GPIO.HIGH)

# Run forever
while True:
    # If more than two weeks have passed since starting session, restart session
    if time.time() > session_limit:
        # Set limit to two weeks from now
        session_limit = time.time() + TWO_WEEKS_SECONDS
        # Load in new session data
        rqst = requests.session()
        rqst.headers.update({'referer': SITE_URL})
        rsp = rqst.get(LOGIN_URL)
        token = rsp.cookies['csrftoken']

    # If more than five minutes have passed since last check, get door state again
    if time.time() > door_limit:
        # Set limit to five minutes from now
        door_limit = time.time() + FIVE_MINUTES_SECONDS
        r = rqst.get(SITE_URL)
        soup = BeautifulSoup(r.content, "html.parser")
        doorState = soup.find(id="door-status").text
        change_pin(doorState)

    # If the button is pressed, start switching the room status
    if GPIO.input(BTN_PIN) == GPIO.HIGH:
        # get current door state
        r = rqst.get(SITE_URL)
        soup = BeautifulSoup(r.content, "html.parser")
        oldState = soup.find(id="door-status").text
        # If room is was open: mark busy
        if oldState[0] == 'O':
            rqst.post(BUSY_URL,
                data = {'csrfmiddlewaretoken': token, 'password': PWD})
            change_pin('BUSY')
            # Only change state once while held
            while GPIO.input(BTN_PIN) == GPIO.HIGH:
                time.sleep(pause_time)
        # If room is was busy: mark closed
        elif oldState[0] == 'B':
            rqst.post(CLOSE_URL,
                data = {'csrfmiddlewaretoken': token, 'password': PWD})
            change_pin('CLOSED')
            # Only change state once while held
            while GPIO.input(BTN_PIN) == GPIO.HIGH:
                time.sleep(pause_time)
        # If room is was closed: mark open
        elif oldState[0] == "C":
            rqst.post(OPEN_URL,
                data = {'csrfmiddlewaretoken': token, 'password': PWD})
            change_pin('OPEN')
            # Only change state once while held
            while GPIO.input(BTN_PIN) == GPIO.HIGH:
                time.sleep(pause_time)
        # Unknown, attempt to close door
        else:
            print("ERROR: Room state unknown!")
            rqst.post(CLOSE_URL,
                data = {'csrfmiddlewaretoken': token, 'password': PWD})
            change_pin('CLOSED')
            # Only change state once while held
            while GPIO.input(BTN_PIN) == GPIO.HIGH:
                time.sleep(pause_time)
    # Pause before taking new input
    time.sleep(pause_time)
