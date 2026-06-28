import sqlite3


class DatabaseHandler:
    """A simple database handler for managing rechnungen in a SQLite database."""

    DB_URL = "data/rechnungen.db"

    def __init__(self):
        """Initialize the database handler."""
        self._initialize_database()

    def insert_rechnung(
        self,
        rechnung: dict[str, str | float | int],
    ) -> int:
        """Insert a new rechnung into the database.

        :param rechnung: A dictionary containing the details of the rechnung to insert.
        :return: The ID of the inserted rechnung.
        """
        with sqlite3.connect(self.DB_URL) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO rechnungen (
                    rechnungsnummer,
                    ausstellungsdatum,
                    aussteller,
                    kundennummer,
                    zahlungsziel,
                    bemerkungen,
                    ist_bezahlt
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rechnung["rechnungsnummer"],
                    rechnung["ausstellungsdatum"],
                    rechnung["aussteller"],
                    rechnung["kundennummer"],
                    rechnung["zahlungsziel"],
                    rechnung["bemerkungen"],
                    rechnung["ist_bezahlt"],
                ),
            )
            conn.commit()
            if cursor.lastrowid is None:
                raise Exception("Failed to insert rechnung into the database.")
            return cursor.lastrowid

    def insert_rechnungsposition(
        self,
        rechnung_id: int,
        rechnungsposition: dict[str, str | float | int],
    ) -> int:
        """Insert a new rechnungsposition into the database.

        :param rechnung_id: The ID of the rechnung to which the position belongs.
        :param rechnungsposition: A dictionary containing the details of the rechnungsposition to insert.
        :return: The ID of the inserted rechnungsposition.
        """
        with sqlite3.connect(self.DB_URL) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO rechnungspositionen (
                    rechnung_id,
                    rechnungsposition,
                    beschreibung,
                    menge,
                    einheit,
                    einzelpreis
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    rechnung_id,
                    rechnungsposition["rechnungsposition"],
                    rechnungsposition["beschreibung"],
                    rechnungsposition["menge"],
                    rechnungsposition["einheit"],
                    rechnungsposition["einzelpreis"],
                ),
            )
            conn.commit()
            if cursor.lastrowid is None:
                raise Exception("Failed to insert rechnungsposition into the database.")
            return cursor.lastrowid

    def update_rechnung_as_paid(self, rechnung_id: int) -> None:
        """Update a rechnung in the database to mark it as paid.

        :param rechnung_id: The ID of the rechnung to update.
        """
        with sqlite3.connect(self.DB_URL) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE rechnungen
                SET ist_bezahlt = 1
                WHERE id = ?
                """,
                (rechnung_id,),
            )
            conn.commit()

    def _initialize_database(self):
        """Initialize the database by creating the rechnungen table if it does not exist."""
        with sqlite3.connect(self.DB_URL) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS rechnungen (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rechnungsnummer TEXT NOT NULL,
                    ausstellungsdatum TEXT NOT NULL,
                    aussteller TEXT NOT NULL,
                    kundennummer TEXT NOT NULL,
                    zahlungsziel TEXT NOT NULL,
                    bemerkungen TEXT NOT NULL,
                    ist_bezahlt INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS rechnungspositionen (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rechnung_id INTEGER NOT NULL,
                    rechnungsposition INTEGER NOT NULL DEFAULT 1,
                    beschreibung TEXT NOT NULL,
                    menge INTEGER NOT NULL DEFAULT 1,
                    einheit TEXT NOT NULL DEFAULT 'Stück',
                    einzelpreis REAL NOT NULL,
                    FOREIGN KEY (rechnung_id) REFERENCES rechnungen (id)
                )
                """
            )
            conn.commit()
