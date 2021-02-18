import asyncapi


def message_to_channel(message: asyncapi.Message, response: asyncapi.Message = None, description: str = None):
    channel_kwargs = dict(
        description=description,
        subscribe=asyncapi.Operation(
            message=message,
        )
    )
    if response:
        channel_kwargs['publish'] = asyncapi.Operation(
            message=response,
        )

    return message.name, asyncapi.Channel(**channel_kwargs)


def message_to_component(message: asyncapi.Message):
    return message.name, message
