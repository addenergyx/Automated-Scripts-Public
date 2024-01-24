import time
import re
from imessage_reader import fetch_data
from dotenv import load_dotenv
import pandas as pd
import boto3
import os
import sys

load_dotenv(verbose=True, override=True)

AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_DEFAULT_REGION = "eu-west-1"


class TextBypass(object):

    def __init__(self, system=None):
        if system is None:
            self.operating_system = os.name

    def _check_system(self):
        # 'nt' is the value for windows, getting code from imessage only works on mac
        if self.operating_system == "nt":
            sys.exit("Your operating system is not supported yet!")

    # def __init__(self, text, institute):
        # self.text = text
        # self.institute = institute

    def get_code(self, text):

        # Check the running operating system
        self._check_system()

        time.sleep(10)
        fd = fetch_data.FetchData('/Users/david/Library/Messages/chat.db')
        my_data = fd.get_messages()

        messages = [message for message in my_data if message[1] and text in message[1]]

        # Needed for paypal because 2 phone numbers codes can be sent from
        df = pd.DataFrame(messages)
        df[2] = pd.to_datetime(df[2])
        df.sort_values(by=[2], inplace=True, ascending=False)

        return re.sub('\D', '', df.iloc[0][1])[:6]

    def check_code(self, text, institute):
        global previous_code
        dynamodb = boto3.resource(
            'dynamodb',
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=AWS_DEFAULT_REGION
        )
        # import pandas as pd
        checkpoints = dynamodb.Table('checkpoints')
        scan = checkpoints.scan()

        for item in scan['Items']:
            if item['checkpoint_id'] == institute:
                previous_code = item['code']
                break
            previous_code = ''

        code = self.get_code(text)

        if not previous_code:
            checkpoints.put_item(Item={"checkpoint_id": institute, 'code': code})
            return code

        tries = 0
        while previous_code == code:
            code = self.get_code(text)
            tries += 1

            print('Attempt: ', tries)
            time.sleep(10)

            # TODO: Click resend code at multiples of 3 (if tries % 3 == 0)

            if tries >= 6:
                print('Failed to get code')
                break

        checkpoints.put_item(Item={"checkpoint_id": institute, 'code': code})

        return code

    # def otp_bypass(driver):
    #     radio_btn = driver.find_element('css selector', "input[id='sms-challenge-option']")
    #     driver.execute_script("arguments[0].click();", radio_btn)
    #     driver.find_element('class name', 'challenge-submit-button').click()
    #     code = check_code("PayPal: ", 'paypal')
    #     driver.find_element('id', 'ci-answer-0').send_keys(code)
    #     driver.find_element('id', 'securityCodeSubmit').click()
