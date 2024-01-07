import json
import os
from datetime import datetime, timedelta
import pandas as pd

from dotenv import load_dotenv
load_dotenv(verbose=True, override=True)

AUTH_SECRET = os.getenv('AUTH_SECRET')
USER_ID = os.getenv('USER_ID')
PASS_ID = os.getenv('PASS_ID')
CALENDAR_ID = os.getenv('CALENDAR_ID')
SITEKEY = os.getenv('SITEKEY')
CLIENT_ID = os.getenv('CLIENT_ID')
WORKING_ENV = os.getenv('WORKING_ENV', 'DEV')
NOTIFICATION_TOKEN = os.getenv('NOTIFICATION_TOKEN')
AWS_ACC_ID = os.getenv('AWS_ACC_ID')

import sys

sys.path.append('../')

from common.aws_connection import connect_to_dynamodb, get_session
from common.google_calendar import create_event, get_events, update_event, delete_event
from common.push_notifications import push_notification
from plutus_api.api import PlutusApi


def handler(event, context):

    api = PlutusApi(USER_ID, PASS_ID, AUTH_SECRET, CLIENT_ID)
    session = api.login()

    transactions = api.get_transactions(session)

    # ppp = pd.DataFrame.from_dict(transactions)
    # qqq = ppp[ppp['amount'] != 0.0]

    perks = api.get_perks(session)

    rewards = api.get_rewards(session)

    price = api.get_current_plu_price()

    total_earned = sum(rewards['amount'].astype(float))
    current_value = total_earned * float(price)

    # Plu collected per month
    valids = rewards[rewards['reason'] != "Rejected by admin"]
    valids['createdAt'] = pd.to_datetime(valids['createdAt'])
    per = valids.createdAt.dt.to_period("M")
    g = valids.groupby(per)
    # print(g.sum()['amount']) # stopped working TypeError: datetime64 type does not support sum operations
    print(g['amount'].sum()) # new syntax

    """"
    It appears that pandas and Numpy treat None specially when comparing for equality. 
    In pandas, None is supposed to be like NaN, representing a missing value. 
    To find rows where the value is not None (or nan), you could do rewards_df[rewards_df.c.notnull()]
    """
    rejects = rewards[(rewards.reason.notnull()) & (rewards['available'] == False)]
    rejects = rejects[
        ['contis_transaction.description', 'reason', 'contis_transaction.transaction_amount', 'amount', 'createdAt']]

    rejects['calDate'] = rejects['createdAt'] + timedelta(days=46)
    rejects['contis_transaction.transaction_amount'] = rejects['contis_transaction.transaction_amount'].astype(
        float) / 100

    rejects['createdAt'] = rejects['createdAt'].dt.strftime('%d/%m/%Y')
    rejects['calDate'] = rejects['calDate'].dt.strftime('%d/%m/%Y')
    total_rejected = sum(rejects['amount'].astype(float))
    print(f'Total rejected: {total_rejected}')

    rejects_json = json.loads(rejects.to_json(orient="records"))

    # delete_all_events(events, CALENDAR_ID)
    # rewards_from_curve = rewards[rewards['contis_transaction.description'].str.match('CRV*', na=False)]

    rewards_cal = [
        {"Total PLU Earned": total_earned, "Total value": round(current_value, 2), "Total PLU Rejected": total_rejected,
         "Rejected value": total_rejected * float(price)}]
    print(f'Total earned: {total_earned}')

    cal_events = []

    def try_parsing_date(text):
        for fmt in ('%Y-%m-%dT%H:%M:%S.%f+00:00', '%Y-%m-%dT%H:%M:%S+00:00'):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                pass
        raise ValueError('no valid date format found')

    events = get_events(calendar_id=CALENDAR_ID)
    lis = [event['description'].casefold() for event in events]

    # filter out refunds '35' and unsettled '0'
    transactions = [d for d in transactions if ((d['type'] not in ['35','0', 'CARD_REFUND']) and (d['amount'] != 0.0))]

    # Transactions rejected before review/pending state
    for x in transactions:

        # if x['type'] in ['LOAD_PLUTUS_CARD_FROM_WALLET', 'DEPOSIT_FUNDS_RECEIVED']
        # if (x['description'] not in [None, 'Plutus - Load a card with deposit']) and (x['type'] != '35'):
        if x['description'] not in [None, 'Plutus - Load a card with deposit']:

            # x['fiat_transaction.reference_type'] == 'card_transactions'
            if (x['id'] not in rewards['reference_id'].unique()):
                # and (x['id'] not in rewards['fiat_transaction.reference_id'].unique()) and (x['id'] not in rewards['fiat_transaction.id'].unique()):

                # Add space before title to bring to top
                # https://support.google.com/calendar/thread/10149893/how-do-i-reorder-all-day-events-in-calendar?hl=en

                title = x['description']
                id_ = x['id']

                cal_start = try_parsing_date(x['date'])
                # print(cal_start)
                cal_end = cal_start + timedelta(days=1)

                matches = [s for s in lis if id_.casefold() in s]

                if not matches:

                    if (((cal_start + timedelta(days=2)).replace(hour=10, minute=0, second=0) - datetime.now()).days >= 0) or x['type'] == 'AUTHORISATION':

                        # In validation
                        title = " Pending - "+title
                        create_event(title, cal_start.strftime('%Y-%m-%d'), cal_end.strftime('%Y-%m-%d'),
                                     calendar_id=CALENDAR_ID,
                                     description=f"In Pending\n{x['id']}\n{cal_start.strftime('%d-%m-%Y')}\n£{abs(x['amount']) / 100}",
                                     colour=6)
                    else:
                        # No reward
                        title = " No reward - "+title
                        create_event(title, cal_start.strftime('%Y-%m-%d'), cal_end.strftime('%Y-%m-%d'),
                                     calendar_id=CALENDAR_ID,
                                     description=f"No reward\n{x['id']}\n{cal_start.strftime('%d-%m-%Y')}\n£{abs(x['amount']) / 100}",
                                     colour=8)


                    cal_events.append({'type': 'Created', 'title': title, 'date': cal_start.strftime('%Y-%m-%d')})
                    continue

                else:

                    idx = lis.index(matches[0].casefold())

                    if (((cal_start + timedelta(days=2)).replace(hour=10, minute=0, second=0) - datetime.now()).days >= 0) or x['type'] == 'AUTHORISATION':
                    # if (cal_start - datetime.now()).days < -1:
                        # In validation
                        title = " Pending - "+title
                        description = f"In Pending\n{x['id']}\n{cal_start.strftime('%d-%m-%Y')}\n£{abs(x['amount']) / 100}"
                        colour = '6'

                    else:
                        # No reward
                        title = " No reward - "+title
                        description = f"No reward\n{x['id']}\n{cal_start.strftime('%d-%m-%Y')}\n£{abs(x['amount']) / 100}"
                        colour = '8'


                    if (events[idx]['summary'] != title) or (events[idx]['description'] != description) or (events[idx]['colorId'] != colour):

                        event_id = events[idx]['id']
                        update_event(title, cal_start.strftime('%Y-%m-%d'), cal_end.strftime('%Y-%m-%d'),
                                     event_id,
                                     calendar_id=CALENDAR_ID, colour=colour,
                                     description=description)
                        cal_events.append({'type': 'Updated', 'title': title, 'date': cal_start.strftime('%Y-%m-%d')})

            else:

                # id_ = rewards[rewards['reference_id'] == x['id']]['id'][0]

                id_ = x['id']

                matches = [s for s in lis if id_.casefold() in s]

                txn = rewards[rewards['reference_id'] == id_] # For some reason sometimes id in cal is fiat_transaction.reference_id

                if txn['fiat_transaction.reference_id'].notnull().values[0]:
                    matches.extend([s for s in lis if txn['fiat_transaction.reference_id'].values[0].casefold() in s])

                if matches:

                    idx = lis.index(matches[0].casefold())
                    event_id = events[idx]['id']
                    delete_event(event_id, events[idx]['summary'], events[idx]['start']['date'], calendar_id=CALENDAR_ID)
                    # delete_event(event_id, events['summary'], cal_start.strftime('%Y-%m-%d'), calendar_id=CALENDAR_ID)

    events = get_events(calendar_id=CALENDAR_ID)
    lis = [event['description'].casefold() for event in events]
    # x=1
    for index, row in rewards.iterrows():

        # x+=1

        title = row['contis_transaction.description']
        id_ = row['id']

        cal_start = row['createdAt'] + timedelta(days=46)
        # print(cal_start)
        cal_end = cal_start + timedelta(days=1)
        # print(cal_end)

        matches = [s for s in lis if s.startswith(id_.casefold())]

        if not matches:

            description = f"{row['id']}\n£{row['contis_transaction.transaction_amount'] / 100}\n{row['createdAt'].strftime('%d-%m-%Y')}"

            if row['available']:

                if "perk" in row['reference_type']:
                    create_event(" "+title, cal_start.strftime('%Y-%m-%d'), cal_end.strftime('%Y-%m-%d'),
                                 calendar_id=CALENDAR_ID,
                                 description=description, colour=5)
                else:
                    create_event(title, cal_start.strftime('%Y-%m-%d'), cal_end.strftime('%Y-%m-%d'),
                                 calendar_id=CALENDAR_ID,
                                 description=description, colour=2)
            elif row['reason']:
                create_event(title, cal_start.strftime('%Y-%m-%d'), cal_end.strftime('%Y-%m-%d'),
                             calendar_id=CALENDAR_ID,
                             description=description, colour=11)
            else:
                if "perk" in row['reference_type']:
                    create_event(" "+title, cal_start.strftime('%Y-%m-%d'), cal_end.strftime('%Y-%m-%d'),
                                 calendar_id=CALENDAR_ID,
                                 description=description, colour=5)
                else:
                    create_event(title, cal_start.strftime('%Y-%m-%d'), cal_end.strftime('%Y-%m-%d'), calendar_id=CALENDAR_ID,
                                 description=description)

            cal_events.append({'type': 'Created', 'title': title, 'date': cal_start.strftime('%Y-%m-%d')})
            continue

        # if id_.casefold() not in lis:
        idx = lis.index(matches[0].casefold())
        # colour_id = int(events[idx]['colorId'])
        event_id = events[idx]['id']

        description = f"{row['id']}\n£{row['contis_transaction.transaction_amount'] / 100}\n{row['createdAt'].strftime('%d-%m-%Y')}"
        description_with_reason = description+f"\n{row['reason']}"

        if 'colorId' not in events[idx]:
            if row['available'] and (events[idx]['description'] != description_with_reason):
                if "perk" in row['reference_type']:
                    update_event(" "+title, cal_start.strftime('%Y-%m-%d'), cal_end.strftime('%Y-%m-%d'), event_id,
                                 calendar_id=CALENDAR_ID, colour=5,
                                 description=description_with_reason)
                else:
                    update_event(title, cal_start.strftime('%Y-%m-%d'), cal_end.strftime('%Y-%m-%d'), event_id,
                                 calendar_id=CALENDAR_ID, colour=2,
                                 description=description_with_reason)

                cal_events.append({'type': 'Accepted', 'title': title, 'date': cal_start.strftime('%Y-%m-%d')})

            elif row['reason'] and (events[idx]['description'] != description_with_reason):
                update_event(" "+title, cal_start.strftime('%Y-%m-%d'), cal_end.strftime('%Y-%m-%d'), event_id,
                             calendar_id=CALENDAR_ID, colour=11,
                             description=description_with_reason)
                cal_events.append({'type': 'Rejected', 'title': title, 'date': cal_start.strftime('%Y-%m-%d')})

        #     else:
        #         update_event(" "+title, cal_start.strftime('%Y-%m-%d'), cal_end.strftime('%Y-%m-%d'), event_id,
        #                      calendar_id=CALENDAR_ID,
        #                      description=description)
        # else:
        #     if row['available'] and ("perk" in row['reference_type']) and ((events[idx]['colorId'] != '5') or (events[idx]['description'] != description_with_reason)):
        #         update_event(title, cal_start.strftime('%Y-%m-%d'), cal_end.strftime('%Y-%m-%d'), event_id,
        #                      calendar_id=CALENDAR_ID, colour=5,
        #                      description=description_with_reason)
        #         cal_events.append({'type': 'Accepted', 'title': title, 'date': cal_start.strftime('%Y-%m-%d')})
        #
        #     elif row['available'] and ((events[idx]['colorId'] != '2') or (events[idx]['description'] != description_with_reason)):
        #         update_event(title, cal_start.strftime('%Y-%m-%d'), cal_end.strftime('%Y-%m-%d'), event_id,
        #                      calendar_id=CALENDAR_ID, colour=2,
        #                      description=description_with_reason)
        #         cal_events.append({'type': 'Accepted', 'title': title, 'date': cal_start.strftime('%Y-%m-%d')})
        #
        #     elif row['reason'] and ((events[idx]['colorId'] != '11') or (events[idx]['description'] != description)):
        #         update_event(" "+title, cal_start.strftime('%Y-%m-%d'), cal_end.strftime('%Y-%m-%d'), event_id,
        #                      calendar_id=CALENDAR_ID, colour=11,
        #                      description=description_with_reason)
        #         cal_events.append({'type': 'Rejected', 'title': title, 'date': cal_start.strftime('%Y-%m-%d')})
        #     else:
        #         update_event(" "+title, cal_start.strftime('%Y-%m-%d'), cal_end.strftime('%Y-%m-%d'), event_id,
        #                      calendar_id=CALENDAR_ID,
        #                      description=description)

        # if x > 300:
        #     break


    ## No pushing to Dynamodb till dataframe is cleaned up
    # plutus_table = connect_to_dynamodb('plutus')

    # Only updating transactions modified in last 45 days to reduce db throttle
    # rewards['updatedAt'] = pd.to_datetime(rewards['updatedAt']).dt.date
    # grace_period = datetime.now() - timedelta(days=45)
    # rewards = rewards[rewards['updatedAt'] >= grace_period.date()]

    rewards['plu_price'].mean()
    rewards['plu_price'].max()
    rewards['plu_price'].min()

    # Getting ProvisionedThroughputExceededException
    # with plutus_table.batch_writer(overwrite_by_pkeys=['id']) as batch:
    #     for index, row in rewards.head(500).iterrows():
    #         # print(index)
    #         try:
    #             batch.put_item(json.loads(row.to_json(), parse_float=Decimal))
    #         except Exception as e:
    #             print(f'Error: {e}')
    #             print('Waiting')
    #             time.sleep(1)
    #             batch.put_item(json.loads(row.to_json(), parse_float=Decimal))

    # invoke plutus monthly rewards lambda using boto3
    response = get_session().client('lambda').invoke(FunctionName=f'arn:aws:lambda:eu-west-1:{AWS_ACC_ID}:function:plutus-monthly-limit', InvocationType='RequestResponse')
    response_json = json.loads(response['Payload'].read().decode("utf-8"))

    # push_notification(NOTIFICATION_TOKEN, "Plutus Cashback", json.dumps({ 'Perks': perks, 'Limit': response_json['body']['Rewards']}, ensure_ascii=False))

    return json.dumps({
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": {
            "message": "Plutus Lambda Container image invoked!",
            "Rewards": rewards_cal,
            'Events': cal_events,
            'Rejects': rejects_json,
            'Perks': perks,
            'Limit': response_json['body']['Rewards']
        }
    }, indent=4, ensure_ascii=False)

if not os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
    print(handler(None, None))
