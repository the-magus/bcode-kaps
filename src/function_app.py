import azure.functions as func
import logging
import zipfile
from bs4 import BeautifulSoup
import barcode
from barcode.writer import ImageWriter
import tempfile
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import os
from azure.storage.blob import BlobServiceClient
from datetime import datetime
import azure.functions as func
import logging
import zipfile

app = func.FunctionApp()

@app.route(route="barcode_generator")
def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main function for the Azure Function App.

    This function is triggered by an HTTP request (from a Logic App).
    It parses the email body, generates barcodes, and sends them to the supplier.
    """
    logging.info('Python HTTP trigger function processed a request.')

    email_body = req.get_body().decode('utf-8')
    
    # Verify sender
    sender = req.headers.get('X-Forwarded-For')
    wms_sender = os.getenv('WMS_SENDER_EMAIL')
    if sender != wms_sender:
        logging.warning(f"Received email from unauthorized sender: {sender}")
        return func.HttpResponse("Unauthorized sender.", status_code=401)

    try:
        variants = parse_html_email(email_body)
        if not variants:
            logging.info("No variants found in the email.")
            return func.HttpResponse("No variants found.", status_code=200)

        po_number = variants[0]['po_number']
        barcode_files = []
        for variant in variants:
            barcode_path = generate_barcode(variant['item_code'])
            barcode_files.append(barcode_path)

        zip_path = f"/tmp/{po_number}.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file in barcode_files:
                zipf.write(file, os.path.basename(file))

        sender_email = os.getenv('SENDER_EMAIL')
        receiver_email = os.getenv('KAPS_EMAIL')
        subject = f"Barcode for PO {po_number}"
        body = f"Please find attached the barcodes for purchase order {po_number}."
        send_email_with_attachment(sender_email, receiver_email, subject, body, zip_path)

        log_completed_purchase_order(po_number)

        return func.HttpResponse(f"Successfully processed PO {po_number}.")

    except Exception as e:
        logging.error(f"Error processing email: {e}")
        # Send notification email to admin
        admin_email = os.getenv('ADMIN_EMAIL')
        if admin_email:
            send_email_with_attachment(sender_email, admin_email, "Error in Barcode Generator", str(e), None)
        return func.HttpResponse("Error processing email.", status_code=500)

def parse_html_email(html_content):
    """
    Parses the HTML email body to extract purchase order details.

    Args:
        html_content: The HTML content of the email.

    Returns:
        A list of dictionaries, where each dictionary represents a variant.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    variants = []
    for item in soup.find_all('td', style='font-family:Arial; font-size:14px; color:gray; padding-top:10px;'):
        text = item.get_text()
        parts = text.split('|')
        po_number = parts[0].split(':')[1].strip()
        item_code = parts[1].split(':')[1].strip()
        description = parts[2].split(':')[1].strip()
        variants.append({
            'po_number': po_number,
            'item_code': item_code,
            'description': description
        })
    return variants

def generate_barcode(variant_code):
    """
    Generates a barcode image for the given variant code.

    Args:
        variant_code: The variant code to generate the barcode for.

    Returns:
        The path to the generated barcode image.
    """
    code128 = barcode.get_barcode_class('code128')
    barcode_image = code128(variant_code, writer=ImageWriter())
    temp_dir = tempfile.gettempdir()
    filename = barcode_image.save(f'{temp_dir}/{variant_code}')
    return filename

def send_email_with_attachment(sender_email, receiver_email, subject, body, attachment_path):
    """
    Sends an email with an attachment.

    Args:
        sender_email: The sender's email address.
        receiver_email: The receiver's email address.
        subject: The subject of the email.
        body: The body of the email.
        attachment_path: The path to the attachment file.
    """
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    with open(attachment_path, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
    
    encoders.encode_base64(part)
    
    part.add_header(
        'Content-Disposition',
        f'attachment; filename= {os.path.basename(attachment_path)}',
    )
    
    msg.attach(part)
    
    server = smtplib.SMTP("smtp.test.com", 587)
    server.sendmail(sender_email, receiver_email, msg.as_string())
    server.quit()

def log_completed_purchase_order(po_number):
    """
    Logs a completed purchase order to a text file in Azure Blob Storage.

    Args:
        po_number: The purchase order number to log.
    """
    connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    container_name = "completed-purchase-orders"
    blob_name = f"completed_pos_{datetime.utcnow().strftime('%Y-%m-%d')}.log"

    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

    log_entry = f"{datetime.utcnow().isoformat()}: {po_number}\n"

    try:
        blob_properties = blob_client.get_blob_properties()
        existing_content = blob_client.download_blob().readall()
        new_content = existing_content + log_entry.encode('utf-8')
        blob_client.upload_blob(new_content, overwrite=True)
    except Exception:
        blob_client.upload_blob(log_entry.encode('utf-8'))
