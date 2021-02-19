import asyncapi


def message_to_channel(message: asyncapi.Message, response: asyncapi.Message = None, publish_made_first=False, description: str = None):
    if publish_made_first:
        first_action, second_action = 'publish', 'subscribe'
    else:
        first_action, second_action = 'subscribe', 'publish'

    channel_kwargs = {
        'description': description,
        first_action: asyncapi.Operation(
            message=message,
        )
    }
    if response:
        channel_kwargs[second_action] = asyncapi.Operation(
            message=response,
        )

    return message.name, asyncapi.Channel(**channel_kwargs)


def message_to_component(message: asyncapi.Message):
    return message.name, message
