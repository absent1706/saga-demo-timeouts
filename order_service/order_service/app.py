import enum
import logging
import os
import random
import traceback

import mimesis  # for fake data generation
from dataclasses import asdict

from celery import Celery
from celery.exceptions import TimeoutError as CeleryTimeoutError
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from saga import SagaBuilder, SagaError
from sqlalchemy_mixins import AllFeaturesMixin

from order_service.app_common import settings
from order_service.app_common.messaging.accounting_service_messaging import \
    authorize_card_message
from order_service.app_common.messaging.consumer_service_messaging import \
    verify_consumer_details_message
from order_service.app_common.messaging import consumer_service_messaging, \
    accounting_service_messaging, restaurant_service_messaging
from order_service.app_common.messaging.restaurant_service_messaging import \
    create_ticket_message, reject_ticket_message, approve_ticket_message

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
    CREATING_RESTAURANT_TICKET = 'CREATING_RESTAURANT_TICKET'
    APPROVING_RESTAURANT_TICKET = 'APPROVING_RESTAURANT_TICKET'
    AUTHORIZING_CREDIT_CARD = 'AUTHORIZING_CREDIT_CARD'
    SUCCEEDED = 'SUCCEEDED'

    REJECTING_RESTAURANT_TICKET = 'REJECTING_RESTAURANT_TICKET'
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

    items = db.relationship("OrderItem", backref="order")

    transaction_id = db.Column(db.String)
    restaurant_ticket_id = db.Column(db.Integer)


