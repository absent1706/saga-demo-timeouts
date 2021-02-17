import enum
import logging
import os
import random
from dataclasses import asdict

from celery import Celery
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from saga import SagaBuilder
from sqlalchemy_mixins import AllFeaturesMixin

from app_common import constants, settings
from order_service.app_common.messaging.accounting_service_messaging import \
    authorize_card_message
from order_service.app_common.messaging.consumer_service_messaging import \
    verify_consumer_details_message
from order_service.app_common.messaging import consumer_service_messaging, \
    accounting_service_messaging

logging.basicConfig(level=logging.DEBUG)

celery_app = Celery('my_celery_app',
                    broker=settings.CELERY_BROKER,
                    backend=settings.CELERY_RESULT_BACKEND)

app = Flask(__name__)

current_dir = os.path.abspath(os.path.dirname(__file__))
app.config[
    'SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{current_dir}/order_service.sqlite"

db = SQLAlchemy(app, session_options={'autocommit': True})


class OrderStatuses(enum.Enum):
    PENDING_VALIDATION = 'pending_validation'
    APPROVED = 'approved'
    REJECTED = 'rejected'


class CreateOrderSagaStatuses(enum.Enum):
    ORDER_CREATED = 'ORDER_CREATED'
    VERIFYING_CONSUMER_DETAILS = 'VERIFYING_CONSUMER_DETAILS'
    AUTHORIZING_CREDIT_CARD = 'AUTHORIZING_CREDIT_CARD'
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
    card_id = db.Column(db.Integer)
    price = db.Column(db.Integer)


class CreateOrderSagaState(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Enum(CreateOrderSagaStatuses),
                       default=CreateOrderSagaStatuses.ORDER_CREATED)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    message_id = db.Column(db.String)


BaseModel.set_session(db.session)
db.create_all()  # "run migrations"


@app.route('/create-order/timeout')
def create_order():
    input_data = dict(
        consumer_id=random.randint(1, 100),
        price=random.randint(10, 100),
        card_id=random.randint(1, 5)
    )

    order = Order.create(**input_data)

    # TODO: execute in a separate Celery task
    CreateOrderSaga(order).execute()
    return 'ok'


class CreateOrderSaga:
    NO_ACTION = lambda *args: None

    def __init__(self, order):
        self.saga = SagaBuilder.create() \
            .action(self.NO_ACTION, self.reject_order) \
            .action(self.verify_consumer_details, self.NO_ACTION) \
            .action(self.authorize_card, self.NO_ACTION) \
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
            verify_consumer_details_message.TASK_NAME,
            args=[asdict(
                verify_consumer_details_message.Payload(consumer_id=self.order.consumer_id)
            )],
            queue=consumer_service_messaging.COMMANDS_QUEUE)
        logging.info('verify consumer command sent')

        self.saga_state.update(status=CreateOrderSagaStatuses.VERIFYING_CONSUMER_DETAILS,
                               message_id=task_result.id)

        # It's safe to assume success case.
        # In case task handler throws exception,
        #   Celery automatically raises exception here by itself
        #   and saga library automatically launches compensations
        response = task_result.get()
        logging.info(f'Response from customer service: {response}')

    def reject_order(self):
        self.order.update(status=OrderStatuses.REJECTED)
        self.saga_state.update(status=CreateOrderSagaStatuses.FAILED)

        logging.info(f'Compensation: order {self.order.id} rejected')

    def authorize_card(self):
        task_result = celery_app.send_task(
            authorize_card_message.TASK_NAME,
            args=[asdict(
                authorize_card_message.Payload(card_id=self.order.card_id,
                                               amount=self.order.price)
            )],
            queue=accounting_service_messaging.COMMANDS_QUEUE)
        logging.info('authorize card command sent')

        self.saga_state.update(status=CreateOrderSagaStatuses.AUTHORIZING_CREDIT_CARD,
                               message_id=task_result.id)

        # It's safe to assume success case.
        # In case task handler throws exception,
        #   Celery automatically raises exception here by itself,
        #   and saga library automatically launches compensations
        response = authorize_card_message.Response(**task_result.get())
        logging.info(f'Card authorized. Transaction ID: {response.transaction_id}')

    def approve_order(self):
        self.order.update(status=OrderStatuses.APPROVED)
        self.saga_state.update(status=CreateOrderSagaStatuses.SUCCEEDED, message_id=None)

        logging.info(f'Order {self.order.id} approved')


if __name__ == '__main__':
    result = create_order()
