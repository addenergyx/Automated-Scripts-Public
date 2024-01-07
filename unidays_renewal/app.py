import requests
import os
import json

from dotenv import load_dotenv

load_dotenv(verbose=True, override=True)

import sys

sys.path.append('../')
from common.captcha_bypass import CaptchaBypass

email_user = os.getenv('USER_ID')
email_pass = os.getenv('PASS_ID')
WORKING_ENV = os.getenv('WORKING_ENV', 'DEV')


def handler(event, context):
    url = "https://account.myunidays.com/GB/en-GB/account/log-in"

    sitekey_clean = '6Ld9uqgUAAAAAKiIVOqkxm7l-Vmpe9F-9ORCOUQg'

    g_response = CaptchaBypass(sitekey_clean, url).bypass()

    payload = f"QueuedPath=/GB/en-GB&EmailAddress={email_user}&Password={email_pass}&g-recaptcha-response={g_response}&GTokenResponse={g_response}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/111.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-GB,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": "https://www.myunidays.com/",
        "ud-source": "www",
        "ud-viewport": "8",
        "ud-style": "default,default,full",
        "ud-validationsubmit": "true",
        "Origin": "https://www.myunidays.com",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Connection": "keep-alive",
    }

    # response = requests.request("POST", url, data=payload, headers=headers)

    s = requests.Session()
    # login_response = s.post(url, data=payload, headers=headers, verify=False)  # login
    login_response = s.post(url, data=payload, headers=headers)  # login
    print(login_response.status_code)
    print(login_response)
    # print(json.loads(login_response.text))

    if login_response.status_code == 200:
        url = "https://account.myunidays.com/GB/en-GB/account/email-verify/fast"
        payload = "PersonalInstitutionEmailAddress=&InstitutionId=73d70876-276b-4dc4-aaae-1765d76ee92d&QueuedPath=/GB/en-GB&Submit=False&EmailOptIn=FALSE&Human="
        # response = s.post(url, data=payload, headers=headers, verify=False)
        response = s.post(url, data=payload, headers=headers)

        print('Passed')

        return {
            "statusCode": response.status_code,
            "body": 'Unidays Lambda Invocation complete'
        }

    print('Failed')

    return {
        "statusCode": login_response.status_code,
        "body": f'Unidays Lambda Invocation Failed: {login_response.text}'
    }


if WORKING_ENV == 'DEV':
    print(handler(None, None))
