import logging

from celery import Celery

from consumer_service.app_common import settings
from consumer_service.app_common.messaging.consumer_service_messaging import \
    verify_consumer_details_message
from consumer_service.app_common.messaging import consumer_service_messaging

logging.basicConfig(level=logging.DEBUG)

command_handlers_celery_app = Celery(
    'consumer_command_handlers',
    broker=settings.CELERY_BROKER,
    backend=settings.CELERY_RESULT_BACKEND)
command_handlers_celery_app.conf.task_default_queue = consumer_service_messaging.COMMANDS_QUEUE


@command_handlers_celery_app.task(name=verify_consumer_details_message.TASK_NAME)
def verify_consumer_details_task(payload: dict):
    payload = verify_consumer_details_message.Payload(**payload)

    if payload.consumer_id < 50:
        raise ValueError('customer validation failed')
    return 'validated successfully'
