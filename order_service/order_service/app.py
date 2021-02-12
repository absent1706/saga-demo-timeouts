import enum
import random
import logging
import os

from saga import SagaBuilder
from celery import Celery
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from app_common import constants, config

logging.basicConfig(level=logging.DEBUG)

celery_app = Celery('my_celery_app',
                    broker=config.CELERY_BROKER,
                    backend=config.CELERY_RESULT_BACKEND)

app = Flask(__name__)

current_dir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{current_dir}/order_service.db"

db = SQLAlchemy(app)


class OrderStatuses(enum.Enum):
    NEW = 'new'
    CREATED = 'created'
    FAILED = 'failed'


class OrderSagaStatuses(enum.Enum):
    ORDER_CREATED = 'order_created'
    CREATED = 'created'
    FAILED = 'failed'


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Enum(OrderStatuses))
    customer_id = db.Column(db.Integer)


class OrderSagaState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Enum(OrderStatuses))
    customer_id = db.Column(db.Integer)

db.create_all()  # "run migrations"


@app.route('/create-order/timeout')
def create_order():

    db.session.add(Order(status=OrderStatuses.NEW, customer_id=1))
    db.session.commit()
    return 'ok'
    # result = celery_app.send_task(constants.VERIFY_CONSUMER_DETAILS_TASK_NAME,
    #                               [random.randint(1, 100)])
    # logging.info(f'created task {result}. waiting for result ...')
    # return result.get(propagate=False)


class CreateOrderSaga:
    def __init__(self):
        # let's say staff goes and manually approves that they're able to prepare desired dishes
        # only authorize after restaurant approves order
        # mark order as approved in Order service
        self.saga = SagaBuilder.create() \
                .action(lambda _: _, self.reject_order) \
                .action(self.consumer_verify_consumer_details, lambda _: _) \
                .action(self.restaurant_create_order, self.restaurant_reject_order) \
                .action(self.accounting_authorize_card, lambda _: _) \
                .action(self.approve_order, lambda _: _) \
            .build()


    def create_order(self):
        pass

    def reject_order(self):
        pass
    #
    # except SagaError as e:
    #     print('saga error: ', e)  # wraps the BaseException('some error happened')
    #

if __name__  == '__main__':
    result = create_order()
