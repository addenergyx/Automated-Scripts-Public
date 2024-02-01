# -*- coding: utf-8 -*-
"""
Created on Fri Sep 16 09:05:26 2022

@author: david
"""
import email
from bs4 import BeautifulSoup
import re
import boto3
from decimal import Decimal
import json
from dotenv import load_dotenv
import os
import requests
import time
import glob
from selenium.webdriver.common.by import By
import logging

load_dotenv(verbose=True, override=True)

import sys

sys.path.append('../')

from common.google_photos_upload import get_media_items_name, get_media_items_id, batch_upload, remove_media, move_media
from common.captcha_bypass import CaptchaBypass
from common.aws_connection import connect_to_s3
from common.notification_manager import NotificationManager
from common.driver_manager import DriverManager

logging.basicConfig(
    format='%(asctime)s %(message)s',
    level=logging.INFO,
    datefmt='%d-%m-%Y %H:%M:%S')

logger = logging.getLogger()
logger.info('The script is starting.')

ANTICAPTCHA_KEY = os.getenv('ANTICAPTCHA_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_DEFAULT_REGION = "eu-west-1"
WORKING_ENV = os.getenv('WORKING_ENV', 'DEV')
NOTIFICATION_TOKEN = os.getenv('NOTIFICATION_TOKEN')
PUBLIC_SITEKEY = '6LcGYtkZAAAAAHu9BgC-ON7jeraLq5Tgv3vFQzZZ'
BALANCE_CHECKER_URL = "https://www.asdagiftcards.com/balance-check"
API_URL = "https://api.asdagiftcards.com/api/v1/balance"
PUSH_NOTIFICATION_TITLE = "Single ASDA Giftcard"

def handler(event=None, context=None):

    if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
        driver_manager = DriverManager('/opt/headless-chromium', '/opt/chromedriver')
        driver = driver_manager.get_driver(headless=True)
        directory = '/tmp'
    else:
        driver_manager = DriverManager()
        driver = driver_manager.get_driver(headless=True)
        directory = os.path.join(os.getcwd(), 'images')

    notification_manager = NotificationManager(NOTIFICATION_TOKEN)

    cards_to_delete = []
    cardnumbers_from_album = []
    total = 0

    dynamodb = boto3.resource(
        'dynamodb',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=AWS_DEFAULT_REGION
    )

    giftcards_table = dynamodb.Table('giftcards')

    current_giftcards_in_album = get_media_items_name()

    for item in current_giftcards_in_album:
        cardnumbers_from_album.append(re.sub('\D', '', item))

    data = []

    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    s3_client = boto3.client('s3')
    response = s3_client.get_object(Bucket=bucket, Key=key)
    email_message = email.message_from_bytes(response['Body'].read())

    for part in email_message.walk():

        content_type = part.get_content_type()

        if "html" in content_type:

            if 'Top Cashback' in email_message['Subject']:

                print('TopCashback')

                html_ = part.get_payload(decode=True)
                soup = BeautifulSoup(html_, 'html.parser')
                href = soup.select('a')
                giftcard_url = href[0]['href']

            else:

                html_ = part.get_payload()
                soup = BeautifulSoup(html_, 'html.parser')
                href = soup.select('a')

                giftcard_url = href[-1].text
                # giftcard_url = href[-1]['href']

                # Newer giftcards have newlines in the url
                # Also fixes the new revealyourgift links started 20/1/24
                giftcard_url = giftcard_url.replace('\n', '').replace('\r', '').replace('=', '')

            page = requests.get(giftcard_url)
            giftcard_url = page.url  # For topcashback email need to get redirect url not original url

            if page.status_code == 200:

                print(giftcard_url)

                if 'asda' in giftcard_url:
                    html_ = page.content
                elif 'spend.runa' in giftcard_url:

                    # Topcashback now use a new giftcard provider that loads giftcards via Javascript so need selenium now
                    # # giftcard_url = 'https://spend.runa.io/223a51f7-ef12-4c65-a44a-c44fea2c17db'
                    # driver.get(giftcard_url)
                    # WebDriverWait(driver, 15).until(lambda driver: driver.find_element('id', "accountnumber_pin")) # Should wait for JS to finish loading
                    # html_ = driver.page_source

                    url = 'https://connect.runa.io/internal-service-api/wallet/asset/' + giftcard_url.split('/')[-1]

                    print('url: '+ url)

                    headers = {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/112.0",
                        "Accept": "application/json",
                        "Accept-Language": "en-GB,en;q=0.5",
                        "Accept-Encoding": "gzip, deflate, utf-8",
                        "Referer": "https://spend.runa.io/",
                        "Origin": "https://spend.runa.io",
                        "Connection": "keep-alive",
                        "Sec-Fetch-Dest": "empty",
                        "Sec-Fetch-Mode": "cors",
                        "Sec-Fetch-Site": "same-site",
                    }

                    redirect = requests.get(url, headers=headers, verify=False, allow_redirects=True)

                    external_redemption_url = redirect.json()['redemptionInformation']['externalRedemptionUrl']

                    page = requests.get(external_redemption_url)
                    giftcard_url = page.url
                    html_ = page.content

                elif 'revealyourgift' in giftcard_url:

                    # Airtime rewards now use a new giftcard provider that requires customers to 'claim' giftcard before the number and pin appear
                    # This requires selenium to click the 'CLAIM YOUR GIFT CARD' button
                    # Page uses javascript so can't get the link for the button from the page
                    # javascript elements won't load in lambda so need to click manually


                    notification_manager.push_notification(PUSH_NOTIFICATION_TITLE, f"Click link to claim giftcard: {giftcard_url}")

                    max_attempts = 60  # Number of attempts to find the button
                    attempt = 0

                    driver.get(giftcard_url)

                    while attempt < max_attempts:
                        # try:
                        response = requests.get(giftcard_url)

                        soup = BeautifulSoup(response.text, 'html.parser')
                        element = soup.find(id="barcode")
                        if element:
                            break
                        else:
                            time.sleep(5)
                            # Wait for the button to be present
                            # WebDriverWait(driver, 20).until(
                            #     EC.presence_of_element_located((By.ID, "barcode"))
                            # )
                            # break  # Exit the loop if the button is found
                        # except Exception as e:
                        #     print(f"Attempt {attempt + 1} failed. Refreshing page...")
                        #     driver.refresh()
                        #     attempt += 1

                    if attempt == max_attempts:
                        # Return a specific response and quit the Lambda function
                        notification_manager.push_notification(PUSH_NOTIFICATION_TITLE,
                                          f"Failed to load giftcard after several attempts, "
                                          f"make sure card has been manually claimed first then run giftcard tracker lambda{giftcard_url}")

                        return {
                            "statusCode": 400,
                            "body": json.dumps("Failed to load giftcard after several attempts.")
                        }

                    page = requests.get(giftcard_url)
                    html_ = page.content

                    # Doesn't work in lambda, javascript won't load
                    # driver.get(giftcard_url)
                    # driver.implicitly_wait(20)
                    # driver.find_element('class name', 'button-redeem').click()
                    # giftcard_url = driver.current_url
                    # driver.implicitly_wait(60)
                    # driver.refresh()
                    # driver.implicitly_wait(10)
                    # html_ = driver.page_source

                else:
                    break

                soup = BeautifulSoup(html_, 'html.parser')

                soup.findAll('iframe')

                aq = soup.select('div[id*="accountnumber_pin"]')

                numbers = re.sub('\D', '', aq[0].text)

                card_number = numbers[:16]
                pin = numbers[-4:]

                link = soup.findAll('a', attrs={'class': 'apple-wallet-badge'})[0]

                link = link['href']

                x = 0

                while x < 4:

                    g_response = CaptchaBypass(PUBLIC_SITEKEY, BALANCE_CHECKER_URL).bypass()

                    payload = {
                        "number": card_number,
                        "pin": pin,
                        "recaptcha": g_response
                    }

                    headers = {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:104.0) Gecko/20100101 Firefox/104.0",
                        "Accept": "application/json, text/plain, */*",
                    }

                    response = requests.request("POST", API_URL, json=payload, headers=headers).json()

                    if 'response_code' in response and response['response_code'] == '00':

                        card_id = response['embossed_card_number']
                        balance = response['new_balance']
                        img_filename = 'giftcard_' + card_id + '.png'

                        balance = float(balance[:-2] + '.' + balance[-2:])  # balance returned in pence

                        if balance <= 0.0:
                            # mark the mail as deleted
                            # mail.store(item, "+FLAGS", "\\Deleted") # delete at the end instead
                            print(f'Card to be deleted: {card_id} with balance {balance}')
                            cards_to_delete.append(img_filename)
                            notification_manager.push_notification(PUSH_NOTIFICATION_TITLE, f"Card number: {card_id}\nCurrent balance: {balance}")
                            break

                        else:
                            notification_manager.push_notification(PUSH_NOTIFICATION_TITLE, f"Card number: {card_id}\nCurrent balance: {balance}")

                            if img_filename not in current_giftcards_in_album:
                                # hti.screenshot(url=giftcard_url, save_as=img_filename)
                                driver.get(giftcard_url)

                                S = lambda X: driver.execute_script('return document.body.parentNode.scroll' + X)
                                driver.set_window_size(S('Width'), S('Height'))  # May need manual adjustment

                                driver.save_screenshot(
                                    directory + '/' + img_filename) if WORKING_ENV == 'PROD' else driver.find_element(
                                    By.TAG_NAME, 'body').screenshot(directory + '/' + img_filename)

                        data.append([card_id, balance, link])
                        print(f'{card_id}-{pin}: £{balance}')
                        total += balance

                        break

                    else:
                        x += 1
                        print(card_number)
                        print(pin)
                        print(response['message'])

                    if x == 3:
                        data.append([card_number, response['message'], '-'])
                        print(card_number)
                        print(pin)
                        print(response['message'])

                        driver.close()
                        driver.quit()

                        notification_manager.push_notification(PUSH_NOTIFICATION_TITLE + " Lambda failed", f"Card number: {card_id}")

                        return json.dumps({
                            "statusCode": 500,
                            "body": {
                                'message': 'Single Giftcard lambda Failed',
                                'card_id': card_number,
                                'error': response['message']
                            }
                        }, indent=4)

    driver.close()
    driver.quit()

    s3 = connect_to_s3()
    s3.Object(bucket, key).delete()

    files = [x for x in glob.glob(os.path.join(directory, '*')) if 'giftcard' in x]
    print(directory)
    print(files)
    print('-------------')

    if files:
        if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
            media_items = batch_upload(files=files)
        else:
            media_items = batch_upload(directory=directory)

        time.sleep(5)
        move_media(media_items)

        for f in files:
            os.remove(f)

    dic_ = [{'card_id': x[0], 'balance': x[1], 'link': x[2]} for x in data]

    with giftcards_table.batch_writer(overwrite_by_pkeys=['card_id']) as batch:
        for row in dic_:
            giftcard_dic = json.loads(json.dumps(row), parse_float=Decimal)
            logger.info(f"Adding giftcard {giftcard_dic['card_id']} in giftcard table")
            batch.put_item(Item=giftcard_dic)

    return json.dumps({
        "statusCode": 200,
        "body": {
            'message':'Giftcard lambda invoke successful',
            'card_id': card_number
        }
    }, indent=4)


if not os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
    print(handler())
