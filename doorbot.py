# Put this on a rpi, set the username and password for the doorbot account, and have it run as root on startup

# Imports
from bs4 import BeautifulSoup
import requests, time
import RPi.GPIO as GPIO

# Constants
TWO_WEEKS_SECONDS = 1210000
BTN_PIN = 7
OPN_PIN = 11
BSY_PIN = 13
CLS_PIN = 15
LOGIN_URL = 'https://prism.andrew.cmu.edu/accounts/login'
SITE_URL = 'https://prism.andrew.cmu.edu'
OPEN_URL = 'https://prism.andrew.cmu.edu/door-open'
BUSY_URL = 'https://prism.andrew.cmu.edu/door-busy'
CLOSE_URL = 'https://prism.andrew.cmu.edu/door-close'
USER_NAME = 'doorbot@prism.andrew.cmu.edu'
PWD = 'PUT PASSWORD HERE DURING SETUP'
PRISM_CERTS = 'prismcert.pem'

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
rqst = ''
rsp = ''

# Switch LEDs to OPN_PIN on
def open_pin():
    GPIO.output(OPN_PIN, GPIO.HIGH)
    GPIO.output(BSY_PIN, GPIO.LOW)
    GPIO.output(CLS_PIN, GPIO.LOW)

# Switch LEDs to BSY_PIN on
def busy_pin():
    GPIO.output(OPN_PIN, GPIO.LOW)
    GPIO.output(BSY_PIN, GPIO.HIGH)
    GPIO.output(CLS_PIN, GPIO.LOW)

# Switch LEDs to CLS_PIN on
def close_pin():
    GPIO.output(OPN_PIN, GPIO.LOW)
    GPIO.output(BSY_PIN, GPIO.LOW)
    GPIO.output(CLS_PIN, GPIO.HIGH)

# Run forever
while True:
    # In two weeks time, restart session
    session_limit = time.time() + TWO_WEEKS_SECONDS
    # Load in new session data
    rqst = requests.session()
    rqst.headers.update({'referer': SITE_URL})
    rsp = rqst.get(LOGIN_URL, verify=PRISM_CERTS)
    token = rsp.cookies['csrftoken']
    rsp = rqst.post(LOGIN_URL, verify=PRISM_CERTS,
                    data = {'email': USER_NAME, 'password': PWD,
                            'csrfmiddlewaretoken': token})

    # Restart session after two weeks
    while time.time() < session_limit:
        # If the button is pressed, start switching the room status
        if GPIO.input(BTN_PIN) == GPIO.HIGH:
            # get current door state
            r = rqst.get(SITE_URL, verify=PRISM_CERTS)
            soup = BeautifulSoup(r.content, "html.parser")
            oldState = soup.find(id="door-status").text
            # If room is was open: mark busy
            if oldState[0] == 'O':
                rqst.post(OPEN_URL, verify=PRISM_CERTS,
                    data = {'csrfmiddlewaretoken': token})
                open_pin()
            # If room is was busy: mark closed
            elif oldState[0] == 'B':
                rqst.post(BUSY_URL, verify=PRISM_CERTS,
                    data = {'csrfmiddlewaretoken': token})
                busy_pin()
            # If room is was closed: mark open
            elif oldState[0] == "C":
                rqst.post(CLOSE_URL, verify=PRISM_CERTS,
                    data = {'csrfmiddlewaretoken': token})
                close_pin()
            else:
                print("ERROR: Room state unknown!")
        # Pause before taking new input
        time.sleep(0.25)
