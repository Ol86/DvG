import ast
import time

import grpc
import pika

from . import rechnung_pb2, rechnung_pb2_grpc

connection = pika.BlockingConnection(
    pika.ConnectionParameters("localhost"),
)
channel = connection.channel()

channel.queue_declare(
    queue="rechnung_queue",
    durable=True,
    arguments={"x-queue-type": "quorum"},
)


def callback(ch, method, properties, body):
    message = ast.literal_eval(body.decode())
    print(f"Processing message: {message}")
    time.sleep(10)
    with grpc.insecure_channel("localhost:50051") as grpc_channel:
        stub = rechnung_pb2_grpc.RechnungServiceStub(grpc_channel)
        response = stub.MarkRechnungAsPaid(
            rechnung_pb2.RechnungPaiedRequest(
                id=message["id"],
            )
        )
    print(f"Done processing message: {response.success}")
    ch.basic_ack(delivery_tag=method.delivery_tag)


def run() -> None:
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="rechnung_queue", on_message_callback=callback)
    print("Waiting for messages. To exit press CTRL+C")
    channel.start_consuming()
