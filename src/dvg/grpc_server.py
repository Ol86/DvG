import sqlite3
from concurrent import futures
from datetime import datetime

import grpc

from . import rechnung_pb2, rechnung_pb2_grpc


class RechnungService(rechnung_pb2_grpc.RechnungServiceServicer):
    def CreateRechnung(
        self,
        request: rechnung_pb2.RechnungCreateRequest,
        context: grpc.ServicerContext,
    ) -> rechnung_pb2.RechnungCreateResponse:
        id = _create_rechnung(request.aussteller, request.empfaenger, request.betrag)
        return rechnung_pb2.RechnungCreateResponse(id=id)

    def GetRechnungById(
        self,
        request: rechnung_pb2.RechnungIdRequest,
        context: grpc.ServicerContext,
    ) -> rechnung_pb2.RechnungIdResponse:
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
        _update_rechnung(request.id, True)
        return rechnung_pb2.RechnungPaiedResponse(success=True)


def serve() -> None:
    _init_db()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    rechnung_pb2_grpc.add_RechnungServiceServicer_to_server(RechnungService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("gRPC server listening on localhost:50051")
    server.wait_for_termination()


def _init_db() -> None:
    conn = sqlite3.connect("data/rechnungen.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS rechnungen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aussteller TEXT NOT NULL,
            empfaenger TEXT NOT NULL,
            betrag REAL NOT NULL,
            ist_bezahlt BOOLEAN NOT NULL DEFAULT 0,
            ausstellungsdatum DATE NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def _create_rechnung(aussteller: str, empfaenger: str, betrag: float) -> int | None:
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    db = cursor.execute(
        "INSERT INTO rechnungen (aussteller, empfaenger, betrag, ausstellungsdatum) VALUES (?, ?, ?, ?)",
        (aussteller, empfaenger, betrag, datetime.now().date()),
    )
    conn.commit()
    conn.close()
    return db.lastrowid


def _get_rechnung_by_id(rechnung_id: int) -> dict:
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rechnungen WHERE id = ?", (rechnung_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "aussteller": row[1],
            "empfaenger": row[2],
            "betrag": row[3],
            "ausstellungsdatum": row[4],
            "ist_bezahlt": bool(row[5]),
        }
    return {}


def _get_all_rechnungen() -> list:
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rechnungen")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": row[0],
            "aussteller": row[1],
            "empfaenger": row[2],
            "betrag": row[3],
            "ausstellungsdatum": row[4],
            "ist_bezahlt": bool(row[5]),
        }
        for row in rows
    ]


def _update_rechnung(rechnung_id: int, ist_bezahlt: bool) -> None:
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE rechnungen SET ist_bezahlt = ? WHERE id = ?",
        (int(ist_bezahlt), rechnung_id),
    )
    conn.commit()
    conn.close()
