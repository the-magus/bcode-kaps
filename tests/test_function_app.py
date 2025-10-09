from pathlib import Path
import zipfile
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from src.function_app import (
    Variant,
    _extract_sender,
    bundle_barcodes,
    build_email_subject,
    generate_barcode_image,
    handle_malformed_email,
    fetch_processed_purchase_orders,
    persist_processed_purchase_orders,
    process_email,
    parse_html_email,
    send_email_with_attachment,
    verify_sender,
)


SAMPLE_HTML = """
<html>
  <body>
    <table>
      <tr>
        <td style="font-family:Arial; font-size:14px; color:gray; padding-top:10px;">
          PO: UPD-PO27652 | Item: V109327 | Desc: Children must not play on this site 200mm x 300mm - 1mm Rigid Plastic Sign
        </td>
      </tr>
      <tr>
        <td style="font-family:Arial; font-size:14px; color:gray; padding-top:10px;">
          PO: UPD-PO27652 | Item: V109328 | Desc: Fire exit 150mm x 150mm - Self Adhesive Vinyl
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def _make_blob_service(existing: str = ""):
    blob_service = MagicMock()
    blob_client = MagicMock()
    blob_service.get_blob_client.return_value = blob_client

    download_blob = MagicMock()
    download_blob.readall.return_value = existing.encode()
    blob_client.download_blob.return_value = download_blob

    return blob_service, blob_client


def test_parse_html_email_returns_variants():
    variants = parse_html_email(SAMPLE_HTML)

    assert variants == [
        Variant(
            po_number="UPD-PO27652",
            item_code="V109327",
            description="Children must not play on this site 200mm x 300mm - 1mm Rigid Plastic Sign",
        ),
        Variant(
            po_number="UPD-PO27652",
            item_code="V109328",
            description="Fire exit 150mm x 150mm - Self Adhesive Vinyl",
        ),
    ]


def test_po_number_used_for_zipfile_and_subject(tmp_path: Path):
    variants = parse_html_email(SAMPLE_HTML)
    po_number = variants[0].po_number

    barcode_dir = tmp_path / "barcodes"
    barcode_dir.mkdir()
    files = []
    for index, variant in enumerate(variants):
        file_path = barcode_dir / f"{variant.item_code}_{index}.png"
        file_path.write_bytes(b"fake-barcode")
        files.append(file_path)

    zip_path = bundle_barcodes(po_number, files, output_dir=tmp_path)

    assert zip_path.name == f"{po_number}.zip"
    assert build_email_subject(po_number) == f"Barcodes for PO {po_number}"


def test_bundle_barcodes_contains_all_files(tmp_path: Path):
    po_number = "UPD-PO27652"
    barcodes = []
    for suffix in ("A", "B"):
        path = tmp_path / f"barcode_{suffix}.png"
        path.write_bytes(suffix.encode())
        barcodes.append(path)

    zip_path = bundle_barcodes(po_number, barcodes, output_dir=tmp_path)

    with zipfile.ZipFile(zip_path, "r") as archive:
        assert set(archive.namelist()) == {path.name for path in barcodes}


def test_generate_barcode_image_creates_file(tmp_path: Path):
    barcode_path = generate_barcode_image(
        "V109327",
        "Sample description for layout validation",
        output_dir=tmp_path,
    )

    assert barcode_path.exists()
    assert barcode_path.parent == tmp_path

    with Image.open(barcode_path) as image:
        assert image.size == (826, 354)


def test_send_email_with_attachment_uses_zip(tmp_path: Path):
    attachment = tmp_path / "test.zip"
    attachment.write_bytes(b"zip-bytes")

    with patch("src.function_app.smtplib.SMTP") as smtp_mock:
        send_email_with_attachment(
            sender_email="sender@example.com",
            receiver_email="kaps@example.com",
            subject="Barcodes for PO 123",
            body="Body",
            attachment_path=attachment,
            smtp_host="smtp.test.com",
            smtp_port=587,
        )

        smtp_mock.assert_called_once_with("smtp.test.com", 587)
        server = smtp_mock.return_value.__enter__.return_value
        server.starttls.assert_called_once()
        server.login.assert_not_called()
        args, kwargs = server.sendmail.call_args
        assert args[0] == "sender@example.com"
        assert args[1] == ["kaps@example.com"]
        assert "Barcodes for PO 123" in args[2]
        assert "test.zip" in args[2]
        assert kwargs == {}


def test_send_email_with_attachment_logins_when_credentials_present(monkeypatch, tmp_path: Path):
    attachment = tmp_path / "test.zip"
    attachment.write_bytes(b"zip-bytes")

    monkeypatch.setenv("SMTP_USERNAME", "smtp-user")
    monkeypatch.setenv("SMTP_PASSWORD", "smtp-pass")

    with patch("src.function_app.smtplib.SMTP") as smtp_mock:
        send_email_with_attachment(
            sender_email="sender@example.com",
            receiver_email="kaps@example.com",
            subject="Barcodes for PO 123",
            body="Body",
            attachment_path=attachment,
            smtp_host="smtp.gmail.com",
            smtp_port=587,
        )

        server = smtp_mock.return_value.__enter__.return_value
        server.login.assert_called_once_with("smtp-user", "smtp-pass")


def test_verify_sender_accepts_authorized_address():
    verify_sender("wms@example.com", "wms@example.com")


def test_verify_sender_rejects_unexpected_address():
    with pytest.raises(PermissionError):
        verify_sender("intruder@example.com", "wms@example.com")


def test_extract_sender_prefers_explicit_header():
    headers = {"X-Sender": "wms@example.com", "X-Forwarded-For": "10.0.0.1"}

    assert _extract_sender(headers) == "wms@example.com"


def test_extract_sender_is_case_insensitive():
	headers = {"x-sender": "donotreply@example.com"}

	assert _extract_sender(headers) == "donotreply@example.com"


def test_extract_sender_handles_forwarded_for_with_ips():
    headers = {"X-Forwarded-For": "203.0.113.4, donotreply@example.com, 10.0.0.1"}

    assert _extract_sender(headers) == "donotreply@example.com"


def test_extract_sender_skips_forwarded_for_when_no_email():
	headers = {"X-Forwarded-For": "203.0.113.4, 10.0.0.1"}

	assert _extract_sender(headers) is None


def test_extract_sender_returns_none_when_missing():
    assert _extract_sender({}) is None


def test_handle_malformed_email_logs_and_notifies(caplog):
    notifier = MagicMock()

    with caplog.at_level("ERROR"):
        handle_malformed_email(
            error=ValueError("Unparseable email"),
            admin_email="admin@example.com",
            notify_admin=notifier,
        )

    notifier.assert_called_once()
    called_args, called_kwargs = notifier.call_args
    assert called_args[0] == "admin@example.com"
    assert "Malformed purchase order email" in called_kwargs["subject"]
    assert "Unparseable email" in called_kwargs["body"]
    assert "Unparseable email" in caplog.text


def test_fetch_processed_purchase_orders_returns_set():
    blob_service = MagicMock()
    blob_client = blob_service.get_blob_client.return_value

    download_blob = MagicMock()
    download_blob.readall.return_value = b"UPD-PO123\nUPD-PO456\n"
    blob_client.download_blob.return_value = download_blob

    processed = fetch_processed_purchase_orders(
        blob_service=blob_service,
        container_name="completed-purchase-orders",
        blob_name="processed_pos.log",
    )

    blob_service.get_blob_client.assert_called_once_with(
        container="completed-purchase-orders",
        blob="processed_pos.log",
    )
    assert processed == {"UPD-PO123", "UPD-PO456"}


def test_persist_processed_purchase_orders_writes_sorted_lines():
    blob_service = MagicMock()
    blob_client = blob_service.get_blob_client.return_value

    persist_processed_purchase_orders(
        processed_orders={"UPD-PO222", "UPD-PO111"},
        blob_service=blob_service,
        container_name="completed-purchase-orders",
        blob_name="processed_pos.log",
    )

    blob_service.get_blob_client.assert_called_once_with(
        container="completed-purchase-orders",
        blob="processed_pos.log",
    )
    upload_args, upload_kwargs = blob_client.upload_blob.call_args
    assert upload_args[0] == b"UPD-PO111\nUPD-PO222\n"
    assert upload_kwargs == {"overwrite": True}


def test_persist_processed_purchase_orders_appends_to_existing(tmp_path: Path):
    blob_service = MagicMock()
    blob_client = blob_service.get_blob_client.return_value

    download_blob = MagicMock()
    download_blob.readall.return_value = b"existing\n"
    blob_client.download_blob.return_value = download_blob

    existing = fetch_processed_purchase_orders(
        blob_service=blob_service,
        container_name="completed-purchase-orders",
        blob_name="processed_pos.log",
    )

    persist_processed_purchase_orders(
        processed_orders=existing | {"UPD-PO27652"},
        blob_service=blob_service,
        container_name="completed-purchase-orders",
        blob_name="processed_pos.log",
    )

    assert blob_client.upload_blob.call_count == 1


def test_process_email_routes_messages_to_admin(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("WMS_SENDER_EMAIL", "wms@example.com")
    monkeypatch.setenv("SENDER_EMAIL", "noreply@example.com")
    monkeypatch.setenv("KAPS_EMAIL", "kaps@example.com")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.delenv("EMAIL_VERIFICATION_MODE", raising=False)

    working_dir = tmp_path / "work"
    working_dir.mkdir()
    monkeypatch.setattr("src.function_app.tempfile.mkdtemp", lambda prefix=None: str(working_dir))

    def fake_generate(item_code: str, description: str, output_dir: Path) -> Path:
        path = Path(output_dir) / f"{item_code}.png"
        path.write_bytes(b"barcode")
        return path

    def fake_bundle(po_number: str, barcode_paths, output_dir: Path | None = None) -> Path:
        path = Path(output_dir or working_dir) / f"{po_number}.zip"
        path.write_bytes(b"zip")
        return path

    with (
        patch("src.function_app.generate_barcode_image", side_effect=fake_generate),
        patch("src.function_app.bundle_barcodes", side_effect=fake_bundle),
        patch("src.function_app.send_email_with_attachment") as send_email_mock,
    ):
        blob_service, blob_client = _make_blob_service()
        message = process_email(
            email_body=SAMPLE_HTML,
            sender="wms@example.com",
            notify_admin=lambda *_args, **_kwargs: None,
            blob_service=blob_service,
        )

    assert message == "Successfully processed PO UPD-PO27652."
    send_email_mock.assert_called_once()
    kwargs = send_email_mock.call_args.kwargs
    assert kwargs["receiver_email"] == "admin@example.com"
    assert kwargs["sender_email"] == "noreply@example.com"
    blob_client.upload_blob.assert_called_once()


def test_process_email_can_target_kaps_when_verification_disabled(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("WMS_SENDER_EMAIL", "wms@example.com")
    monkeypatch.setenv("SENDER_EMAIL", "noreply@example.com")
    monkeypatch.setenv("KAPS_EMAIL", "kaps@example.com")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("EMAIL_VERIFICATION_MODE", "false")

    working_dir = tmp_path / "prod"
    working_dir.mkdir()
    monkeypatch.setattr("src.function_app.tempfile.mkdtemp", lambda prefix=None: str(working_dir))

    def fake_generate(item_code: str, description: str, output_dir: Path) -> Path:
        path = Path(output_dir) / f"{item_code}.png"
        path.write_bytes(b"barcode")
        return path

    def fake_bundle(po_number: str, barcode_paths, output_dir: Path | None = None) -> Path:
        path = Path(output_dir or working_dir) / f"{po_number}.zip"
        path.write_bytes(b"zip")
        return path

    with (
        patch("src.function_app.generate_barcode_image", side_effect=fake_generate),
        patch("src.function_app.bundle_barcodes", side_effect=fake_bundle),
        patch("src.function_app.send_email_with_attachment") as send_email_mock,
    ):
        blob_service, blob_client = _make_blob_service()
        process_email(
            email_body=SAMPLE_HTML,
            sender="wms@example.com",
            notify_admin=lambda *_args, **_kwargs: None,
            blob_service=blob_service,
        )

    send_email_mock.assert_called_once()
    kwargs = send_email_mock.call_args.kwargs
    assert kwargs["receiver_email"] == "kaps@example.com"
    blob_client.upload_blob.assert_called_once()


def test_process_email_skips_previously_processed_order(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("WMS_SENDER_EMAIL", "wms@example.com")
    monkeypatch.setenv("SENDER_EMAIL", "noreply@example.com")
    monkeypatch.setenv("KAPS_EMAIL", "kaps@example.com")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")

    working_dir = tmp_path / "dup"
    working_dir.mkdir()
    monkeypatch.setattr("src.function_app.tempfile.mkdtemp", lambda prefix=None: str(working_dir))

    blob_service, blob_client = _make_blob_service(existing="UPD-PO27652\n")

    message = process_email(
        email_body=SAMPLE_HTML,
        sender="wms@example.com",
        notify_admin=lambda *_args, **_kwargs: None,
        blob_service=blob_service,
    )

    assert message == "PO UPD-PO27652 was already processed."
    blob_client.upload_blob.assert_not_called()
