from bs4 import BeautifulSoup
import requests, time

# Constants
LOGIN_URL = 'https://prism.andrew.cmu.edu/accounts/login'
SITE_URL = 'https://prism.andrew.cmu.edu'
OPEN_URL = 'https://prism.andrew.cmu.edu/door-open'
BUSY_URL = 'https://prism.andrew.cmu.edu/door-busy'
CLOSE_URL = 'https://prism.andrew.cmu.edu/door-close'
USER_NAME = 'doorbot@prism.andrew.cmu.edu'
PWD = 'PUT PASSWORD HERE DURING SETUP'
PRISM_CERTS = 'prismcert.pem'

# Variables
session_limit = 0
rqst = ''
rsp = ''

# Run forever
while True:
    session_limit = time.time() + 10000
    rqst = requests.session()
    rqst.headers.update({'referer': SITE_URL})
    rsp = rqst.get(LOGIN_URL, verify=PRISM_CERTS)
    token = rsp.cookies['csrftoken']
    rsp = rqst.post(LOGIN_URL, verify=PRISM_CERTS,
        data = {'email': USER_NAME, 'password': PWD,
                'csrfmiddlewaretoken': token})

    # Restart session after two weeks
    while time.time() < session_limit:
        # get current door state
        r = rqst.get(SITE_URL, verify=PRISM_CERTS)
        soup = BeautifulSoup(r.content, "html.parser")
        # If button pressed, change door state on site
        oldState = soup.find(id="door-status").text
        print(oldState)
        newState = input("New door status: ")
        if newState == "open":
            rqst.post(OPEN_URL, verify=PRISM_CERTS,
                data = {'csrfmiddlewaretoken': token})
            print("Door opened!")
        elif newState == "close":
            rqst.post(CLOSE_URL, verify=PRISM_CERTS,
                data = {'csrfmiddlewaretoken': token})
            print("Door closed!")
        elif newState == "busy":
            rqst.post(BUSY_URL, verify=PRISM_CERTS,
                data = {'csrfmiddlewaretoken': token})
            print("Room marked busy!")
        else:
            print("INVALID INPUT. YOU SAID: ")
            print(newState)
