# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 12:02:24 2022

@author: david
"""

from dotenv import load_dotenv
import os

from googleapiclient.discovery import build
import google.auth

from googleapiclient.http import MediaFileUpload  # File format required to upload

import time

load_dotenv(verbose=True, override=True)

# SERVICE_ACCOUNT_FILE = os.path.join(os.getcwd(), 'common', os.getenv('SERVICE_ACCOUNT_FILE'))  # IDE/Docker
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(os.getcwd()), 'common',
                                    os.getenv('SERVICE_ACCOUNT_FILE'))  # Terminal
GOOGLEDRIVE_FOLDER_ID = os.getenv('GOOGLEDRIVE_FOLDER_ID')


# https://developers.google.com/drive/api/guides/manage-sharing
def upload(src, file_name):
    SCOPES = ['https://www.googleapis.com/auth/drive']

    API_NAME = 'drive'
    API_VERSION = 'v3'

    # https://www.labnol.org/google-api-service-account-220404
    # Make sure to share google drive folder with service account email
    creds = google.auth.load_credentials_from_file(SERVICE_ACCOUNT_FILE, SCOPES)[0]
    service = build(API_NAME, API_VERSION, credentials=creds)

    media_content = MediaFileUpload(src, mimetype='text/pdf')

    # Listing files in folder
    query = f"parents = '{GOOGLEDRIVE_FOLDER_ID}'"
    response = service.files().list(q=query).execute()
    files = response.get('files')
    next_page_token = response.get('nextPageToken')

    while next_page_token:
        response = service.files().list(q=query, pagetoken=next_page_token).execute()
        files.extend(response.get('files'))
        next_page_token = response.get('nextPageToken')

    # Overwrite existing file
    for file in files:
        if file['name'] == file_name:
            file_metadata = {
                'name': file_name,
                # 'parents': [GOOGLEDRIVE_FOLDER_ID] # The parents field is not directly writable in update requests.
            }

            service.files().update(fileId=file['id'], body=file_metadata, media_body=media_content).execute()
            
            time.sleep(2)
            
            # os.remove(src) # Creating separate cronjob to move file to onedrive
            return print(f"Overwritten file in google drive: {file['name']}")

    file_metadata = {
        'name': file_name,
        'parents': [GOOGLEDRIVE_FOLDER_ID]  # id must be in a list
    }

    file = service.files().create(
        body=file_metadata,
        media_body=media_content
    ).execute()
    
    # os.remove(src) # Creating separate cronjob to move file to onedrive
    
    return print(f"Created file: {file['name']}")
