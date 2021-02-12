import logging

from celery import Celery

from app_common import constants, settings

logging.basicConfig(level=logging.DEBUG)

command_handlers_celery_app = Celery(
    'consumer_command_handlers',
    broker=settings.CELERY_BROKER,
    backend=settings.CELERY_RESULT_BACKEND)
command_handlers_celery_app.conf.task_default_queue = constants.CONSUMER_SERVICE_COMMANDS_QUEUE


@command_handlers_celery_app.task(
    name=constants.VERIFY_CONSUMER_DETAILS_TASK_NAME)
def verify_consumer_details(customer_id: int):
    if customer_id < 50:
        raise ValueError('customer validation failed')
    return 'validated successfully'
