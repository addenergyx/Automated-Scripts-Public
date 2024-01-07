import os
import time
from dotenv import load_dotenv
import boto3
import json
# from klarna_browser import KlarnaBrowser

load_dotenv(verbose=True, override=True)

import sys
sys.path.append('../')
from common.push_notifications import push_notification
from common.aws_connection import get_session
from paydown_service.klarna_browser import KlarnaBrowser

NOTIFICATION_TOKEN = os.getenv('NOTIFICATION_TOKEN')
AWS_ACC_ID = os.getenv('AWS_ACC_ID')

# print('Starting paydown service...')

# Get the service resource
sqs = boto3.resource('sqs')

# Get the queue. This returns an SQS.Queue instance
# queue = sqs.get_queue_by_name(QueueName='PaydownServiceQueue')

# print('Queue found...')

# Klanra new card no longer sends emails when transaction is settled
# If there are messages in flight don't rerun job
# if int(queue.attributes["ApproximateNumberOfMessages"]) > 0 and queue.attributes["ApproximateNumberOfMessagesNotVisible"] == '0':

print('Messages in queue...')
# queue.receive_messages(MessageAttributeNames=['MessageBody'])

push_notification(NOTIFICATION_TOKEN, "Klarna Paydown Service", 'Messages in queue...')

email_user = os.getenv('ALT_EMAIL')
email_pass = os.getenv('ALT_PASS')
PHONE_NUM = os.getenv('PHONE_NUM')

browser = KlarnaBrowser(PHONE_NUM, email_user, email_pass)

# total_unpaid_orders = browser.total_unpaid_orders()
#
# # invoke plutus balance lambda using boto3
# print('Getting plutus balance...')
# response = get_session().client('lambda').invoke(
#     FunctionName=f'arn:aws:lambda:eu-west-1:{AWS_ACC_ID}:function:plutus-balance', InvocationType='RequestResponse')
# plutus_balance = json.loads(response['Payload'].read().decode("utf-8"))['body']['balance']
#
# arrears = total_unpaid_orders - plutus_balance

# if arrears >= 0.0:
#     push_notification(NOTIFICATION_TOKEN, "Klarna Paydown Service", f'Paydown service starting in 5 Minutes. Transfer £{"{:.2f}".format(arrears)} to plutus and ensure Curve card is set to Plutus')
#     time.sleep(60*5)
# else:
#     push_notification(NOTIFICATION_TOKEN, "Klarna Paydown Service", 'Paydown service starting in 1 Minute. Set Curve card to Plutus')
#     time.sleep(60)

push_notification(NOTIFICATION_TOKEN, "Klarna Paydown Service", 'Starting paydown service...')

# browser.paydown_klarna(card='Plutus')
browser.paydown_klarna(card='Uphold')
# browser.paydown_klarna()
browser.close()

push_notification(NOTIFICATION_TOKEN, "Klarna Paydown Service", 'Payments Complete')

