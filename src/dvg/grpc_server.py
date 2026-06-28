from concurrent import futures
from datetime import datetime

import grpc

from dvg.config import rechnung_pb2, rechnung_pb2_grpc
from dvg.config.db import DatabaseHandler


class RechnungService(rechnung_pb2_grpc.RechnungServiceServicer):
    """gRPC service for managing rechnungen."""

    database_handler: DatabaseHandler

    def __init__(self) -> None:
        self.database_handler = DatabaseHandler()

    def CreateRechnung(
        self,
        request: rechnung_pb2.CreateRechnungRequest,
        context: grpc.ServicerContext,
    ) -> rechnung_pb2.CreateRechnungResponse:
        """Create a new rechnung.

        :param request: The gRPC request containing the rechnung details.
        :param context: The gRPC context for handling the request.
        :return: A gRPC response containing the ID of the created rechnung.
        """
        print(f"[CreateRechnung] - Create Rechnung with request: {request}")
        rechnung = {
            "rechnungsnummer": request.rechnungsnummer,
            "aussteller": request.aussteller,
            "kundennummer": request.kundennummer,
            "zahlungsziel": request.zahlungsziel,
            "bemerkungen": request.bemerkungen,
            "ausstellungsdatum": datetime.strptime(
                request.ausstellungsdatum, "%d.%m.%Y"
            ).date()
            if request.ausstellungsdatum
            else datetime.now().date(),
            "ist_bezahlt": False,
        }
        id = self.database_handler.insert_rechnung(
            rechnung=rechnung,
        )
        print(f"[CreateRechnungsPosition] - Created Rechnung with id:{id}")
        return rechnung_pb2.CreateRechnungResponse(id=id)

    def CreateRechnungsposition(
        self,
        request: rechnung_pb2.CreateRechnungspositionRequest,
        context: grpc.ServicerContext,
    ) -> rechnung_pb2.CreateRechnungspositionResponse:
        """Create a new rechnungsposition for a given rechnung.

        :param request: The gRPC request containing the rechnungsposition details and the ID of the associated rechnung.
        :param context: The gRPC context for handling the request.
        :return: A gRPC response containing the ID of the created rechnungsposition.
        """
        print(
            f"[CreateRechnungsPositio] - Create Rechnungsposition with request: {request}"
        )
        rechnungsposition = {
            "rechnungsposition": request.rechnungsposition,
            "beschreibung": request.beschreibung,
            "menge": request.menge,
            "einheit": request.einheit,
            "einzelpreis": request.einzelpreis,
        }
        id = self.database_handler.insert_rechnungsposition(
            rechnung_id=request.rechnung_id,
            rechnungsposition=rechnungsposition,
        )
        print(f"[CreateRechnungsPosition] - Created RechnungsPosition with id:{id}")
        return rechnung_pb2.CreateRechnungspositionResponse(id=id)

    def MarkRechnungAsPaid(
        self,
        request: rechnung_pb2.MarkRechnungAsPaidRequest,
        context: grpc.ServicerContext,
    ) -> rechnung_pb2.MarkRechnungAsPaidResponse:
        """Mark a rechnung as paid.

        :param request: The gRPC request containing the ID of the rechnung to mark as paid.
        :param context: The gRPC context for handling the request.
        :return: A gRPC response indicating the success of the operation.
        """
        print(f"[MarkRechnungAsPaid] - Marking Rechnung with id: {request.id} as paid")
        self.database_handler.update_rechnung_as_paid(
            rechnung_id=request.id,
        )
        return rechnung_pb2.MarkRechnungAsPaidResponse(success=True)


def serve() -> None:
    """Start the gRPC server."""
    rechnung_service = RechnungService()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    rechnung_pb2_grpc.add_RechnungServiceServicer_to_server(rechnung_service, server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("gRPC server listening on localhost:50051")
    server.wait_for_termination()
