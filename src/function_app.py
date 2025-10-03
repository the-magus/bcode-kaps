"""Azure Function entry point for the barcode generator workflow.

This module provides composable helpers for parsing purchase order emails,
generating barcode assets, bundling them, emailing the supplier, and logging
completion details to Azure Blob Storage. The Azure Function handler orchestrates
the workflow while keeping side effects isolated for testability.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Set

import logging
import os
import smtplib
import tempfile
import zipfile

import azure.functions as func
from azure.storage.blob import BlobServiceClient
from bs4 import BeautifulSoup
import barcode
from barcode.writer import ImageWriter
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Variant:
	"""Represents a single variant row parsed from the WMS email."""

	po_number: str
	item_code: str
	description: str


def parse_html_email(html_content: str) -> List[Variant]:
	"""Parse the HTML body of the WMS email.

	Args:
		html_content: Raw HTML string sent by the WMS.

	Returns:
		A list of :class:`Variant` entries. An empty list indicates no
		purchasable variants were found (e.g., a non-PO email).

	Raises:
		ValueError: If candidate rows exist but are malformed.
	"""

	if not html_content:
		return []

	soup = BeautifulSoup(html_content, "html.parser")
	variants: List[Variant] = []
	malformed_detected = False

	for cell in soup.find_all("td"):
		text = cell.get_text(strip=True)
		# Only process cells that contain both 'PO:' and 'Item:' (case-sensitive)
		if "PO:" in text and "Item:" in text:
			segments = [segment.strip() for segment in text.split("|")]
			if len(segments) != 3:
				malformed_detected = True
				continue

			try:
				po_number = segments[0].split(":", 1)[1].strip()
				item_code = segments[1].split(":", 1)[1].strip()
				description = segments[2].split(":", 1)[1].strip()
			except IndexError:
				malformed_detected = True
				continue

			variants.append(Variant(po_number, item_code, description))

	if not variants and malformed_detected:
		raise ValueError("Email body did not contain well-formed purchase order rows.")

	return variants


def generate_barcode_image(item_code: str, output_dir: Optional[Path] = None) -> Path:
	"""Generate a Code128 barcode image for a variant.

	Args:
		item_code: SKU for which to create the barcode.
		output_dir: Directory where the file should be written. Defaults to the
			system temporary directory.

	Returns:
		Path to the generated PNG file.
	"""

	target_dir = Path(output_dir or tempfile.gettempdir())
	target_dir.mkdir(parents=True, exist_ok=True)

	code128 = barcode.get_barcode_class("code128")
	barcode_image = code128(item_code, writer=ImageWriter())
	saved_path = Path(barcode_image.save(str(target_dir / item_code)))
	return saved_path if saved_path.suffix else saved_path.with_suffix(".png")


def bundle_barcodes(
	po_number: str,
	barcode_paths: Iterable[Path],
	output_dir: Optional[Path] = None,
) -> Path:
	"""Bundle generated barcode files into a per-PO zip archive."""

	target_dir = Path(output_dir or tempfile.gettempdir())
	target_dir.mkdir(parents=True, exist_ok=True)
	zip_path = target_dir / f"{po_number}.zip"

	with zipfile.ZipFile(zip_path, "w") as archive:
		for path in barcode_paths:
			archive.write(path, arcname=Path(path).name)

	return zip_path


def build_email_subject(po_number: str) -> str:
	"""Return the subject line used when emailing barcodes to Kaps."""

	return f"Barcodes for PO {po_number}"


def send_email_with_attachment(
	*,
	sender_email: str,
	receiver_email: str,
	subject: str,
	body: str,
	attachment_path: Optional[Path],
	smtp_host: Optional[str] = None,
	smtp_port: Optional[int] = None,
) -> None:
	"""Send an email, optionally attaching the provided file."""

	smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.test.com")
	smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))

	message = MIMEMultipart()
	message["From"] = sender_email
	message["To"] = receiver_email
	message["Subject"] = subject
	message.attach(MIMEText(body, "plain"))

	if attachment_path is not None:
		with open(attachment_path, "rb") as attachment:
			part = MIMEBase("application", "octet-stream")
			part.set_payload(attachment.read())
		encoders.encode_base64(part)
		part.add_header(
			"Content-Disposition",
			f"attachment; filename={Path(attachment_path).name}",
		)
		message.attach(part)

	with smtplib.SMTP(smtp_host, smtp_port) as server:
		server.sendmail(sender_email, [receiver_email], message.as_string())


def verify_sender(actual_sender: Optional[str], expected_sender: Optional[str]) -> None:
	"""Ensure the inbound request originated from the configured WMS address."""

	if not expected_sender:
		raise PermissionError("Expected WMS sender email is not configured.")
	if actual_sender != expected_sender:
		raise PermissionError("Unauthorized sender.")


def handle_malformed_email(
	*,
	error: Exception,
	admin_email: Optional[str],
	notify_admin: Callable[[str, str, str], None],
) -> None:
	"""Log and escalate malformed purchase order emails."""

	LOGGER.error("Malformed purchase order email: %s", error)
	if admin_email:
		notify_admin(
			admin_email,
			subject="Malformed purchase order email",
			body=str(error),
		)



def _ensure_blob_service(blob_service: Optional[BlobServiceClient]) -> BlobServiceClient:
	if blob_service is not None:
		return blob_service

	connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
	if not connection_string:
		raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is not configured.")
	return BlobServiceClient.from_connection_string(connection_string)


def fetch_processed_purchase_orders(
	*,
	blob_service: Optional[BlobServiceClient] = None,
	container_name: str = "completed-purchase-orders",
	blob_name: str = "processed_pos.log",
) -> Set[str]:
	"""Return the set of purchase orders that have already been processed."""

	blob_service = _ensure_blob_service(blob_service)
	blob_client = blob_service.get_blob_client(container=container_name, blob=blob_name)

	try:
		contents = blob_client.download_blob().readall().decode("utf-8")
	except Exception:
		return set()

	return {line.strip() for line in contents.splitlines() if line.strip()}


def persist_processed_purchase_orders(
	*,
	processed_orders: Set[str],
	blob_service: Optional[BlobServiceClient] = None,
	container_name: str = "completed-purchase-orders",
	blob_name: str = "processed_pos.log",
) -> None:
	"""Write the canonical list of processed purchase orders to Blob Storage."""

	blob_service = _ensure_blob_service(blob_service)
	blob_client = blob_service.get_blob_client(container=container_name, blob=blob_name)

	data = "\n".join(sorted(processed_orders)) + "\n"
	blob_client.upload_blob(data.encode("utf-8"), overwrite=True)


def build_email_body(po_number: str) -> str:
	"""Construct the body of the email sent to Kaps."""

	return f"Please find attached the barcodes for purchase order {po_number}."


def _resolve_recipient(env: dict[str, str]) -> str:
	"""Determine who should receive outbound purchase order emails."""

	verification_mode = os.getenv("EMAIL_VERIFICATION_MODE", "true").strip().lower()
	if verification_mode in {"false", "0", "no", "off"}:
		return env["KAPS_EMAIL"]

	recipient = env["ADMIN_EMAIL"]
	LOGGER.info(
		"Email verification mode active; routing purchase order message to admin %s",
		recipient,
	)
	return recipient


def notify_admin_email(*, admin_email: str, sender_email: str, subject: str, body: str) -> None:
	"""Notify the administrator about an error processing a purchase order."""

	if not admin_email:
		LOGGER.warning("Admin email not configured; skipping notification.")
		return

	send_email_with_attachment(
		sender_email=sender_email,
		receiver_email=admin_email,
		subject=subject,
		body=body,
		attachment_path=None,
	)


def _cleanup_temp_directory(path: Path) -> None:
	"""Best-effort removal of temporary assets."""

	for child in path.glob("*"):
		try:
			child.unlink()
		except OSError:
			LOGGER.debug("Unable to delete temporary file %s", child, exc_info=True)
	try:
		path.rmdir()
	except OSError:
		LOGGER.debug("Unable to delete temporary directory %s", path, exc_info=True)


def _load_required_env() -> dict[str, str]:
	"""Retrieve required environment variables, raising if any are missing."""

	required_keys = ["WMS_SENDER_EMAIL", "SENDER_EMAIL", "KAPS_EMAIL", "ADMIN_EMAIL"]
	values = {}
	missing = []
	for key in required_keys:
		value = os.getenv(key)
		if value:
			values[key] = value
		else:
			missing.append(key)
	if missing:
		raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
	return values


def process_email(
	*,
	email_body: str,
	sender: Optional[str],
	notify_admin: Callable[[str, str, str], None],
	blob_service: Optional[BlobServiceClient] = None,
) -> str:
	"""Core orchestration for processing a WMS email."""

	env = _load_required_env()

	verify_sender(sender, env["WMS_SENDER_EMAIL"])

	try:
		variants = parse_html_email(email_body)
	except ValueError as error:
		handle_malformed_email(
			error=error,
			admin_email=env["ADMIN_EMAIL"],
			notify_admin=notify_admin,
		)
		raise

	if not variants:
		LOGGER.info("Email did not contain any purchase order variants; nothing to do.")
		return "No variants found."

	po_number = variants[0].po_number
	processed_orders = fetch_processed_purchase_orders(blob_service=blob_service)
	if po_number in processed_orders:
		LOGGER.info("Purchase order %s already processed; skipping.", po_number)
		return f"PO {po_number} was already processed."

	temp_dir = Path(tempfile.mkdtemp(prefix="barcode_generator_"))
	try:
		barcode_paths = [
			generate_barcode_image(variant.item_code, output_dir=temp_dir)
			for variant in variants
		]
		zip_path = bundle_barcodes(po_number, barcode_paths, output_dir=temp_dir)
		subject = build_email_subject(po_number)
		body = build_email_body(po_number)
		receiver_email = _resolve_recipient(env)
		send_email_with_attachment(
			sender_email=env["SENDER_EMAIL"],
			receiver_email=receiver_email,
			subject=subject,
			body=body,
			attachment_path=zip_path,
		)
		processed_orders.add(po_number)
		persist_processed_purchase_orders(
			processed_orders=processed_orders,
			blob_service=blob_service,
		)
	finally:
		_cleanup_temp_directory(temp_dir)

	return f"Successfully processed PO {po_number}."


app = func.FunctionApp()


@app.route(route="barcode_generator")
def main(req: func.HttpRequest) -> func.HttpResponse:
	"""HTTP-triggered Azure Function entry point."""

	email_body = req.get_body().decode("utf-8")
	sender = req.headers.get("X-Forwarded-For") or req.headers.get("X-Sender")

	env = _load_required_env()

	def _notify(admin_email: str, subject: str, body: str) -> None:
		notify_admin_email(
			admin_email=admin_email,
			sender_email=env["SENDER_EMAIL"],
			subject=subject,
			body=body,
		)

	try:
		message = process_email(
			email_body=email_body,
			sender=sender,
			notify_admin=_notify,
		)
		status_code = 200
	except PermissionError as error:
		LOGGER.warning("Unauthorized sender attempted access: %s", sender)
		return func.HttpResponse(str(error), status_code=401)
	except ValueError as error:
		return func.HttpResponse(str(error), status_code=400)
	except RuntimeError as error:
		LOGGER.error("Configuration error: %s", error)
		return func.HttpResponse(str(error), status_code=500)
	except Exception as error:  # noqa: BLE001
		LOGGER.exception("Unexpected error processing purchase order email")
		handle_malformed_email(
			error=error,
			admin_email=env["ADMIN_EMAIL"],
			notify_admin=_notify,
		)
		return func.HttpResponse("Error processing email.", status_code=500)

	return func.HttpResponse(message, status_code=status_code)
