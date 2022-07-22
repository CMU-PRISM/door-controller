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
with open(os.path.join(BASE_DIR, 'botpassword.txt')) as f:
    PWD = f.read().strip()
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
door_limit = 0
rqst = ''
rsp = ''
doorState = "CLOSED"
time_since_last_press = 0

def change_pin(doorstate):
    '''
    Changes GPIO pins to HIGH/LOW depending on @doorstate
    '''
    # If doorstate starts with 'OPEN'
    if doorstate[0] == 'O':
        high_pin = OPN_PIN
    # If doorstate starts with 'BUSY'
    if doorstate[0] == 'B':
        high_pin = BSY_PIN
    # If doorstate starts with 'CLOSED'
    if doorstate[0] == 'C':
        high_pin = CLS_PIN
    # Reset all pins
    GPIO.output(OPN_PIN, GPIO.LOW)
    GPIO.output(BSY_PIN, GPIO.LOW)
    GPIO.output(CLS_PIN, GPIO.LOW)
    # Set pin corresponding with doorstate high
    GPIO.output(high_pin, GPIO.HIGH)

def debounce_check(oldTime):
    '''
    Makes sure button press is a valid press and not the fault of bouncing

    :param oldTime: Last time the button was pressed
    :return: True if the current time is greater than @oldTime by at least 100 milliseconds
    '''
    millitime = int(round(time.time() * 1000))
    milliold = int(round(oldTime * 1000))
    if (millitime - milliold) >= 100:
        return True
    else:
        return False

# Run forever
while True:
    print("-----")
    print(time.time())
    print("Button state is: " + str(GPIO.input(BTN_PIN)))
    print("Doorstate is: " + str(doorState))
    # If more than two weeks have passed since starting session, restart session
    if time.time() > session_limit:
        # Set limit to two weeks from now
        session_limit = time.time() + TWO_WEEKS_SECONDS

    # If more than five minutes have passed since last check, get door state again
    if time.time() > door_limit:
        # Set limit to five minutes from now
        door_limit = time.time() + FIVE_MINUTES_SECONDS
        change_pin(doorState)

    # If the button is pressed, start switching the room status
    if GPIO.input(BTN_PIN) == GPIO.HIGH and debounce_check(time_since_last_press):
        time_since_last_press = time.time()
        # If room is was open: mark busy
        if doorState[0] == 'O':
            doorState = 'BUSY'
            change_pin(doorState)
            # Only change state once while held
            while GPIO.input(BTN_PIN) == GPIO.HIGH:
                print("Button is held down!")
                time.sleep(0.15)
        # If room is was busy: mark closed
        elif doorState[0] == 'B':
            doorState = 'CLOSED'
            change_pin(doorState)
            # Only change state once while held
            while GPIO.input(BTN_PIN) == GPIO.HIGH:
                print("Button is held down!")
                time.sleep(0.15)
        # If room is was closed: mark open
        elif doorState[0] == "C":
            doorState = 'OPEN'
            change_pin(doorState)
            # Only change state once while held
            while GPIO.input(BTN_PIN) == GPIO.HIGH:
                print("Button is held down!")
                time.sleep(0.15)
        # Unknown, attempt to close door
        else:
            print("ERROR: Room state unknown!")
            change_pin('CLOSED')
            time.sleep(0.15)

GPIO.cleanup()
