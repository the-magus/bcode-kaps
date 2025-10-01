# Azure Barcode Generator

This project is an Azure Function App that automates the process of sending barcode images to a supplier (Kaps) for new purchase orders.

## How it works

The Function App is triggered by an email from a Warehouse Management System (WMS). It parses the variant details from the email body, generates barcode images, zips them, and emails the zip file to Kaps.

## Setup

1.  Clone the repository.
2.  Install the dependencies: `pip install -r src/requirements.txt`
3.  Set the following environment variables in `src/local.settings.json`:
    *   `AZURE_STORAGE_CONNECTION_STRING`: The connection string to the Azure Storage Account for logging.
    *   `WMS_SENDER_EMAIL`: The email address of the WMS.
    *   `SENDER_EMAIL`: The email address to send the barcodes from.
    *   `KAPS_EMAIL`: The email address of the supplier (Kaps).
    *   `ADMIN_EMAIL`: The email address of the administrator to receive error notifications.

## Deployment

The Function App can be deployed to Azure using the Azure Functions extension for Visual Studio Code or the Azure CLI.

## Usage

The Function App is triggered by an email. To use it, you need to configure a Logic App or Power Automate to monitor an email inbox and trigger the Function App when a new email arrives.
