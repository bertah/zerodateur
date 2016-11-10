import sys
import json
import os
import re
import logging
import random
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime
from datetime import timedelta
from gcal import GoogleCalendarHelper
from fdtparser import FDTParser


# En mode simulation, on interroge FDT mais on n'effectue pas l'action
SIMULATION = False

# Surtout pour le logging
DEBUG = True

# Marge d'erreur aléatoire appliquée sur les événements pour simuler la saisie humaine
RANDOM_RANGE_IN_SECONDS = [-180, 180]

# Plage minimum / maximum à respecter pour le diner
LUNCH_BREAK_MIN_MAX_IN_MINUTES = [30, 90]

GCAL_SERVICE_ACCOUNT_KEYFILE = 'service_keyfile.json'
GCAL_APPLICATION_NAME = 'Zerodateur'
GCAL_CALENDAR_ID = 'v8l496693oe7snhpukk4r210fs@group.calendar.google.com'
OAUTH_CREDENTIALS_PATH = 'oauth2.json'

log = logging.getLogger()
scheduler = BlockingScheduler()
fdt_parser = ""

def CreateConfig():
    p = re.compile("\d\d:\d\d")
    p2 = re.compile("\d{4}-\d{2}-\d{2}")
    p3 = re.compile("p0\d{4}")
    p4 = re.compile("^.+$")
    heureDebut = ""
    heureDiner = ""
    heureRetour = ""
    heureDepart = ""
    dateProchainCP = ""
    fdtUsername = ""
    fdtPassword = ""
    fdtCompany = ""
    additionnalGcalName = ""
        
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
    while p4.match(fdtCompany) is None:
        fdtCompany = input("Nom d'entreprise FDT : ")
    while p3.match(fdtUsername) is None:
        fdtUsername = input("Nom d'usager FDT (p0XXXX) : ")
    while p4.match(fdtPassword) is None:
        fdtPassword = input("Mot de passe : ")
    additionnalGcalName = input("Nom du calendrier partagé pour absences (laisser vide si aucun) : ")

    conf = {'heureDebut': heureDebut,
            'heureDiner': heureDiner,
            'heureRetour': heureRetour,
            'heureDepart': heureDepart,
            'journeeCP': datetime.strptime(dateProchainCP, "%Y-%m-%d").weekday(),
            'semaineCP': datetime.strptime(dateProchainCP, "%Y-%m-%d").isocalendar()[1] % 2,
            'fdtCompany': fdtCompany,
            'fdtUsername': fdtUsername,
            'fdtPassword': fdtPassword,
            'additionnalGcalName': additionnalGcalName}
    
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

def PunchIn(config, fdt_parser, calendar_helper):
    # Check for active events in GCALs
    events = calendar_helper.listEvents(GCAL_CALENDAR_ID)
    events = [elem for elem in events if IsConflictingEvent(elem, config['journeeCP'], config['semaineCP'])]

    if not events and "additionnalGcalID" in config:
        log.info("Checking for events in calendar " + config["additionnalGcalName"] + " ...")
        try:
            events = calendar_helper.listEvents(config["additionnalGcalID"])
        except:
            log.warn("Error while checking additionnal Gcal")
    if not events:
        log.info('No conflicting events found. Punching in ...')
        state = fdt_parser.getCurrentState()
        log.info("Current state: " + state)
        
        if state == '60':
            fdt_parser.punchInDayStart()
        elif state == '20':
            fdt_parser.punchInBackFromLunch()
        else:
            log.error('Unrecognized state: ' + state + '. Already punched in?')
        state = fdt_parser.getCurrentState()
    else:
        log.warn('Found following conflicting event(s). Will not punch in.')
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            log.warn(str(start) + " " + str(event['summary']))

def PunchOut(config, fdt_parser):
    log.info("Punching out ...")
    state = fdt_parser.getCurrentState()
    log.info("Current state: " + state)
    if state == '1':
        fdt_parser.punchOutLunch()
    elif state == '30':
        fdt_parser.punchOutDayEnd()
    else:
        log.error('Unrecognized state: ' + state + '. Already punched out?')
    state = fdt_parser.getCurrentState()
