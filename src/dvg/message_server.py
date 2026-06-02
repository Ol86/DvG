import ast
import time

import grpc
import pika

from dvg.config import rechnung_pb2, rechnung_pb2_grpc
from dvg.config.db import DatabaseHandler

db_handler = DatabaseHandler()

connection = pika.BlockingConnection(
    pika.ConnectionParameters("localhost"),
)
channel = connection.channel()
"""The RabbitMQ channel for consuming messages."""

channel.queue_declare(
    queue="payment_queue",
    durable=True,
    arguments={"x-queue-type": "quorum"},
)
"""The RabbitMQ queue for consuming messages."""


def callback(ch, method, properties, body) -> None:
    """Callback function to process messages from the RabbitMQ queue.

    :param ch: The RabbitMQ channel.
    :param method: The method frame containing delivery information.
    :param properties: The properties of the message.
    :param body: The body of the message, containing the data to process.
    """
    message = ast.literal_eval(body.decode())
    print(f"Processing message: {message}")
    time.sleep(10)
    with grpc.insecure_channel("localhost:50051") as grpc_channel:
        stub = rechnung_pb2_grpc.RechnungServiceStub(grpc_channel)
        response = stub.MarkRechnungAsPaid(
            rechnung_pb2.MarkRechnungAsPaidRequest(
                id=message["id"],
            )
        )
        db_handler.update_rechnung_as_paid(message["id"])
    print(f"Done processing message: {response.success}")
    ch.basic_ack(delivery_tag=method.delivery_tag)


def run() -> None:
    """Run the message server."""
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="payment_queue", on_message_callback=callback)
    print("Waiting for messages. To exit press CTRL+C")
    channel.start_consuming()
