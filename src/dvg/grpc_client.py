import sys

import grpc
import pika

from dvg.config import rechnung_pb2, rechnung_pb2_grpc

GRPC_SERVER_ADDRESS = "localhost:50051"
"""The address of the gRPC server."""

connection = pika.BlockingConnection(
    pika.ConnectionParameters("localhost"),
)
rabbit_mq_channel = connection.channel()
"""The RabbitMQ channel for sending messages."""

rabbit_mq_channel.queue_declare(
    queue="rechnung_queue",
    durable=True,
    arguments={"x-queue-type": "quorum"},
)
"""The RabbitMQ queue for sending messages."""


def run() -> None:
    """Run the gRPC client."""
    function = sys.argv[1]
    response = None
    match function:
        case "create":
            _create_rechnung(sys.argv[2], sys.argv[3], float(sys.argv[4]))
        case "get":
            rechnung = _get_rechnung_by_id(int(sys.argv[2]))
            if rechnung is None:
                response = f"Rechnung with id {sys.argv[2]} not found"
            else:
                response = f"Rechnung with id {sys.argv[2]}: {rechnung}"
    print(f"Server replied: {response}")


def _create_rechnung(aussteller: str, empfaenger: str, betrag: float) -> None:
    """Create a new rechnung.

    :param aussteller: The name of the person or company issuing the invoice.
    :param empfaenger: The name of the person or company receiving the invoice.
    :param betrag: The amount of the invoice.
    """
    with grpc.insecure_channel(GRPC_SERVER_ADDRESS) as grpc_channel:
        stub = rechnung_pb2_grpc.RechnungServiceStub(grpc_channel)
        response = stub.CreateRechnung(
            rechnung_pb2.RechnungCreateRequest(
                aussteller=aussteller,
                empfaenger=empfaenger,
                betrag=betrag,
            )
        )
    print(f"Created rechnung with id {response.id}")

    message = {
        "id": response.id,
        "aussteller": aussteller,
        "empfaenger": empfaenger,
        "betrag": betrag,
    }
    rabbit_mq_channel.basic_publish(
        exchange="",
        routing_key="rechnung_queue",
        body=str(message),
        properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent),
    )
    print(f"Sent message to RabbitMQ: {message}")
    connection.close()


def _get_rechnung_by_id(id: int) -> dict | None:
    """Get a rechnung by its id.

    :param id: The id of the rechnung to retrieve.
    :return: The rechnung if found, otherwise None.
    """
    with grpc.insecure_channel(GRPC_SERVER_ADDRESS) as grpc_channel:
        stub = rechnung_pb2_grpc.RechnungServiceStub(grpc_channel)
        response = stub.GetRechnungById(rechnung_pb2.RechnungIdRequest(id=id))
    if response is None:
        return None
    return {
        "aussteller": response.aussteller,
        "empfaenger": response.empfaenger,
        "betrag": response.betrag,
        "ausstellungsdatum": response.ausstellungsdatum,
        "ist_bezahlt": response.ist_bezahlt,
    }
