# -*- coding: utf-8 -*-
import imaplib
import email
from bs4 import BeautifulSoup
import re
# import pandas as pd
import boto3
from decimal import Decimal
import json
from dotenv import load_dotenv
import os
import requests
import time
import glob
# import chromedriver_autoinstaller
from selenium import webdriver
# from weasyprint import HTML, CSS
# from html2image import Html2Image
from selenium.webdriver.common.by import By
import logging

load_dotenv(verbose=True, override=True)

import sys

sys.path.append('../')

from common.google_photos_upload import get_media_items_name, get_media_items_id, batch_upload, remove_media, move_media
from common.captcha_bypass import CaptchaBypass
from common.push_notifications import push_notification

logging.basicConfig(
    format='%(asctime)s %(message)s',
    level=logging.INFO,
    datefmt='%d-%m-%Y %H:%M:%S')

logger = logging.getLogger()
logger.info('The script is starting.')

email_user = os.getenv('DASHBOARD_EMAIL')
email_pass = os.getenv('DASHBOARD_PASS')
ANTICAPTCHA_KEY = os.getenv('ANTICAPTCHA_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_DEFAULT_REGION = "eu-west-1"
WORKING_ENV = os.getenv('WORKING_ENV', 'DEV')
NOTIFICATION_TOKEN = os.getenv('NOTIFICATION_TOKEN')

def handler(event=None, context=None):
    if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
        from common.lambda_scraper import get_driver
        driver = get_driver()  # Driver installed and set in docker
        directory = '/tmp'
    else:
        # from common.scraper import get_driver
        # driver = get_driver(headless=True)

        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service as ChromeService
        # chromedriver_autoinstaller.install()
        options = webdriver.ChromeOptions()
        # options.add_argument("--no-sandbox")  # Must have this flag for docker
        options.add_argument("--headless")
        # options.add_argument("--disable-gpu")
        # options.add_argument("--disable-extensions")
        # options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

        # print('DEV')
        # from common.scraper import get_driver
        # driver = get_driver(headless=True)

        directory = os.path.join(os.getcwd(), 'images')

    # driver = get_driver(headless=True)

    # driver.get('https://www.tesco.com/account/login/en-GB/')

    # driver = webdriver.Remote("http://127.0.0.1:4444/wd/hub", DesiredCapabilities.CHROME)

    # sitekey = driver.find_element(By.XPATH, '//*[@id="recaptcha-demo"]').get_attribute('outerHTML')
    # sitekey_clean = sitekey.split('" data-callback')[0].split('data-sitekey="')[1]

    # # TODO: get sitekey, is in the iframe kdriver = webdriver.Chrome(options = options)=
    # # https://anti-captcha.com/apidoc/articles/how-to-find-the-sitekey
    sitekey_clean = '6LcGYtkZAAAAAHu9BgC-ON7jeraLq5Tgv3vFQzZZ'
    # print(sitekey_clean)

    balance_checker_url = "https://www.asdagiftcards.com/balance-check"

    api_url = "https://api.asdagiftcards.com/api/v1/balance"

    port = 993

    SMTP_SERVER = "imap.gmail.com"

    mail = imaplib.IMAP4_SSL(SMTP_SERVER)

    mail.login(email_user, email_pass)

    mail.select('giftcards')

    status, mailbox = mail.search(None, 'ALL')

    mailbox_list = mailbox[0].split()

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

    # scan = giftcards_table.scan()
    # current_giftcards_ddb = pd.DataFrame(scan['Items'])['card_id'].tolist()
    # current_giftcards[current_giftcards['balance'].astype(float) > 0]['card_id'].tolist()

    current_giftcards_in_album = get_media_items_name()

    for item in current_giftcards_in_album:
        cardnumbers_from_album.append(re.sub('\D', '', item))

    data = []

    for item in mailbox_list:

        # item = mailbox_list[-1]

        # for num in data[0].split():
        status, body = mail.fetch(item, '(RFC822)')
        email_msg = body[0][1]

        email_message = email.message_from_bytes(email_msg)

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
            # print(content_type)

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
                    giftcard_url = giftcard_url.replace('\n', '').replace('\r', '').replace('=', '')

                page = requests.get(giftcard_url)
                giftcard_url = page.url  # For topcashback email need to get redirect url not original url

                if page.status_code == 200:

                    print(giftcard_url)

                    if 'asda' in giftcard_url:
                        html_ = page.content
                    elif 'spend.runa' in giftcard_url:

                        # Topcashback now uses a new giftcard provider that loads giftcards via Javascript so need selenium now
                        # driver.get(giftcard_url)
                        # WebDriverWait(driver, 15).until(lambda driver: driver.find_element('id', "accountnumber_pin")) # Should wait for JS to finish loading
                        # html_ = driver.page_source

                        # giftcard_url = 'https://spend.runa.io/223a51f7-ef12-4c65-a44a-c44fea2c17db'

                        url = 'https://connect.runa.io/internal-service-api/wallet/asset/' + giftcard_url.split('/')[-1]

                        print('url: '+ url)

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
                            # "Content-Type": "application/json"
                        }

                        redirect = requests.get(url, headers=headers, verify=False, allow_redirects=True)

                        # redirect.encoding = redirect.apparent_encoding

                        # print(redirect.content)
                        # print(redirect.text)
                        # print(redirect.json)

                        response = json.loads(redirect.content)

                        external_redemption_url = redirect.json()['redemptionInformation']['externalRedemptionUrl']

                        page = requests.get(external_redemption_url)
                        giftcard_url = page.url
                        html_ = page.content

                    else:
                        break

                    soup = BeautifulSoup(html_, 'html.parser')
                    # print(soup.prettify())

                    a = soup.prettify()
                    soup.findAll('iframe')

                    aq = soup.select('div[id*="accountnumber_pin"]')

                    numbers = re.sub('\D', '', aq[0].text)

                    card_number = numbers[:16]
                    pin = numbers[-4:]

                    # print(pin)

                    link = soup.findAll('a', attrs={'class': 'apple-wallet-badge'})[0]

                    link = link['href']

                    x = 0

                    if card_number not in cards_from_email:
                        cards_from_email.append(card_number)

                    while x < 3:

                        g_response = CaptchaBypass(sitekey_clean, balance_checker_url).bypass()

                        payload = {
                            "number": card_number,
                            "pin": pin,
                            "recaptcha": g_response
                        }

                        headers = {
                            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:104.0) Gecko/20100101 Firefox/104.0",
                            "Accept": "application/json, text/plain, */*",
                        }

                        response = requests.request("POST", api_url, json=payload, headers=headers).json()

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
                                mail_to_delete.append(item)
                            else:

                                push_notification(NOTIFICATION_TOKEN, "ASDA Giftcards", f"Card: {card_id}\nCurrent balance: {balance}")

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
                            # print(response['response_code'])
                            # print(response['errors'])
                            print(response['message'])

                        if x == 2:
                            data.append([card_number, response['message'], '-'])
                            print(card_number)
                            print(pin)
                            # print(response['response_code'])
                            # print(response['errors'])
                            print(response['message'])
                            break

    # Sometimes empty cards are removed from email but not deleted from photo album.
    # This is to ensure they are deleted
    # for item in cardnumbers_from_album:

    #     if item not in cards_from_email:

    #         print('card only in album')

    #         # get pin from aws
    #         link = giftcards_table.get_item(Key={'card_id': item})['Item']['link']  # pin not in dynamodb
    #         pin = link.split('/')[7]

    #         g_response = CaptchaBypass(sitekey_clean, balance_checker_url).bypass()

    #         payload = {
    #             "number": item,
    #             "pin": pin,
    #             "recaptcha": g_response
    #         }

    #         headers = {
    #             "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:104.0) Gecko/20100101 Firefox/104.0",
    #             "Accept": "application/json, text/plain, */*",
    #         }

    #         response = requests.request("POST", api_url, json=payload, headers=headers).json()

    #         balance = response['new_balance']

    #         balance = float(balance[:-2] + '.' + balance[-2:])

    #         print(f'{item}-{pin}: £{balance}')

    #         if float(balance) <= 0.0:
    #             img_filename = 'giftcard_' + item + '.png'
    #             cards_to_delete.append(img_filename)
    #         else:
    #             total += float(balance)
    #             print(f'New total: £{total}')

    files = [x for x in glob.glob(os.path.join(directory, '*')) if 'giftcard' in x]
    print(directory)
    print(files)
    print('-------------')

    if files:
        if WORKING_ENV == 'PROD':
            media_items = batch_upload(files=files)
        else:
            media_items = batch_upload(directory=directory)

        time.sleep(5)
        move_media(media_items)

        for f in files:
            os.remove(f)

    print('Cards only in album:')
    print(cardnumbers_from_album)

    cards_to_delete = list(set(cards_to_delete))

    print('Cards to be deleted:')
    print(cards_to_delete)

    print('Total Balance:')
    print(total)

    if cards_to_delete:
        time.sleep(2)
        media_to_delete = get_media_items_id(filter_=cards_to_delete)
        push_notification(NOTIFICATION_TOKEN, "ASDA Giftcards",
                          f"Current balance: {total}\nDeleted cards {cards_to_delete}")
        if media_to_delete:
            remove_media(media_to_delete)

    # Not sure what max list for google api is. May need to use chunks
    # if len(cards_to_delete) > 10:
    #     splits = [cards_to_delete[i:i+10] for i in range(0, len(cards_to_delete), 10)]
    #
    #     for chunk in splits:
    #         time.sleep(2)
    #         media_to_delete = get_media_items_id(filter_=chunk)
    #         if media_to_delete:
    #             remove_media(media_to_delete)
    #
    # elif cards_to_delete:
    #     time.sleep(2)
    #     media_to_delete = get_media_items_id(filter_=cards_to_delete)
    #     if media_to_delete:
    #         remove_media(media_to_delete)

    for email_item in mail_to_delete:
        mail.store(email_item, "+FLAGS", "\\Deleted")

    # permanently remove mails that are marked as deleted
    # from the selected mailbox
    mail.expunge()
    # close the mailbox
    mail.close()
    # logout from the account
    mail.logout()

    # Avoiding pandas as layer is too big
    # column_headers = ['card_id', 'balance', 'link']
    # balances = pd.DataFrame(data, columns=column_headers)

    # for index, row in balances.iterrows():
    #     batch.put_item(json.loads(row.to_json(), parse_float=Decimal))
    #     print(row['card_id'])

    dic_ = [{'card_id': x[0], 'balance': x[1], 'link': x[2]} for x in data]

    with giftcards_table.batch_writer(overwrite_by_pkeys=['card_id']) as batch:
        for row in dic_:
            giftcard_dic = json.loads(json.dumps(row), parse_float=Decimal)
            logger.info(f"Updated challenge {giftcard_dic['card_id']} in giftcard table")
            batch.put_item(Item=giftcard_dic)

    driver.close()
    driver.quit()

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
