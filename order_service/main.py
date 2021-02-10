import random
import logging

from celery import Celery

logging.basicConfig(level=logging.DEBUG)

celery_app = Celery('my_celery_app', broker='pyamqp://rabbitmq:rabbitmq@localhost//', backend='db+postgresql://postgres:postgres@localhost/postgres')


result = celery_app.send_task('validate_customer', [random.randint(1, 100)])

