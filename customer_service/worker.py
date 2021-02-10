import random

from celery import Celery

app = Celery('my_celery_app', broker='pyamqp://rabbitmq:rabbitmq@localhost//', backend='db+postgresql://postgres:postgres@localhost/postgres')


@app.task(bind=True, name='validate_customer', default_retry_delay = 3)
def add(self, customer_id: int):
    try:
        if random.random() <= 0.9:
            raise ValueError('some error text')
        return 'validated successfully'
    except BaseException as exc:
        raise self.retry(exc=exc)

