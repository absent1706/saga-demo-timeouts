import asyncapi

from accounting_service.app_common.messaging.asyncapi_utils import message_to_channel, message_to_component
from accounting_service.app_common.messaging.accounting_service_messaging import authorize_card_message
from accounting_service.app_common.messaging import accounting_service_messaging

spec = asyncapi.Specification(
    info=asyncapi.Info(
        title='Consumer service', version='1.0.0',
        description=f'Takes command messages from "{accounting_service_messaging.COMMANDS_QUEUE}" queue',
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