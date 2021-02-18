import logging
import random
from dataclasses import asdict

from celery import Celery

from restaurant_service.app_common import settings
from restaurant_service.app_common.messaging import restaurant_service_messaging
from restaurant_service.app_common.messaging.restaurant_service_messaging import \
    create_ticket_message

logging.basicConfig(level=logging.DEBUG)

command_handlers_celery_app = Celery(
    'restaurant_command_handlers',
    broker=settings.CELERY_BROKER,
    backend=settings.CELERY_RESULT_BACKEND)
command_handlers_celery_app.conf.task_default_queue = restaurant_service_messaging.COMMANDS_QUEUE


@command_handlers_celery_app.task(name=create_ticket_message.TASK_NAME)
def create_ticket_task(payload: dict):
    payload = create_ticket_message.Payload(**payload)

    # in real app, we would create a ticket in restaurant service DB
    # here, we will just generate some fake ID of just created ticket

    ticket_id = random.randint(200, 300)

    return asdict(create_ticket_message.Response(ticket_id=ticket_id))
