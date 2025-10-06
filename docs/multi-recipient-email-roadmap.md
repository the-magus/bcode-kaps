# Multi-recipient email roadmap

## Mission
- Enable the Azure Function to deliver barcode archives to every operational contact (Kaps, purchasing, goods-in) while keeping administrators copied for audit trails.
- Preserve the existing verification mode behaviour so smoke testing can target only the administrator.
- Ensure the local tooling, configuration, tests, and documentation reflect the widened distribution list.

## Current snapshot
- Local trigger utility can already refresh purchase-order emails and post to the function endpoint.
- Recipient orchestration now resolves Kaps, purchasing, and goods-in mailboxes with the admin CC'd, while verification mode keeps traffic admin-only.
- Unit tests cover SMTP fan-out, verification routing, and helper behaviour; pytest passes locally.
- README and sample configuration list the new environment variables for optional mailboxes.

## Milestones
| ID | Description | Status | Notes |
|----|-------------|--------|-------|
| M1 | Update `send_email_with_attachment` to support multiple recipients and CCs | Complete | Helper refactored 2025-10-06. |
| M2 | Load purchasing and goods-in mailboxes from configuration and fan-out emails accordingly | Complete | `_collect_recipients` pulls optional mailboxes and CCs the admin. |
| M3 | Expand unit tests to cover multi-recipient routing and verification-mode gating | Complete | Added assertions for TO/CC behaviour and helper coverage. |
| M4 | Refresh documentation and local settings examples with new environment variables | Complete | README/env samples updated with purchasing and goods-in contacts. |
| M5 | Validate flow end-to-end via pytest and record outcomes | Complete | `pytest` run on 2025-10-06 (19 tests passing).

## Metrics & success criteria
- ✅ All required recipients receive messages when verification mode is disabled.
- ✅ Administrator remains sole recipient while verification mode is enabled.
- ✅ Unit test suite exercises both verification paths and the optional contact fan-out.
- ✅ README and sample settings list every environment variable needed for production.

## Risks & mitigations
- **Risk:** Misconfigured environment variables could silently remove recipients.  
  **Mitigation:** Raise explicit `RuntimeError` when verification mode is off but no TO recipients resolve.
- **Risk:** Duplicate email addresses may cause multiple sends.  
  **Mitigation:** Deduplicate recipient lists while preserving order before dispatching SMTP requests.
- **Risk:** Documentation drift leads to incorrect deployments.  
  **Mitigation:** Update README/local settings as part of the implementation milestone.

## Decisions & open questions
- Keep verification mode defaulting to admin-only to avoid accidental production delivery during validation.
- CC the administrator on production sends to maintain visibility without interrupting operational teams.
- No clarification received yet on additional distribution lists beyond purchasing/goods-in.

## Change log
- **2025-10-06:** Roadmap created to capture multi-recipient email initiative status.
- **2025-10-06:** Completed multi-recipient implementation, documentation, and tests; recorded passing pytest run.
