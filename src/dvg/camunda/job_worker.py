"""The CamundaJobWorker class provides a simple interface for creating and running a Camunda job worker."""

import asyncio
import uuid
from pathlib import Path

import grpc
import pika
import requests
from camunda_orchestration_sdk import (
    ActivatedJobResult,
    CamundaAsyncClient,
    ConnectedJobContext,
    WorkerConfig,
)
from dotenv import load_dotenv

from dvg.config import rechnung_pb2, rechnung_pb2_grpc


class CamundaJobWorker:
    """Small wrapper to configure and run a Camunda job worker."""

    GRPC_SERVER_ADDRESS = "localhost:50051"
    _patched_marker = "_dvg_patched_from_dict"

    def __init__(
        self,
        job_timeout_milliseconds: int = 30_000,
        env_path: Path | None = None,
    ) -> None:
        """Initialize the Camunda job worker.

        :param job_timeout_milliseconds: The timeout for each job in milliseconds.
        :param env_path: The path to the .env file containing Camunda client credentials.
        """
        self.job_timeout_milliseconds = job_timeout_milliseconds
        self.env_path = env_path or (
            Path(__file__).resolve().parents[3] / "CamundaClientCredentials.env"
        )
        load_dotenv(self.env_path)
        self._patch_activated_job_result()
        self.client = CamundaAsyncClient(
            configuration={
                "CAMUNDA_LOAD_ENVFILE": "true",
            }
        )

    @classmethod
    def _patch_activated_job_result(cls) -> None:
        """Patch the from_dict method of ActivatedJobResult to handle missing fields gracefully.

        :param cls: The class itself, used to check if the patch has already been applied.
        """
        if getattr(ActivatedJobResult.from_dict, cls._patched_marker, False):
            return
        original_from_dict = ActivatedJobResult.from_dict.__func__

        @classmethod
        def patched_from_dict(patched_cls, src_dict):
            """Patched from_dict method that adds default values for missing fields.

            :param patched_cls: The class for which the method is called.
            :param src_dict: The source dictionary to create the ActivatedJobResult from.
            :return: An instance of ActivatedJobResult created from the source dictionary.
            """
            data = dict(src_dict)
            data.setdefault("userTask", None)
            data.setdefault("rootProcessInstanceKey", None)
            return original_from_dict(patched_cls, data)

        setattr(patched_from_dict, cls._patched_marker, True)
        ActivatedJobResult.from_dict = patched_from_dict

    async def handle_register_invoice(
        self, job_context: ConnectedJobContext
    ) -> dict[str, object]:
        """Handle the RegisterInvoice job by creating a grpc request and store the metadata to a local db.

        :param job_context: The context of the job being handled, containing the job key and variables.
        :return: A dictionary indicating the completion of the job.
        """
        job_context.log.debug(f"Received job with id: {job_context.job_key}")
        variables = job_context.variables.to_dict()
        rechnungsnummer = f"R-${uuid.uuid4()}"
        kundennummer = f"K-${uuid.uuid4()}"
        job_context.log.debug(f"Job variables: {variables}")

        with grpc.insecure_channel(self.GRPC_SERVER_ADDRESS) as grpc_channel:
            stub = rechnung_pb2_grpc.RechnungServiceStub(grpc_channel)
            response = stub.CreateRechnung(
                rechnung_pb2.CreateRechnungRequest(
                    rechnungsnummer=rechnungsnummer,
                    ausstellungsdatum=variables["Ausstellungsdatum"],
                    aussteller=variables["Aussteller"],
                    kundennummer=kundennummer,
                    zahlungsziel=variables["Zahlungsziel"],
                    bemerkungen=variables["Bemerkungen"],
                )
            )
            rechnungspositionen = variables.get("Rechnungspositionen", [])
            if rechnungspositionen:
                for position in range(0, len(rechnungspositionen)):
                    try:
                        einheit = rechnungspositionen[position]["Einheit"]
                    except Exception as e:
                        einheit = "Stück"

                    stub.CreateRechnungsposition(
                        rechnung_pb2.CreateRechnungspositionRequest(
                            rechnung_id=response.id,
                            rechnungsposition=position + 1,
                            beschreibung=rechnungspositionen[position]["Beschreibung"],
                            menge=int(rechnungspositionen[position]["Menge"]),
                            einheit=einheit,
                            einzelpreis=float(
                                rechnungspositionen[position]["Einzelpreis"]
                            ),
                        )
                    )
        job_context.log.debug(
            f"Created rechnung with id {response.id} for job {job_context.job_key}"
        )

        variables.update(
            {
                "Rechnungsnummer": rechnungsnummer,
                "Kundennummer": kundennummer,
                "RechnungId": response.id,
            }
        )

        return {
            **variables,
            "done": True,
        }

    async def handle_execute_payment(
        self, job_context: ConnectedJobContext
    ) -> dict[str, object]:
        job_context.log.debug(f"Received job with id: {job_context.job_key}")
        variables = job_context.variables.to_dict()
        job_context.log.debug(f"Job variables: {variables}")

        pika_connection = pika.BlockingConnection(
            pika.ConnectionParameters("localhost"),
        )
        rabbit_mq_channel = pika_connection.channel()

        rabbit_mq_channel.queue_declare(
            queue="payment_queue",
            durable=True,
            arguments={"x-queue-type": "quorum"},
        )
        job_context.log.debug("Declared RabbitMQ queue: payment_queue")

        message = {
            "id": variables["RechnungId"],
        }
        job_context.log.debug(f"Prepared message for RabbitMQ: {message}")

        rabbit_mq_channel.basic_publish(
            exchange="",
            routing_key="payment_queue",
            body=str(message),
            properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent),
        )
        pika_connection.close()
        return {"done": True}

    async def handle_extract_data_n8n(
        self, job_context: ConnectedJobContext
    ) -> dict[str, object]:
        job_context.log.debug(f"Starte n8n Extraktion für Job: {job_context.job_key}")
        variables = job_context.variables.to_dict()

        n8n_url = "http://localhost:5678/webhook/c1688700-b19c-484f-83ef-190c38c651e2"

        attachments = variables.get("attachments", [])
        pdf_inhalt = attachments[0].get("content", "") if attachments else ""

        payload = {"prozessId": job_context.job_key, "pdf_base64": pdf_inhalt}

        try:
            requests.post(n8n_url, json=payload)
            job_context.log.debug("Daten erfolgreich an n8n gesendet.")
        except Exception as e:
            job_context.log.error(f"Fehler beim Senden an n8n: {e}")

        return {"done": True}

    async def run(self) -> None:
        """Run the Camunda job worker, listening for jobs and handling them asynchronously."""
        async with self.client as client:
            # Create the worker configs
            register_invoice_worker = WorkerConfig(
                job_type="RegisterInvoice",
                job_timeout_milliseconds=self.job_timeout_milliseconds,
            )
            execute_payment_worker = WorkerConfig(
                job_type="ExecutePayment",
                job_timeout_milliseconds=self.job_timeout_milliseconds,
            )
            extract_data_n8n_worker = WorkerConfig(
                job_type="ExtractDataWithN8n",
                job_timeout_milliseconds=self.job_timeout_milliseconds,
            )

            # Create the job worker and register the job handler
            client.create_job_worker(
                config=register_invoice_worker,
                callback=self.handle_register_invoice,
            )
            client.create_job_worker(
                config=execute_payment_worker,
                callback=self.handle_execute_payment,
            )
            client.create_job_worker(
                config=extract_data_n8n_worker,
                callback=self.handle_extract_data_n8n,
            )

            # Run the worker indefinitely
            await client.run_workers()


async def main() -> None:
    """Main function to create and run the Camunda job worker."""
    worker = CamundaJobWorker()
    await worker.run()


def run():
    """Run the job worker in an asynchone environment."""
    asyncio.run(main())
