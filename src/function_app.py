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
from typing import Callable, Iterable, List, Mapping, Optional, Set

import logging
import os
import smtplib
import ssl
import tempfile
import zipfile

import azure.functions as func
from azure.storage.blob import BlobServiceClient
from bs4 import BeautifulSoup
import qrcode
from PIL import Image, ImageDraw, ImageFont
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

	for cell in soup.find_all(
		"td",
		style="font-family:Arial; font-size:14px; color:gray; padding-top:10px;",
	):
		text = cell.get_text(strip=True)
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


def _resolve_font_file(filename: str) -> Path:
	"""Return the first existing path for ``filename`` across known locations."""

	candidates = [
		Path(__file__).resolve().parent / filename,
		Path(__file__).resolve().parent / "fonts" / filename,
		Path(__file__).resolve().parent.parent / filename,
	]

	for candidate in candidates:
		if candidate.exists():
			return candidate

	raise FileNotFoundError(
		f"Required font file '{filename}' not found. Ensure it is bundled with the function deployment."
	)


def _wrap_text(words: List[str], font: ImageFont.ImageFont, max_width: int) -> str:
	"""Return wrapped text that fits within ``max_width`` pixels for the font."""

	lines: List[str] = []
	current_line: List[str] = []

	for word in words:
		candidate = " ".join(current_line + [word])
		if font.getlength(candidate) <= max_width:
			current_line.append(word)
		else:
			if current_line:
				lines.append(" ".join(current_line))
			current_line = [word]

	if current_line:
		lines.append(" ".join(current_line))

	return "\n".join(lines)


def generate_barcode_image(
	item_code: str,
	description: str,
	output_dir: Optional[Path] = None,
) -> Path:
	"""Generate a legacy-formatted QR label image for a purchase-order line.

	The layout matches the historical on-premise tooling:

	* 70mm x 30mm canvas rendered at 300 DPI (826 x 354 pixels)
	* Variant code rendered in Arial Bold above wrapped description text
	* QR code positioned on the right-hand side with 40px padding

	Args:
		item_code: SKU for which to create the barcode.
		description: Human-readable description printed beneath the code.
		output_dir: Directory where the file should be written. Defaults to the
			system temporary directory.

	Returns:
		Path to the generated PNG file.
	"""

	target_dir = Path(output_dir or tempfile.gettempdir())
	target_dir.mkdir(parents=True, exist_ok=True)

	main_font_path = _resolve_font_file("arial.ttf")
	bold_font_path = _resolve_font_file("arialbd.ttf")

	# Create QR code matching the historical configuration.
	qr = qrcode.QRCode(
		version=1,
		error_correction=qrcode.constants.ERROR_CORRECT_L,
		box_size=10,
		border=4,
	)
	qr.add_data(item_code)
	qr.make(fit=True)
	qr_image = qr.make_image(fill_color="black", back_color="white").convert("RGB")

	# Canvas dimensions at 300 DPI for 70mm x 30mm labels.
	dpi = 300
	canvas_width = int(70 * 0.0393701 * dpi)
	canvas_height = int(30 * 0.0393701 * dpi)
	label = Image.new("RGB", (canvas_width, canvas_height), "white")

	# Resize QR image to match legacy layout.
	qr_target_width = 150
	aspect_ratio = qr_image.height / qr_image.width
	qr_target_height = int(qr_target_width * aspect_ratio)
	qr_image = qr_image.resize((qr_target_width, qr_target_height))
	QR_IMAGE_PADDING_X = 40
	QR_IMAGE_PADDING_Y = 40
	label.paste(qr_image, (canvas_width - qr_target_width - QR_IMAGE_PADDING_X, QR_IMAGE_PADDING_Y))

	draw = ImageDraw.Draw(label)
	main_font = ImageFont.truetype(str(main_font_path), 45)
	bold_font = ImageFont.truetype(str(bold_font_path), 100)

	draw.text((30, 30), item_code, font=bold_font, fill=(0, 0, 0))
	wrapped_description = _wrap_text(description.split(), main_font, (label.width // 2) + 200)
	draw.text((30, 160), wrapped_description, font=main_font, fill=(0, 0, 0))

	safe_name = "".join(char for char in item_code if char.isalnum()) or "barcode"
	image_path = target_dir / f"{safe_name}.png"
	label.save(image_path)
	return image_path


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
	"""Send an email, optionally attaching the provided file.

	If ``SMTP_USERNAME`` and ``SMTP_PASSWORD`` environment variables are present the
	connection upgrades to TLS and authenticates with those credentials before
	sending the message. This enables compatibility with providers such as Gmail
	that require STARTTLS + login on port 587.
	"""

	smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.test.com")
	smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
	smtp_username = os.getenv("SMTP_USERNAME")
	smtp_password = os.getenv("SMTP_PASSWORD")
	LOGGER.info(
		"SMTP configuration env overrides host=%s port=%s",
		os.getenv("SMTP_HOST"),
		os.getenv("SMTP_PORT"),
	)

	if smtp_username and not smtp_password:
		raise RuntimeError("SMTP_PASSWORD must be set when SMTP_USERNAME is provided.")
	if smtp_password and not smtp_username:
		raise RuntimeError("SMTP_USERNAME must be set when SMTP_PASSWORD is provided.")

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

	context = ssl.create_default_context()
	LOGGER.info("Connecting to SMTP host %s:%s", smtp_host, smtp_port)
	with smtplib.SMTP(smtp_host, smtp_port) as server:
		server.ehlo()
		try:
			server.starttls(context=context)
		except smtplib.SMTPNotSupportedError:
			LOGGER.warning("SMTP server %s:%s does not support STARTTLS", smtp_host, smtp_port)
		else:
			server.ehlo()
		if smtp_username and smtp_password:
			server.login(smtp_username, smtp_password)
		server.sendmail(sender_email, [receiver_email], message.as_string())


def _extract_sender(headers: Mapping[str, str]) -> Optional[str]:
	"""Resolve the WMS sender email from HTTP headers.

	The Logic App sets either ``X-Sender`` or ``X-Forwarded-For``. Azure also injects
	client IPs into ``X-Forwarded-For`` which means the header can contain multiple
	comma-separated values. This helper normalizes that into the first entry that
	looks like an email address.
	"""

	for header_name in ("X-Sender", "X-Forwarded-For"):
		raw_value = headers.get(header_name)
		if not raw_value:
			continue
		for candidate in (value.strip() for value in raw_value.split(",")):
			if "@" in candidate:
				return candidate

	return None


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
			generate_barcode_image(
				variant.item_code,
				variant.description,
				output_dir=temp_dir,
			)
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


@app.function_name(name="barcode_generator")
@app.route(route="barcode_generator")
def main(req: func.HttpRequest) -> func.HttpResponse:
	"""HTTP-triggered Azure Function entry point."""

	email_body = req.get_body().decode("utf-8")
	sender = _extract_sender(req.headers)

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
