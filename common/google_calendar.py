# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 16:31:05 2022

@author: david
"""

from datetime import datetime, timedelta
import os
import logging

from googleapiclient.discovery import build
import google.auth

from dotenv import load_dotenv
load_dotenv(verbose=True, override=True)

logger = logging.getLogger()
logging.basicConfig(
    format='%(asctime)s %(message)s',
    level=logging.INFO,
    datefmt='%d-%m-%Y %H:%M:%S')

SCOPES = ['https://www.googleapis.com/auth/calendar',
          'https://www.googleapis.com/auth/calendar.events']

API_NAME = 'calendar'
API_VERSION = 'v3'
CALENDAR_ID = os.getenv('CALENDAR_ID') # Defaults to fitness calendar
# SERVICE_ACCOUNT_FILE = os.path.join(os.getcwd(), 'common', os.getenv('SERVICE_ACCOUNT_FILE'))  # IDE/Docker
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(os.getcwd()), 'common', os.getenv('SERVICE_ACCOUNT_FILE'))  # Terminal

creds = google.auth.load_credentials_from_file(SERVICE_ACCOUNT_FILE, SCOPES)[0]
service = build(API_NAME, API_VERSION, credentials=creds)



def get_events(time_min=None,
               calendar_id=CALENDAR_ID):

    # time_min = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%dT00:00:00-00:00')

    if not time_min:
        return service.events().list(
            calendarId=calendar_id,
            singleEvents=True,
            orderBy='startTime',
            maxResults=2500,
        ).execute().get('items')
    else:
        return service.events().list(
            calendarId=calendar_id,
            singleEvents=True,
            orderBy='startTime',
            maxResults=2500,
            timeMin=time_min,  # Lower bound (exclusive)
        ).execute().get('items')


def create_body(name, start, end, colour=0, description=None):

    if not description:
        # description = f'Don\'t forget weigh in due between {start} and {end}'
        description = ''

    return {
        'summary': f'{name}',
        'description': description,
        'start': {
            'date': start,
            'timeZone': 'Europe/London',
        },
        'end': {
            'date': end,
            'timeZone': 'Europe/London',
        },
        'colorId': colour,  # 0 if weight else 11 https://lukeboyle.com/blog/posts/google-calendar-api-color-id
    }


def convert_date_for_cal(day, add_days=0):
    day = datetime.strptime(day.replace(",", ""), '%b %d %Y').date() + timedelta(days=add_days)
    return day.strftime('%Y-%m-%d')


def active(date, start: bool):
    # Change to if between dates then active elif before start else after end
    if start:
        return datetime.now() <= datetime.strptime(date.replace(",", ""), '%b %d %Y')
    else:
        # Taking away one day to take into account sending final weight in on last day
        return datetime.now() <= datetime.strptime(date.replace(",", ""), '%b %d %Y').replace(
            hour=23, minute=59,
            second=59,
            microsecond=999999)


def update_event(title, start, end, event_id, calendar_id=CALENDAR_ID, colour=0, description=None):
    logger.info(f'Updated event {title} in calendar, Date: {start}')
    return service.events().update(
        calendarId=calendar_id,
        eventId=event_id,
        body=create_body(title, start, end, colour, description)
    ).execute()


def delete_event(event_id, title, date, calendar_id=CALENDAR_ID):
    logger.info(f'Deleting event {title} in calendar  Date: {date}')
    # Deleting to keep calendar clean
    return service.events().delete(
        calendarId=calendar_id,
        eventId=event_id,
    ).execute()


def create_event(title, start, end, calendar_id=CALENDAR_ID, colour=0, description=None):
    logger.info(f'Creating event {title} in calendar, Date: {start}')
    return service.events().insert(
        calendarId=calendar_id,
        body=create_body(title, start, end, colour, description)
    ).execute()


def delete_all_events(events, calendar_id=CALENDAR_ID):
    for event in events:
        delete_event(event['id'], event['summary'], calendar_id)

