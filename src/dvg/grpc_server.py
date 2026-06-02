import sqlite3
from concurrent import futures
from datetime import datetime

import grpc

from dvg.config import rechnung_pb2, rechnung_pb2_grpc

DB_URL = "data/rechnungen.db"
"""The URL of the SQLite database for storing rechnungen."""


class RechnungService(rechnung_pb2_grpc.RechnungServiceServicer):
    """gRPC service for managing rechnungen."""

    def CreateRechnung(
        self,
        request: rechnung_pb2.RechnungCreateRequest,
        context: grpc.ServicerContext,
    ) -> rechnung_pb2.RechnungCreateResponse:
        """Create a new rechnung.

        :param request: The gRPC request containing the rechnung details.
        :param context: The gRPC context for handling the request.
        :return: A gRPC response containing the ID of the created rechnung.
        """
        id = _create_rechnung(
            request.rechnungsnummer,
            request.aussteller,
            request.kundennummer,
            request.empfaenger,
            request.betrag,
        )
        return rechnung_pb2.RechnungCreateResponse(id=id)

    def GetRechnungById(
        self,
        request: rechnung_pb2.RechnungIdRequest,
        context: grpc.ServicerContext,
    ) -> rechnung_pb2.RechnungIdResponse:
        """Get a rechnung by its ID.

        :param request: The gRPC request containing the ID of the rechnung to retrieve.
        :param context: The gRPC context for handling the request.
        :return: A gRPC response containing the details of the requested rechnung, or an error if the rechnung is not found.
        """
        rechnung = _get_rechnung_by_id(request.id)
        if not rechnung:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Rechnung not found")
            return rechnung_pb2.RechnungIdResponse()
        return rechnung_pb2.RechnungIdResponse(
            aussteller=rechnung["aussteller"],
            empfaenger=rechnung["empfaenger"],
            betrag=rechnung["betrag"],
            ausstellungsdatum=str(rechnung["ausstellungsdatum"]),
            ist_bezahlt=rechnung["ist_bezahlt"],
        )

    def MarkRechnungAsPaid(
        self,
        request: rechnung_pb2.RechnungPaiedRequest,
        context: grpc.ServicerContext,
    ) -> rechnung_pb2.RechnungPaiedResponse:
        """Mark a rechnung as paid.

        :param request: The gRPC request containing the ID of the rechnung to mark as paid.
        :param context: The gRPC context for handling the request.
        :return: A gRPC response indicating the success of the operation.
        """
        _update_rechnung(request.id, True)
        return rechnung_pb2.RechnungPaiedResponse(success=True)


def serve() -> None:
    """Start the gRPC server."""
    _init_db()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    rechnung_pb2_grpc.add_RechnungServiceServicer_to_server(RechnungService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("gRPC server listening on localhost:50051")
    server.wait_for_termination()


def _init_db() -> None:
    """Initialize the SQLite database and create the rechnungen table if it doesn't exist."""
    conn = sqlite3.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS rechnungen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rechnungsnummer TEXT NOT NULL,
            aussteller TEXT NOT NULL,
            kundennummer TEXT NOT NULL,
            empfaenger TEXT NOT NULL,
            betrag REAL NOT NULL,
            ist_bezahlt BOOLEAN NOT NULL DEFAULT 0,
            ausstellungsdatum DATE NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def _create_rechnung(
    rechnungsnummer: str,
    aussteller: str,
    kundenummer: str,
    empfaenger: str,
    betrag: float,
) -> int | None:
    """Create a new rechnung in the database.

    :param aussteller: The name of the person or company issuing the invoice.
    :param empfaenger: The name of the person or company receiving the invoice.
    :param betrag: The amount of the invoice.
    :return: The ID of the created rechnung, or None if creation failed.
    """
    conn = sqlite3.connect(DB_URL)
    cursor = conn.cursor()
    db = cursor.execute(
        "INSERT INTO rechnungen (rechnungsnummer, aussteller, kundennummer, empfaenger, betrag, ausstellungsdatum) VALUES (?, ?, ?, ?, ?, ?)",
        (
            rechnungsnummer,
            aussteller,
            kundenummer,
            empfaenger,
            betrag,
            datetime.now().date(),
        ),
    )
    conn.commit()
    conn.close()
    return db.lastrowid


def _get_rechnung_by_id(rechnung_id: int) -> dict:
    """Get a rechnung from the database by its ID.

    :param rechnung_id: The ID of the rechnung to retrieve.
    :return: A dictionary containing the details of the requested rechnung, or an empty dictionary if not found.
    """
    conn = sqlite3.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rechnungen WHERE id = ?", (rechnung_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "rechnungsnummer": row[1],
            "aussteller": row[2],
            "kundennummer": row[3],
            "empfaenger": row[4],
            "betrag": row[5],
            "ausstellungsdatum": row[6],
            "ist_bezahlt": bool(row[7]),
        }
    return {}


def _get_all_rechnungen() -> list:
    """Get all rechnungen from the database."""
    conn = sqlite3.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rechnungen")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": row[0],
            "rechnungsnummer": row[1],
            "aussteller": row[2],
            "kundennummer": row[3],
            "empfaenger": row[4],
            "betrag": row[5],
            "ausstellungsdatum": row[6],
            "ist_bezahlt": bool(row[7]),
        }
        for row in rows
    ]


def _update_rechnung(rechnung_id: int, ist_bezahlt: bool) -> None:
    """Update the payment status of a rechnung in the database.

    :param rechnung_id: The ID of the rechnung to update.
    :param ist_bezahlt: The new payment status of the rechnung.
    """
    conn = sqlite3.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE rechnungen SET ist_bezahlt = ? WHERE id = ?",
        (int(ist_bezahlt), rechnung_id),
    )
    conn.commit()
    conn.close()
