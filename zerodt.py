﻿import sys
import json
import os
import re
import logging
import random
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from datetime import timedelta

from gcal import GoogleCalendarHelper

# pip install apscheduler
# pip install --upgrade google-api-python-client
# pip install robobrowser


#import httplib2
#from apiclient import discovery
#from oauth2client import client
#from oauth2client import tools
#from oauth2client.file import Storage
#from oauth2client.service_account import ServiceAccountCredentials

DEBUG = True
FORCE_CONFIG_OVERWRITE = False

RANDOM_RANGE_IN_SECONDS = 0
LUNCH_BREAK_MIN_MAX_IN_MINUTES = [30, 90]

GCAL_SERVICE_ACCOUNT_KEYFILE = 'service_keyfile.json'
GCAL_APPLICATION_NAME = 'Zerodateur'
GCAL_CALENDAR_ID = 'v8l496693oe7snhpukk4r210fs@group.calendar.google.com'
OAUTH_CREDENTIALS_PATH = 'oauth2.json'

log = logging.getLogger()
scheduler = BackgroundScheduler()
calendar_helper = ""

def CreateConfig():
    p = re.compile("\d\d:\d\d")
    p2 = re.compile("\d{4}-\d{2}-\d{2}")
    heureDebut = ""
    heureDiner = ""
    heureRetour = ""
    heureDepart = ""
    dateProchainCP = ""
        
    while p.match(heureDebut) is None:
        heureDebut = input("Heure d'arrivée (format HH:mm) : ")
        
    while p.match(heureDiner) is None:
        heureDiner = input("Début de votre dîner (format HH:mm) : ")
    
    while p.match(heureRetour) is None:
        heureRetour = input("Heure de retour de dîner (format HH:mm) : ")
        
    while p.match(heureDepart) is None:
        heureDepart = input("Heure de départ (format HH:mm) : ")

    while p2.match(dateProchainCP) is None:
        dateProchainCP = input("Date de votre prochain CP (yyyy-mm-dd) : ")

    conf = {'heureDebut': heureDebut,
            'heureDiner': heureDiner,
            'heureRetour': heureRetour,
            'heureDepart': heureDepart,
            'journeeCP': datetime.strptime(dateProchainCP, "%Y-%m-%d").weekday(),
            'semaineCP': datetime.strptime(dateProchainCP, "%Y-%m-%d").isocalendar()[1] % 2}
    
    with open('config.json', 'w') as f:
        json.dump(conf, f)

    
def LoadConfig():
    if not os.path.isfile('config.json'): return
    with open('config.json', 'r') as f:
        config = json.load(f)
    return config



# misc
def IsConflictingEvent(event, journeeCP, semaineCP):  
    if str(event['summary']).startswith("CP_"):
        split = str(event['summary']).split("_")
        if split[1] != str(journeeCP) or split[2] != str(semaineCP):
            log.debug('Found CP but wrong week. Skipping')
            return False
    log.debug('Found conflicting event ' + str(event['summary']))
    return True

# Requests

def PunchIn(config):

    # Check for active events in GCALs
    events = calendar_helper.listEvents(GCAL_CALENDAR_ID)
    events = [elem for elem in events if IsConflictingEvent(elem, config['journeeCP'], config['semaineCP'])]

    if not events:
        log.info('No conflicting events found.')
        log.info("Punching in ...")
    else:
        log.warn('Found conflicting event(s). Will not punch in.')
        log.debug(events)
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            log.debug(str(start) + " " + str(event['summary']))                                       

def PunchOut(config):
    log.info("Punching out ...")
        

# Scheduling

def AddEvent(date, eventType, scheduler, config):
    log.info("Creating event " + eventType + " at " + str(date))

    if eventType == "PUNCHIN":
        j = scheduler.add_job(PunchIn, 'date', run_date=date, args=[config])
        return

    if eventType == "PUNCHOUT":
        j = scheduler.add_job(PunchOut, 'date', run_date=date, args=[config])
        return

    log.info(str(j))
    
    
def ComputeDate(date, time, previousEvent = None, minMaxDelayBetweenPreviousEvent = None):
    computed = date + timedelta(hours=time.hour, minutes=time.minute) + timedelta(seconds=random.randint(-RANDOM_RANGE_IN_SECONDS, RANDOM_RANGE_IN_SECONDS))

    minDelay = minMaxDelayBetweenPreviousEvent[0]
    maxDelay = minMaxDelayBetweenPreviousEvent[1]
    if previousEvent is not None and minimumDelayBetweenEvents is not None:
        while ((computed - previousEvent).total_seconds() < minDelay * 60):
            log.debug("Computed date " + str(computed) + " does not respect minimum delay of " + str(minDelay) + " between event " + str(previousEvent) + ". Adding 1 minute...")
            computed = computed + timedelta(minutes=1)
        while ((computed - previousEvent).total_seconds() > maxDelay * 60):
            log.debug("Computed date " + str(computed) + " does not respect maximum delay of " + str(maxDelay) + " between event " + str(previousEvent) + ". Substracting 1 minute...")
            computed = computed + timedelta(minutes=-1)
            
    return computed
                
def AddEvents(day, scheduler, config):
    assert (day.hour == 0)
    assert (day.minute == 0)
    assert (day.second == 0)
    
    h = datetime.strptime(config["heureDebut"], "%H:%M")
    date = ComputeDate(day, h)

    AddEvent(date, "PUNCHIN", scheduler, config)

    h = datetime.strptime(config["heureDiner"], "%H:%M")
    date = ComputeDate(day, h)

    AddEvent(date, "PUNCHOUT", scheduler, config)

    h = datetime.strptime(config["heureRetour"], "%H:%M")
    date = ComputeDate(day, h, date, LUNCH_BREAK_MIN_MAX_IN_MINUTES)

    AddEvent(date, "PUNCHIN", scheduler, config)

    h = datetime.strptime(config["heureDepart"], "%H:%M")
    date = ComputeDate(day, h)

    AddEvent(date, "PUNCHOUT", scheduler, config)

def CreateSchedule(config):
    now = datetime.now()
    
    for i in range(0, 7):
        date = datetime(now.year, now.month, now.day) + timedelta(days=i)
        
        if date.weekday() in [5, 6] and not DEBUG:
            log.info("Skipping " + str(date) + " - Reason: Weekend")
            continue

        AddEvents(date, scheduler, config)

def RunSchedule():
    scheduler.start()
        
def main():
    # Main
    
    log.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    log.addHandler(ch)
    
    if not os.path.isfile('config.json') or FORCE_CONFIG_OVERWRITE:
        CreateConfig()
    
    config = LoadConfig()

    calendar_helper = GoogleCalendarHelper(GCAL_SERVICE_ACCOUNT_KEYFILE)
    events = calendar_helper.listEvents(GCAL_CALENDAR_ID)

    log.info(events)

    
    
    #CreateSchedule(config)
    #RunSchedule()


if __name__ == '__main__':
    main()
