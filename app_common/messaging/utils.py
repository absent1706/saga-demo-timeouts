import asyncapi


def message_to_channel(message: asyncapi.Message, description: str = None):
    return message.name, asyncapi.Channel(
        description=None,
        subscribe=asyncapi.Operation(
            message=message,
        )
    )


def message_to_component(message: asyncapi.Message):
    return message.name, message
