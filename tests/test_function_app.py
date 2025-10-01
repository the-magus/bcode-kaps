import pytest
import os
from unittest.mock import patch
from src.function_app import parse_html_email, generate_barcode, send_email_with_attachment, log_completed_purchase_order

HTML_CONTENT = '''
<html><head><title>Alert Summary - New PO Kaps</title><meta charset="utf-8">
        <style>
          body { font-size: 16px; word-break: break-word; white-space: pre-wrap; }
        </style>
        </head><body><!DOCTYPE html><html lang="en" xmlns="http://www.w3.org/1999/xhtml"><head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title></title>
</head>
<body style="margin:20px">
    <p style="text-align:center; margin-bottom:25px;">
        <img src="https://www.orderwise.co.uk/wp-content/uploads/2018/10/OrderWise-business-software-Logo.png" alt="OrderWise" width="300" height="70">
    </p>

    <center><b style="color:#515151; font-family:Arial; font-size:30px;">New PO Kaps</b></center>

    <center><p style="color:#515151; font-family:Arial; margin-top:10px; font-size:18px;">122 alerts generated</p></center>

    <div style="width:100%">
        <div style="width:80%; margin: 0 auto;">
            <table>
                <tr>
                            <td width="100%" style="font-size:18px; font-family:Arial; font-weight:bold; color:#515151;">Account Number: TS11892</td>
                            <th rowspan="3&lt;/th">
                        </tr>
                        <tr style="font-size:12px; font-family:Arial; color:#515151;">
                            <td>Supplier Name: Kaps Finishing Ltd</td>
                        </tr><tr>
                            <td style="font-family:Arial; font-size:14px; color:gray; padding-top:10px;">PO: UPD-PO27652 | Item: V109327 | Desc: Children must not play on this site 200mm x 300mm - 1mm Rigid Plastic Sign</td>
                        </tr><tr>
                            <td colspan="2"><hr size="0" style="color:lightgray; font-size:0px;"></td>
                        </tr>
            </table>
        </div>
    </div>
</body></html></body></html>
'''

def test_parse_html_email():
    expected_data = [
        {
            'po_number': 'UPD-PO27652',
            'item_code': 'V109327',
            'description': 'Children must not play on this site 200mm x 300mm - 1mm Rigid Plastic Sign'
        }
    ]
    assert parse_html_email(HTML_CONTENT) == expected_data

def test_generate_barcode():
    variant_code = "V109327"
    # The function should save the barcode to a file and return the path
    barcode_path = generate_barcode(variant_code)
    assert os.path.exists(barcode_path)
    # Clean up the generated file
    os.remove(barcode_path)

@patch('smtplib.SMTP')
def test_send_email_with_attachment(mock_smtp):
    sender_email = "test@example.com"
    receiver_email = "kaps@example.com"
    subject = "Test Subject"
    body = "Test Body"
    attachment_path = "test.zip"

    # Create a dummy attachment file
    with open(attachment_path, "w") as f:
        f.write("test content")

    send_email_with_attachment(sender_email, receiver_email, subject, body, attachment_path)

    # Check that the SMTP server was connected to
    mock_smtp.assert_called_with("smtp.test.com", 587)
    # Check that the email was sent
    instance = mock_smtp.return_value
    assert instance.sendmail.call_count == 1

    # Clean up the dummy attachment file
    os.remove(attachment_path)

@patch('src.function_app.BlobServiceClient')
def test_log_completed_purchase_order(mock_blob_service_client, monkeypatch):
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test;EndpointSuffix=core.windows.net")
    po_number = "UPD-PO27652"
    
    mock_blob_client = mock_blob_service_client.from_connection_string.return_value.get_blob_client.return_value
    mock_blob_client.get_blob_properties.side_effect = Exception()

    log_completed_purchase_order(po_number)

    # Check that the blob client was created
    mock_blob_service_client.from_connection_string.assert_called_once()
    # Check that a blob was uploaded
    assert mock_blob_client.upload_blob.call_count == 1
