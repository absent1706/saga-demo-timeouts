import asyncapi

from restaurant_service.app_common.messaging.utils import message_to_channel, message_to_component
from restaurant_service.app_common.messaging.restaurant_service_messaging import authorize_card_message

spec = asyncapi.Specification(
    info=asyncapi.Info(
        title='Consumer service', version='1.0.0', description='Some service description goes here...',
    ),
    channels=dict([
        message_to_channel(authorize_card_message.message,
                           authorize_card_message.response)
    ]),
    # all messages met in specification
    components=asyncapi.Components(messages=dict([
        message_to_component(authorize_card_message.message),
        message_to_component(authorize_card_message.response)
    ])),
    servers={'development': asyncapi.Server(
        url='localhost',
        protocol=asyncapi.ProtocolType.REDIS,
        description='Development Broker Server',
    )},
)