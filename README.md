# Azure Barcode Generator

This project is an Azure Function App that automates the process of sending barcode images to a supplier (Kaps) for new purchase orders.

## How it works

The Function App is triggered by an email from a Warehouse Management System (WMS). It parses the variant details from the email body, generates barcode images, zips them, and emails the zip file to Kaps.

## Setup

1. Clone the repository.
2. Create and activate a Python 3.11 virtual environment.
3. Install the dependencies:

    ```bash
    pip install -r src/requirements.txt
    ```

4. Provide the following environment variables (for local development place them in `src/local.settings.json`, and in production store them as Function App application settings):

    | Variable | Purpose |
    | --- | --- |
    | `AZURE_STORAGE_CONNECTION_STRING` | Connection string for the storage account that stores the `processed_pos.log` canonical record. |
    | `WMS_SENDER_EMAIL` | Authoritative sender address for inbound purchase order emails. |
    | `SENDER_EMAIL` | Outbound email address used when contacting Kaps and the administrator. |
    | `KAPS_EMAIL` | Destination address for barcode deliveries. (Production: `tiger@kapsfinishing.co.uk`.) |
    | `ADMIN_EMAIL` | Address that receives error notifications for malformed or failed emails. (Production: `hsatchell@upwood-distribution.co.uk`.) |
    | `EMAIL_VERIFICATION_MODE` *(optional)* | Defaults to `true`. While enabled, production emails are routed to the administrator for smoke testing. Set to `false` after verifying the deployed Function App to resume deliveries to Kaps. |
    | `SMTP_HOST` / `SMTP_PORT` *(optional)* | Override defaults for the SMTP relay used to send email if different from the local development placeholder. |

## Deployment

1. **Publish the Azure Function**
    - Ensure the project is built locally by running `pytest`.
    - Use the Azure Functions Core Tools or the Azure CLI to publish the function (`func azure functionapp publish <app-name>`).

2. **Configure a cost-efficient trigger**
    - Create an Azure Logic App (Consumption plan) that listens to the mailbox where the WMS delivers purchase order reports.
    - Add a filter so only messages from `WMS_SENDER_EMAIL` trigger the workflow, keeping executions minimal and pay-per-use.
    - Configure the Logic App to invoke the deployed HTTP function endpoint (supply the body of the email as the request payload and forward the sender address in a header such as `X-Forwarded-For`).

3. **Provision supporting resources**
    - Create the target Blob Storage container `completed-purchase-orders` if it does not already exist.
    - Store all required application settings in the Function App configuration and provide the Logic App access to the Function key.

## Expected Throughput and Cost Profile

- Designed workload: 2–3 purchase orders per day (~30 variants per order).
- Barcode generation and zipping happen on-demand, so the Function App incurs charges only while processing events.
- Using a consumption-based Logic App keeps idle costs near zero; ensure email filters prevent unnecessary triggers.

## Usage

Once the Logic App is wired to the mailbox, each matching email automatically triggers the Function App, which:

1. Verifies the sender address.
2. Parses variant rows from the HTML body.
3. Generates Code128 barcodes and zips them using the purchase order number as the filename.
4. Emails the archive to Kaps (or the admin while verification mode is enabled) and records the purchase order number in `processed_pos.log` so duplicates are ignored on subsequent runs.

If the email is malformed, the function logs the issue and sends an alert to the administrator without contacting Kaps.

## Local Testing

- Execute the unit test suite:

  ```bash
  pytest
  ```

- Linting is configured via `ruff.toml`; run `ruff check .` to enforce style rules.
- Use the Functions Core Tools (`func start`) with a sample email payload to exercise the end-to-end workflow locally.

## Operations

- Operational runbooks and reliability guidance live in `docs/operations.md`.
- Blob storage contains a canonical `processed_pos.log` file holding all completed purchase orders. Seed this file with any historic POs (one per line) to prevent the app from reprocessing them.
