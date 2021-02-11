import random
import logging

from celery import Celery
from flask import Flask

from app_common import constants, config

logging.basicConfig(level=logging.DEBUG)

celery_app = Celery('my_celery_app',
                    broker=config.CELERY_BROKER,
                    backend=config.CELERY_RESULT_BACKEND)

app = Flask(__name__)


@app.route('/create-order/timeout')
def create_order():
    result = celery_app.send_task(constants.VERIFY_CONSUMER_DETAILS_TASK_NAME,
                                  [random.randint(1, 100)])
    logging.info(f'created task {result}. waiting for result ...')
    return result.get(propagate = False)

if __name__  == '__main__':
    result = create_order()
