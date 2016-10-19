import httplib2
import logging
from apiclient import discovery
from datetime import datetime
from datetime import timedelta
from oauth2client.service_account import ServiceAccountCredentials

import ssl


# Google Calendar

class GoogleCalendarHelper():

    GCAL_SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
    
    def __init__(self, keyfile):
        self.keyfile_path = keyfile
        self.scopes = GoogleCalendarHelper.GCAL_SCOPES
        self.log = logging.getLogger()

        ssl._create_default_https_context = ssl._create_unverified_context

        self.credentials = GoogleCalendarHelper.getCredentials(self.keyfile_path, self.scopes)
        

    def listEvents(self, calendarIds, credentials=None):
                
        log = self.log
        
        http = self.credentials.authorize(httplib2.Http())
        service = discovery.build('calendar', 'v3', http=http)

        now = datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
        then = (datetime.utcnow() + timedelta(hours=3)).isoformat() + 'Z' # 'Z' indicates UTC time
        log.info('Checking for events between now and ' + str(then))

        eventsResult = service.events().list(calendarId=calendarId, timeMin=now, timeMax=then, maxResults=10, singleEvents=True, orderBy='startTime').execute()
        events = eventsResult.get('items', [])
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            log.debug(str(start) + " " + str(event['summary']))  

        return events

    def getCalendarIdByName(self, calendarName):
        
        log = self.log

        http = self.credentials.authorize(httplib2.Http())
        service = discovery.build('calendar', 'v3', http=http)

        log.debug("Fetching calendar list...")
        
        cal_list = service.calendarList().list().execute()
        for cal in cal_list['items']:
                log.debug("Calendar found: " + cal.get('summary') + " ID: " + cal.get('id'))
                if cal.get('summary') == calendarName:
                        return cal.get('id')

        raise NameError
        
                
    def getCredentials(keyfile_path, scopes):
        creds = ServiceAccountCredentials.from_json_keyfile_name(keyfile_path, scopes=scopes)
        delegated_credentials = creds.create_delegated('zerodt@ccq2.org')
        return delegated_credentials
