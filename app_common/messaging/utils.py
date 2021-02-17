import asyncapi


def message_to_channel(message: asyncapi.Message, response: asyncapi.Message, description: str = None):
    return message.name, asyncapi.Channel(
        description=description,
        subscribe=asyncapi.Operation(
            message=message,
        ),
        publish=asyncapi.Operation(
            message=response,
        )
    )


def message_to_component(message: asyncapi.Message):
    return message.name, message
