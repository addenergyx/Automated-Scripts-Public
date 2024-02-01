from request_manager import RequestManager
import os

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
def lambda_handler(event, context):
    urls = ['https://indel-app.onrender.com/', 'https://fixed-loan-calculator.onrender.com/']
    request_manager = RequestManager()

    status = None
    for url in urls:
        status = request_manager.make_request(url)
        logger.info(status)

    return {
        'statusCode': 200,
        'body': status
    }

if __name__ == '__main__' and not os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
    lambda_handler(None, None)