# Scheduling

def AddEvent(date, eventType, scheduler, config, calendar_helper, fdt_parser):
    log.info("Creating event " + eventType + " at " + str(date))

    if eventType == "PUNCHIN":
        j = scheduler.add_job(PunchIn, 'date', run_date=date, args=[config, fdt_parser, calendar_helper])
        return

    if eventType == "PUNCHOUT":
        j = scheduler.add_job(PunchOut, 'date', run_date=date, args=[config, fdt_parser])
        return

    log.info(str(j))
    
    
def ComputeDate(date, time, previousEvent = None, minMaxDelayBetweenPreviousEvent = None):
    computed = date + timedelta(hours=time.hour, minutes=time.minute) + timedelta(seconds=random.randint(RANDOM_RANGE_IN_SECONDS[0], RANDOM_RANGE_IN_SECONDS[1]))
    
    if previousEvent is not None and minMaxDelayBetweenPreviousEvent is not None:
        minDelay = minMaxDelayBetweenPreviousEvent[0]
        maxDelay = minMaxDelayBetweenPreviousEvent[1]
    
        while ((computed - previousEvent).total_seconds() < minDelay * 60):
            log.debug("Computed date " + str(computed) + " does not respect minimum delay of " + str(minDelay) + " between event " + str(previousEvent) + ". Adding 1 minute...")
            computed = computed + timedelta(minutes=1)
        while ((computed - previousEvent).total_seconds() > maxDelay * 60):
            log.debug("Computed date " + str(computed) + " does not respect maximum delay of " + str(maxDelay) + " between event " + str(previousEvent) + ". Substracting 1 minute...")
            computed = computed + timedelta(minutes=-1)
            
    return computed
                
def AddEvents(day, scheduler, config, calendar_helper, fdt_parser):
    assert (day.hour == 0)
    assert (day.minute == 0)
    assert (day.second == 0)
    
    h = datetime.strptime(config["heureDebut"], "%H:%M")
    date = ComputeDate(day, h)

    AddEvent(date, "PUNCHIN", scheduler, config, calendar_helper, fdt_parser)

    h = datetime.strptime(config["heureDiner"], "%H:%M")
    date = ComputeDate(day, h)

    AddEvent(date, "PUNCHOUT", scheduler, config, calendar_helper, fdt_parser)

    h = datetime.strptime(config["heureRetour"], "%H:%M")
    date = ComputeDate(day, h, date, LUNCH_BREAK_MIN_MAX_IN_MINUTES)

    AddEvent(date, "PUNCHIN", scheduler, config, calendar_helper, fdt_parser)

    h = datetime.strptime(config["heureDepart"], "%H:%M")
    date = ComputeDate(day, h)

    AddEvent(date, "PUNCHOUT", scheduler, config, calendar_helper, fdt_parser)

def CreateSchedule(config, calendar_helper, fdt_parser):
    now = datetime.now()
    
    for i in range(0, 14):
        date = datetime(now.year, now.month, now.day) + timedelta(days=i)
        
        if date.weekday() in [5, 6]:
            log.info("Skipping " + str(date) + " - Reason: Weekend")
            continue

        AddEvents(date, scheduler, config, calendar_helper, fdt_parser)

def RunSchedule():
    scheduler.start()
        
def main():
    log.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    log.addHandler(ch)
    
    if not os.path.isfile('config.json'):
        CreateConfig()
    
    config = LoadConfig()
    calendar_helper = GoogleCalendarHelper(GCAL_SERVICE_ACCOUNT_KEYFILE)

    if config["additionnalGcalName"]:
        try:
            config["additionnalGcalID"] = calendar_helper.getCalendarIdByName(config["additionnalGcalName"])
            log.debug("Got additionnal calendar Id =" + config["additionnalGcalID"])
        except NameError:
            log.error("Impossible de trouver le calendrier " + config["additionnalGcalName"])
            
    fdt_parser = FDTParser(config['fdtCompany'], config['fdtUsername'], config['fdtPassword'], simulation=SIMULATION )
   
    CreateSchedule(config, calendar_helper, fdt_parser)

    RunSchedule()


if __name__ == '__main__':
    main()
