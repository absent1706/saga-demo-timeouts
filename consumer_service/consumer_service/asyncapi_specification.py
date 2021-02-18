import asyncapi

from consumer_service.app_common.messaging import consumer_service_messaging
from consumer_service.app_common.messaging.consumer_service_messaging import \
    verify_consumer_details_message
from consumer_service.app_common.messaging.utils import message_to_channel, message_to_component

spec = asyncapi.Specification(
    info=asyncapi.Info(
        title='Consumer service', version='1.0.0',
        description=f'Takes command messages from "{consumer_service_messaging.COMMANDS_QUEUE}" queue',
    ),
    channels=dict([
        message_to_channel(verify_consumer_details_message.message)
    ]),
    # all messages met in specification
    components=asyncapi.Components(messages=dict([
        message_to_component(verify_consumer_details_message.message)
    ])),
    servers={'development': asyncapi.Server(
        url='localhost',
        protocol=asyncapi.ProtocolType.REDIS,
        description='Development Broker Server',
    )},
)