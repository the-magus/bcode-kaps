# Operations Guide

This document captures the day-to-day operational guidance for the Azure Barcode Generator feature.

## Monitoring

- **Azure Application Insights**: Enable request and dependency telemetry for the Function App to track processing latency. Set an alert if the failure rate exceeds 1 error per 24 hours.
- **Blob Storage Logs**: Review the `completed-purchase-orders` container daily. Each `completed_pos_YYYY-MM-DD.log` file should list the processed purchase orders for that day. Absence of entries when orders are expected may indicate Logic App trigger issues.
- **Logic App Runs History**: Configure an alert on failed Logic App runs to promptly investigate mailbox connectivity or authentication problems.
- **SMTP Relay**: Monitor outbound email delivery (e.g., via SendGrid or Office 365 dashboards) for bounces to Kaps or the administrator.

## Notifications

- The function sends a notification email to `ADMIN_EMAIL` whenever a malformed purchase order email is detected or an unexpected exception occurs during processing.
- Ensure the admin inbox is monitored; consider routing alerts into an on-call system if 24/7 coverage is required.

## Recovery Procedures

1. **Malformed Email**
   - Review the administrator alert for the full error details.
   - Inspect the original email in the monitored mailbox. If the format is incorrect, contact the WMS team.
   - Once the email format is corrected, re-trigger the Logic App with the original payload to resume processing.

2. **Unauthorized Sender Rejected**
   - Confirm that the email originated from the legitimate WMS address.
   - Update the `WMS_SENDER_EMAIL` application setting if the sender address legitimately changed.

3. **Blob Storage Failures**
   - Validate the storage account connection string.
   - Ensure the `completed-purchase-orders` container exists and that the Function App has write permissions.
   - Reprocess recent orders if the log file is missing entries to maintain audit completeness.

4. **Email Delivery Issues**
   - Check SMTP host and port configuration (`SMTP_HOST`, `SMTP_PORT`).
   - Confirm the sender mailbox has permission to send to Kaps and the administrator.
   - Resend the most recent purchase order archive manually if Kaps did not receive it.

## Capacity & Scaling

- The workload is sized for ~3 purchase orders per day with roughly 30 variants per order.
- Azure Functions Consumption Plan automatically scales based on concurrency. No additional scaling actions are required under expected load.
- If volume increases substantially, confirm that barcode generation time remains within the default Function timeout and consider moving temporary storage to Azure Files for higher throughput.

## Dependency Management

- Azure has advised pinning `cryptography` to mitigate upstream packaging issues. The Function App tracks `cryptography==43.0.3`; update both `src/requirements.txt` and the deployment package together if you revise this pin in the future.
- Remote builds are enabled for deployments (`func azure functionapp publish ...`), which is the recommended workaround should dependency resolution regress again.
