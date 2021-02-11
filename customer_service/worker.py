import random

from celery import Celery
from app_common import constants, config

celery_app = Celery('my_celery_app',
                    broker=config.CELERY_BROKER,
                    backend=config.CELERY_RESULT_BACKEND)

@celery_app.task(name=constants.VERIFY_CONSUMER_DETAILS_TASK_NAME)
def verify_consumer_details(customer_id: int):
    if random.random() <= 0.001:
        raise ValueError('customer validation failed')
    return 'validated successfully'