class OrderItem(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    name = db.Column(db.String)
    quantity = db.Column(db.Integer)


class CreateOrderSagaState(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Enum(CreateOrderSagaStatuses),
                       default=CreateOrderSagaStatuses.ORDER_CREATED)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    last_message_id = db.Column(db.String)


BaseModel.set_session(db.session)
db.create_all()  # "run migrations"


@app.route('/ping')
def ping():
    return 'ping response'


BASE_INPUT_DATA = dict(
    items=[
        OrderItem(
           name=mimesis.Food().dish(),  # some fake dish name
           quantity=random.randint(1, 5)
        ),
        OrderItem(
            name=mimesis.Food().dish(),  # some fake dish name
            quantity=random.randint(1, 5)
        )
    ]
)

# magic numbers that make consumer_service succeed or fail
CONSUMER_ID_THAT_WILL_SUCCEED = 70
CONSUMER_ID_THAT_WILL_FAIL = 10
CONSUMER_ID_THAT_WILL_FAIL_BECAUSE_OF_TIMEOUT = 55

# magic numbers that make accounting_service succeed or fail
PRICE_THAT_WILL_SUCCEED = 20
PRICE_THAT_WILL_FAIL = 80


def _run_saga(input_data):
    order = Order.create(**input_data)

    # TODO: execute in a separate Celery task
    try:
        CreateOrderSaga(order).execute()
    except SagaError as e:
        return f'Saga failed: {e} \n . See logs for more details'

    return 'Saga succeeded'


@app.route('/')
def welcome_page():
    return '''
    Welcome to saga orchestration demo!
    You can use next endpoints to start Order Create saga:
    <ul>
      <li><a href="/run-random-saga">/run-random-saga</a></li>
      <li><a href="/run-success-saga">/run-success-saga</a></li>
      <li><a href="/run-saga-failing-on-consumer-verification-because-of-incorrect-id">/run-saga-failing-on-consumer-verification-because-of-incorrect-id</a></li>
      <li><a href="/run-saga-failing-on-consumer-verification-because-of-timeout">/run-saga-failing-on-consumer-verification-because-of-timeout</a></li>
      <li><a href="/run-saga-failing-on-card-authorization">/run-saga-failing-on-card-authorization</a></li>
    </ul>
    '''


@app.route('/run-random-saga')
def run_random_saga():
    # it will randomly pass or fail
    return _run_saga(input_data=dict(
        **BASE_INPUT_DATA,
        consumer_id=random.randint(1, 100),
        price=random.randint(10, 100),
        card_id=random.randint(1, 5)
    ))


@app.route('/run-success-saga')
def run_success_saga():
    # it should succeed
    return _run_saga(input_data=dict(
        **BASE_INPUT_DATA,
        consumer_id=CONSUMER_ID_THAT_WILL_SUCCEED,
        price=PRICE_THAT_WILL_SUCCEED,
        card_id=random.randint(1, 5)
    ))


@app.route('/run-saga-failing-on-consumer-verification-because-of-incorrect-id')
def run_saga_failing_on_consumer_verification_incorrect_id():
    # it should fail on consumer verification stage
    return _run_saga(input_data=dict(
        **BASE_INPUT_DATA,
        consumer_id=CONSUMER_ID_THAT_WILL_FAIL,
        price=PRICE_THAT_WILL_SUCCEED,
        card_id=random.randint(1, 5)
    ))


@app.route('/run-saga-failing-on-consumer-verification-because-of-timeout')
def run_saga_failing_on_consumer_verification_timeout():
    # it should fail on consumer verification stage
    return _run_saga(input_data=dict(
        **BASE_INPUT_DATA,
        consumer_id=CONSUMER_ID_THAT_WILL_FAIL_BECAUSE_OF_TIMEOUT,
        price=PRICE_THAT_WILL_SUCCEED,
        card_id=random.randint(1, 5)
    ))

@app.route('/run-saga-failing-on-card-authorization')
def run_saga_failing_on_card_authorization():
    # it should fail on card authorization stage
    return _run_saga(input_data=dict(
        **BASE_INPUT_DATA,
        consumer_id=CONSUMER_ID_THAT_WILL_SUCCEED,
        price=PRICE_THAT_WILL_FAIL,
        card_id=random.randint(1, 5)
    ))


class CreateOrderSaga:
    NO_ACTION = lambda *args: None
    TIMEOUT = 5  # wait for result for this amount of seconds,
                 # then Celery will raise TimeoutError

    def __init__(self, order):
        self.saga = SagaBuilder.create() \
            .action(self.NO_ACTION, self.reject_order) \
            .action(self.verify_consumer_details, self.NO_ACTION) \
            .action(self.create_restaurant_ticket, self.reject_restaurant_ticket) \
            .action(self.authorize_card, self.NO_ACTION) \
            .action(self.approve_restaurant_ticket, self.NO_ACTION) \
            .action(self.approve_order, self.NO_ACTION) \
            .build()

        self.order = order

        self.saga_state = CreateOrderSagaState.create(order_id=order.id)

    def execute(self):
        try:
            logging.info(f'Starting order create saga #{self.saga_state.id}')
            result = self.saga.execute()
            logging.error(f'Saga #{self.saga_state.id} suceeded')
            return result
        except SagaError as e:
            logging.error(f'Saga #{self.saga_state.id} failed: {e} \n')
            if isinstance(e.action, CeleryTimeoutError):
                logging.error(f'Timeout happened\n')
            if e.compensations:
                logging.error(f'Also, errors occured in some compensations: \n')
                for compensation_exception in e.compensations:
                    logging.error(f'{compensation_exception} \n ----- \n')

            logging.error(f'Full exception trace: \n'
                          f'===========\n'
                          f'{traceback.format_exc()}\n'
                          f'===========\n')
            logging.error('Closing saga')
            # in real world, we would also report this error somewhere
            raise

    def verify_consumer_details(self):
        logging.info(f'Verifying consumer #{self.order.consumer_id} ...')
        task_result = celery_app.send_task(
            verify_consumer_details_message.TASK_NAME,
            args=[asdict(
                verify_consumer_details_message.Payload(consumer_id=self.order.consumer_id)
            )],
            queue=consumer_service_messaging.COMMANDS_QUEUE)

        self.saga_state.update(status=CreateOrderSagaStatuses.VERIFYING_CONSUMER_DETAILS,
                               last_message_id=task_result.id)

        # It's safe to assume success case.
        # In case task handler throws exception,
        #   Celery automatically raises exception here by itself
        #   and saga library automatically launches compensations
        result = task_result.get(timeout=self.TIMEOUT)
        logging.info(f'result = {result}')
        logging.info(f'Consumer #{self.order.consumer_id} verified')

    def reject_order(self):
        self.order.update(status=OrderStatuses.REJECTED)
        self.saga_state.update(status=CreateOrderSagaStatuses.FAILED)

        logging.info(f'Compensation: order {self.order.id} rejected')

    def create_restaurant_ticket(self):
        logging.info('Sending "create restaurant ticket" command ...')
        task_result = celery_app.send_task(
            create_ticket_message.TASK_NAME,
            args=[asdict(
                create_ticket_message.Payload(
                    order_id=self.order.id,
                    customer_id=self.order.consumer_id,
                    items=[
                        create_ticket_message.OrderItem(
                            name=item.name,
                            quantity=item.quantity
                        )
                        for item in self.order.items
                    ]
                )
            )],
            queue=restaurant_service_messaging.COMMANDS_QUEUE)

        self.saga_state.update(status=CreateOrderSagaStatuses.CREATING_RESTAURANT_TICKET,
                               last_message_id=task_result.id)

        # It's safe to assume success case.
        # In case task handler throws exception,
        #   Celery automatically raises exception here by itself,
        #   and saga library automatically launches compensations
        response = create_ticket_message.Response(**task_result.get(timeout=self.TIMEOUT))
        logging.info(f'Restaurant ticket # {response.ticket_id} created')
        self.order.update(restaurant_ticket_id=response.ticket_id)

    def reject_restaurant_ticket(self):
        logging.info(f'Compensation: rejecting restaurant ticket #{self.order.restaurant_ticket_id} ...')
        task_result = celery_app.send_task(
            reject_ticket_message.TASK_NAME,
            args=[asdict(
                reject_ticket_message.Payload(
                    ticket_id=self.order.restaurant_ticket_id
                )
            )],
            queue=restaurant_service_messaging.COMMANDS_QUEUE)

        self.saga_state.update(status=CreateOrderSagaStatuses.REJECTING_RESTAURANT_TICKET,
                               last_message_id=task_result.id)

        task_result.get(timeout=self.TIMEOUT)
        logging.info(f'Compensation: restaurant ticket #{self.order.restaurant_ticket_id} rejected')

    def approve_restaurant_ticket(self):
        logging.info(f'Approving restaurant ticket #{self.order.restaurant_ticket_id} ...')
        task_result = celery_app.send_task(
            approve_ticket_message.TASK_NAME,
            args=[asdict(
                approve_ticket_message.Payload(
                    ticket_id=self.order.restaurant_ticket_id
                )
            )],
            queue=restaurant_service_messaging.COMMANDS_QUEUE)

        self.saga_state.update(status=CreateOrderSagaStatuses.APPROVING_RESTAURANT_TICKET,
                               last_message_id=task_result.id)

        task_result.get(timeout=self.TIMEOUT)
        logging.info(f'Compensation: restaurant ticket #{self.order.restaurant_ticket_id} approved')

    def authorize_card(self):
        logging.info(f'Authorizing card (amount={self.order.price}) ...')
        task_result = celery_app.send_task(
            authorize_card_message.TASK_NAME,
            args=[asdict(
                authorize_card_message.Payload(card_id=self.order.card_id,
                                               amount=self.order.price)
            )],
            queue=accounting_service_messaging.COMMANDS_QUEUE)

        self.saga_state.update(status=CreateOrderSagaStatuses.AUTHORIZING_CREDIT_CARD,
                               last_message_id=task_result.id)

        # It's safe to assume success case.
        # In case task handler throws exception,
        #   Celery automatically raises exception here by itself,
        #   and saga library automatically launches compensations
        response = authorize_card_message.Response(**task_result.get(timeout=self.TIMEOUT))
        logging.info(f'Card authorized. Transaction ID: {response.transaction_id}')
        self.order.update(transaction_id=response.transaction_id)

    def approve_order(self):
        self.order.update(status=OrderStatuses.APPROVED)
        self.saga_state.update(status=CreateOrderSagaStatuses.SUCCEEDED, last_message_id=None)

        logging.info(f'Order {self.order.id} approved')


if __name__ == '__main__':
    result = create_order()
