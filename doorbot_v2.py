# Put this on a rpi, set the username and password for the
# doorbot account, and have it run as root on startup

####################### Doorbot V2 #######################
# V1 had the right idea but it's execution was flawed.   #
# Chief amoung (us) the problems was the fact that the   #
# door controller would freeze after an unknown period   #
# of time, at most one week. Pressumably, decreasing     #
# the session time drastically would prevent the freeze, #
# as rebooting the device makes things work as intended. #
##########################################################

## Pseudocode
# Run script on device startup
# on script run:
#   connect to website and fetch door status
#   light up corresponding light
#   set timer vars to 0
#
# while true:
#   if idle time > 5 minutes
#       idle = true
#       turn LEDs off
#   on button press:
#       if idle:
#           turn all LEDs on
#           connect to website and fetch door status
#           turn all incorrect LEDs off
#       else:
#           increment door state
#           toggle correct LED on
#       idle time = 0
#       reset idle timer


## Imports
from bs4 import BeautifulSoup
import requests, time, os
import RPi.GPIO as GPIO


## Constants
# Longest amount of time (in seconds) the device is able to sit for before going idle
IDLE_MAX = 300
# Sets delay (in seconds) when waiting for new button input, helps prevent button bounce
PAUSE_DELAY = 1
# Which GPIO pins correspond to which component
BTN_PIN = 7
OPN_PIN = 11
BSY_PIN = 13
CLS_PIN = 15
# Website links for initiating sessions and POSTing new door states
SITE_URL = 'https://prism.andrew.cmu.edu'
OPEN_URL = 'https://prism.andrew.cmu.edu/door-open'
BUSY_URL = 'https://prism.andrew.cmu.edu/door-busy'
CLOSE_URL = 'https://prism.andrew.cmu.edu/door-close'
# Which GPIO pins correspond to which door state
DOOR_STATES = {
    "OPEN": OPN_PIN,
    "BUSY": BSY_PIN,
    "CLOSED": CLS_PIN,
    }
# Which URL gets POSTed, i.e. the status the door should be updated to, given the current state
CHANGE_STATE = {
    "OPEN": BUSY_URL,
    "BUSY": CLOSE_URL,
    "CLOSED": OPEN_URL,
    }
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, 'botpassword.txt')) as f:
    PWD = f.read().strip()


## Variables
# Track when the most recent button interaction was
most_recent_press = time.time()
# Stores the page request session
session = {
    'rqst': '',
    'rsp': '',
    'token': '',
    }


## Helper Functions
# Main button driver
def do_button_press(session, idle_time):
    '''
    Handle button presses, changing what happens depending on if
    the device has been idle for some time or not.

    @param session: List containing vars relevant to the current session
    '''
    # Check if the most recent press was more than five minutes ago
    if idle_time > IDLE_MAX:
        on_idle_press(session)
    else:
        on_active_press(session)
    return

# Idle button press
def on_idle_press(session):
    '''
    When pressed from an idle state, turn on all LEDs,
    restart the session, grab the door state, then leave only
    the correct LED powered on

    @param session: Active session information
    '''
    # Flash all LEDs to on
    GPIO.output(OPN_PIN, GPIO.HIGH)
    GPIO.output(BSY_PIN, GPIO.HIGH)
    GPIO.output(CLS_PIN, GPIO.HIGH)

    # Load in new session data
    session['rqst'] = requests.session()
    session['rqst'].headers.update({'referer': SITE_URL})
    session['rsp'] = session['rqst'].get(SITE_URL)
    session['token'] = session['rsp'].cookies['csrftoken']

    # Grab the door state
    door_state = get_state(session)

    # Set the correct LED to on
    change_led(door_state)

# Non-idle button press
def on_active_press(session):
    '''
    When pressed from a non idle state, turn off all LEDs,
    grab the door state, increment the door state, then turn
    on the correct LED and POST to the website the new status

    @param session: Active session information
    '''
    # Flash all LEDs to off
    GPIO.output(OPN_PIN, GPIO.LOW)
    GPIO.output(BSY_PIN, GPIO.LOW)
    GPIO.output(CLS_PIN, GPIO.LOW)

    # Grab the door state
    door_state = get_state(session)

    # Set the correct LED to on
    change_led(door_state)
    send_POST(session, )

    return

# Get door state
def get_state(session):
    '''
    Parse site to find door state

    @param session: Active session information
    '''
    r = session['rqst'].get(SITE_URL)
    soup = BeautifulSoup(r.content, "html.parser")
    return soup.find(id="door-status").text

# Turn off all LEDs, then turn on the LED corresponding to the state
def change_led(state):
    '''
    Changes LED GPIO pins to HIGH/LOW depending on @door_state, or turns all LEDs off

    @param door_state: which state to set the room to, either OPEN, BUSY, or CLOSED
    '''
    # Reset all pins to off
    GPIO.output(OPN_PIN, GPIO.LOW)
    GPIO.output(BSY_PIN, GPIO.LOW)
    GPIO.output(CLS_PIN, GPIO.LOW)

    # Handle the special case where the device has been idle and all pins are to be powered off
    if state == "IDLE":
        return None

    # Turn correct pin on
    GPIO.output(DOOR_STATES[state], GPIO.HIGH)

# Submit POST and update door state on the website
def send_POST(session, state):
    '''
    Depending on @state, send a POST to the website, either opeing,
    marking as busy, or closing the room.

    @param session: Active session information
    @param state: which state to set the room to, either OPEN, BUSY, or CLOSED
    '''
    session['rqst'].post(CHANGE_STATE[state],
        data = {'csrfmiddlewaretoken': session['token'], 'password': PWD})
    return


## Startup
# Use physical pin numbering
GPIO.setmode(GPIO.BOARD)
# Set button pin (7) to be an input pin with initial value low (off)
GPIO.setup(BTN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
# Set button pin (11, 13, 15) to be output pins
GPIO.setup(OPN_PIN, GPIO.OUT)
GPIO.setup(BSY_PIN, GPIO.OUT)
GPIO.setup(CLS_PIN, GPIO.OUT)


# Run forever
while True:
    # Only act on button press
    if GPIO.input(BTN_PIN) == GPIO.HIGH:
        do_button_press(session, idle_time)
        most_recent_press = time.time()
        # Wait while the button is held down, after running a button press
        while GPIO.input(BTN_PIN) == GPIO.HIGH:
            time.sleep(PAUSE_DELAY)

    # Between presses, keep track of the time since the last button press
    idle_time = time.time() - most_recent_press

    if idle_time > IDLE_MAX:
        change_led("IDLE")

    # Pause before taking new input
    time.sleep(PAUSE_DELAY)
