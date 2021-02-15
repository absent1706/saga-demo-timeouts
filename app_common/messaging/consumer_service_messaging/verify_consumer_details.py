import dataclasses

import asyncapi


TASK_NAME = 'consumer_service.verify_consumer_details'


@dataclasses.dataclass
class Payload:
    consumer_id: int


message = asyncapi.Message(
    name=TASK_NAME,
    title='Verify consumer details',
    summary='This command makes consumer service verify consumer details',
    payload=Payload,
)
