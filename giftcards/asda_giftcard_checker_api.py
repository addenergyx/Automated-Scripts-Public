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
from selenium import webdriver
from selenium.webdriver.common.by import By
import logging
from email_client import EmailClient

load_dotenv(verbose=True, override=True)

import sys

sys.path.append('../')

from common.google_photos_upload import get_media_items_name, get_media_items_id, batch_upload, remove_media, move_media
from common.captcha_bypass import CaptchaBypass
from common.notification_manager import NotificationManager
from common.driver_manager import DriverManager

logging.basicConfig(
    format='%(asctime)s %(message)s',
    level=logging.INFO,
    datefmt='%d-%m-%Y %H:%M:%S')

logger = logging.getLogger()
logger.info('The script is starting.')

EMAIL_USER = os.getenv('DASHBOARD_EMAIL')
EMAIL_PASS = os.getenv('DASHBOARD_PASS')
ANTICAPTCHA_KEY = os.getenv('ANTICAPTCHA_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_DEFAULT_REGION = "eu-west-1"
WORKING_ENV = os.getenv('WORKING_ENV', 'DEV')
NOTIFICATION_TOKEN = os.getenv('NOTIFICATION_TOKEN')
BALANCE_CHECKER_URL = "https://www.asdagiftcards.com/balance-check"
API_URL = "https://api.asdagiftcards.com/api/v1/balance"
PUSH_TITLE = "ASDA Giftcards"

# # TODO: get sitekey, is in the iframe kdriver = webdriver.Chrome(options = options)=
# # https://anti-captcha.com/apidoc/articles/how-to-find-the-sitekey
PUBLIC_SITEKEY = '6LcGYtkZAAAAAHu9BgC-ON7jeraLq5Tgv3vFQzZZ'

def handler(event=None, context=None):

    if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
        driver_manager = DriverManager('/opt/headless-chromium', '/opt/chromedriver')
        driver = driver_manager.get_driver(headless=True)
        directory = '/tmp'
    else:
        driver_manager = DriverManager()
        driver = driver_manager.get_driver(headless=True)
        directory = os.path.join(os.getcwd(), 'images')

    email_client = EmailClient(server="imap.gmail.com", username=EMAIL_USER, password=EMAIL_PASS)
    notification_manager = NotificationManager(NOTIFICATION_TOKEN)

    email_client.connect()

    email_client.select_mailbox('giftcards')
    mailbox_list = email_client.search_emails()

    cards_to_delete = []
    mail_to_delete = []
    cards_from_email = []
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

    for item in mailbox_list:

        email_message = email_client.fetch_email(item)

        counter = 1
        for part in email_message.walk():
            if part.get_content_maintype() == "multipart":
                continue
            filename = part.get_filename()
            if not filename:
                ext = '.html'
                filename = 'msg-part%08d%s' % (counter, ext)

            counter += 1

            content_type = part.get_content_type()

            if "html" in content_type:

                if 'Top Cashback' in email_message['Subject']:

                    logger.info('TopCashback')

                    html_ = part.get_payload(decode=True)
                    soup = BeautifulSoup(html_, 'html.parser')
                    href = soup.select('a')
                    giftcard_url = href[0]['href']

                else:

                    html_ = part.get_payload()
                    soup = BeautifulSoup(html_, 'html.parser')
                    href = soup.select('a')

                    giftcard_url = href[-1].text

                    # Newer giftcards have newlines in the url
                    giftcard_url = giftcard_url.replace('\n', '').replace('\r', '').replace('=', '')

                page = requests.get(giftcard_url)
                giftcard_url = page.url  # For topcashback email need to get redirect url not original url

                if page.status_code == 200:

                    if 'asda' in giftcard_url:
                        html_ = page.content
                    elif 'spend.runa' in giftcard_url:

                        # Topcashback now uses a new giftcard provider that loads giftcards via Javascript so need selenium now
                        # driver.get(giftcard_url)
                        # WebDriverWait(driver, 15).until(lambda driver: driver.find_element('id', "accountnumber_pin")) # Should wait for JS to finish loading
                        # html_ = driver.page_source

                        url = 'https://connect.runa.io/internal-service-api/wallet/asset/' + giftcard_url.split('/')[-1]

                        logger.debug(f'url: {url}')

                        # url = "https://connect.runa.io/internal-service-api/wallet/asset/2b5aa276-e9e7-49ec-9e2e-3401a2ec9085"

                        headers = {
                            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/112.0",
                            "Accept": "application/json",
                            "Accept-Language": "en-GB,en;q=0.5",

                            # Changed encoding to get json, works if the API supports exporting directly as utf-8, can't be generalized as a solution imo
                            # https://stackoverflow.com/a/67799052
                            # "Accept-Encoding": "gzip, deflate, br",
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

                        if external_redemption_url is None or 'asda' not in external_redemption_url:
                            continue

                        page = requests.get(external_redemption_url)
                        giftcard_url = page.url
                        html_ = page.content

                    else:
                        continue

                    soup = BeautifulSoup(html_, 'html.parser')

                    a = soup.prettify()
                    soup.findAll('iframe')

                    aq = soup.select('div[id*="accountnumber_pin"]')

                    numbers = re.sub('\D', '', aq[0].text)

                    card_number = numbers[:16]
                    pin = numbers[-4:]

                    link = soup.findAll('a', attrs={'class': 'apple-wallet-badge'})[0]

                    link = link['href']

                    x = 0

                    if card_number not in cards_from_email:
                        cards_from_email.append(card_number)

                    while x < 3:

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
                                logger.info(f'Card to be deleted: {card_id} with balance {balance}')
                                cards_to_delete.append(img_filename)
                                mail_to_delete.append(item)
                            else:

                                notification_manager.push_notification(PUSH_TITLE, f"Card: {card_id}\nCurrent balance: {balance}")

                                if img_filename not in current_giftcards_in_album:
                                    driver.get(giftcard_url)

                                    S = lambda X: driver.execute_script('return document.body.parentNode.scroll' + X)
                                    driver.set_window_size(S('Width'), S('Height'))

                                    driver.save_screenshot(
                                        directory + '/' + img_filename) if WORKING_ENV == 'PROD' else driver.find_element(
                                        By.TAG_NAME, 'body').screenshot(directory + '/' + img_filename)

                            data.append([card_id, balance, link])
                            logger.info(f'{card_id}-{pin}: £{balance}')
                            total += balance

                            break

                        else:
                            x += 1
                            logger.debug(f'Card number: {card_number}')
                            logger.debug(f'Pin: {pin}')
                            logger.error(f'Response message: {response["message"]}')
                        if x == 2:
                            data.append([card_number, response['message'], '-'])
                            logger.debug(f'Card number: {card_number}')
                            logger.debug(f'Pin: {pin}')
                            logger.error(f'Response message: {response["message"]}')
                            break

    files = [x for x in glob.glob(os.path.join(directory, '*')) if 'giftcard' in x]
    logger.info('Directory: %s', directory)
    logger.info('Files: %s', files)

    if files:
        if WORKING_ENV == 'PROD':
            media_items = batch_upload(files=files)
        else:
            media_items = batch_upload(directory=directory)

        time.sleep(5)
        move_media(media_items)

        for f in files:
            os.remove(f)

    logger.info('Cards only in album: %s', cardnumbers_from_album)

    cards_to_delete = list(set(cards_to_delete))

    logger.info('Cards to be deleted: %s', cards_to_delete)
    logger.info('Total Balance: %s', total)

    push_content = f"Current Total Balance: {total}"

    if cards_to_delete:
        time.sleep(2)
        media_to_delete = get_media_items_id(filter_=cards_to_delete)
        notification_manager.push_notification(PUSH_TITLE, f"{push_content}\nDeleted cards {cards_to_delete}")

        # push_notification(NOTIFICATION_TOKEN, "ASDA Giftcards",
        #                   f"Current balance: {total}\nDeleted cards {cards_to_delete}")
        if media_to_delete:
            remove_media(media_to_delete)
    else:
        notification_manager.push_notification(PUSH_TITLE, push_content)

    email_client.delete_email(mail_to_delete)
    email_client.logout()

    dic_ = [{'card_id': x[0], 'balance': x[1], 'link': x[2]} for x in data]

    with giftcards_table.batch_writer(overwrite_by_pkeys=['card_id']) as batch:
        for row in dic_:
            giftcard_dic = json.loads(json.dumps(row), parse_float=Decimal)
            logger.info(f"Updated challenge {giftcard_dic['card_id']} in giftcard table")
            batch.put_item(Item=giftcard_dic)

    driver_manager.close_driver()

    return json.dumps({
        "statusCode": 200,
        "body": {
            'message':'Giftcard lambda invoke successful',
            'Balance': total,
            'Added': files,
            'Deleted': cards_to_delete
        }
    }, indent=4)


if not os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
    print(handler())
