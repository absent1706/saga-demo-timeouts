import enum
import logging
import os
import random

from celery import Celery
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from saga import SagaBuilder
from sqlalchemy_mixins import AllFeaturesMixin

from app_common import constants, settings

logging.basicConfig(level=logging.DEBUG)

celery_app = Celery('my_celery_app',
                    broker=settings.CELERY_BROKER,
                    backend=settings.CELERY_RESULT_BACKEND)

app = Flask(__name__)

current_dir = os.path.abspath(os.path.dirname(__file__))
app.config[
    'SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{current_dir}/order_service.db"

db = SQLAlchemy(app, session_options={'autocommit': True})


class OrderStatuses(enum.Enum):
    PENDING_VALIDATION = 'pending_validation'
    APPROVED = 'approved'
    REJECTED = 'rejected'


class CreateOrderSagaStatuses(enum.Enum):
    ORDER_CREATED = 'ORDER_CREATED'
    VERIFYING_CONSUMER_DETAILS = 'VERIFYING_CONSUMER_DETAILS'
    SUCCEEDED = 'SUCCEEDED'
    FAILED = 'FAILED'


class BaseModel(db.Model, AllFeaturesMixin):
    __abstract__ = True
    pass


class Order(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Enum(OrderStatuses),
                       default=OrderStatuses.PENDING_VALIDATION)
    consumer_id = db.Column(db.Integer)


class CreateOrderSagaState(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Enum(CreateOrderSagaStatuses),
                       default=CreateOrderSagaStatuses.ORDER_CREATED)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))


BaseModel.set_session(db.session)
db.create_all()  # "run migrations"


@app.route('/create-order/timeout')
def create_order():
    order = Order.create(consumer_id=random.randint(1, 100))

    CreateOrderSaga(order).execute()
    return 'ok'


class CreateOrderSaga:
    NO_ACTION = lambda *args: None

    def __init__(self, order):
        self.saga = SagaBuilder.create() \
            .action(self.NO_ACTION, self.reject_order) \
            .action(self.verify_consumer_details, self.NO_ACTION) \
            .action(self.approve_order, self.NO_ACTION) \
            .build()
        # .action(self.restaurant_create_order, self.restaurant_reject_order) \
        # .action(self.accounting_authorize_card, lambda _: _) \
        # .action(self.approve_order, lambda _: _) \

        self.order = order

        self.saga_state = CreateOrderSagaState.create(order_id=order.id)

    def execute(self):
        return self.saga.execute()
        #
        # except SagaError as e:
        #     print('saga error: ', e)  # wraps the BaseException('some error happened')
        #

    def verify_consumer_details(self):
        task_result = celery_app.send_task(
            constants.VERIFY_CONSUMER_DETAILS_TASK_NAME,
            args=[self.order.consumer_id],
            queue=constants.CONSUMER_SERVICE_COMMANDS_QUEUE)
        logging.info('verify consumer command sent')

        self.saga_state.update(
            status=CreateOrderSagaStatuses.VERIFYING_CONSUMER_DETAILS)

        response = task_result.get()
        logging.info(f'Response from customer service: {response}')

    def reject_order(self):
        self.order.update(status=OrderStatuses.REJECTED)
        self.saga_state.update(status=CreateOrderSagaStatuses.FAILED)

        logging.info(f'Compensation: order {self.order.id} rejected')

    def approve_order(self):
        self.order.update(status=OrderStatuses.APPROVED)
        self.saga_state.update(status=CreateOrderSagaStatuses.SUCCEEDED)

        logging.info(f'Order {self.order.id} approved')


if __name__ == '__main__':
    result = create_order()
