# Historic PO regeneration roadmap

## Mission
- Recreate barcode archives for previously processed purchase orders when downstream teams require replacements.
- Maintain accurate processed-PO audit trails while allowing controlled re-runs for historical orders.
- Document a repeatable procedure for restoring, regenerating, and verifying archived purchase orders.

## Current snapshot
- The Azure Function and local generator respect `processed_pos.log`, preventing duplicate processing by default.
- Latest HTML payload (`latest_po_email.html`) still contains variants for POs UPD-PO27635, UPD-PO27779, and UPD-PO27922.
- `processed_pos.log` lists these POs, so the local generator currently skips them and no replacement archives exist in `barcodes/`.
- Backups of the processed log (for example `processed_pos.log.bak-20251008`) are available for safe restoration.

## Milestones
| ID | Description | Status | Notes |
|----|-------------|--------|-------|
| M1 | Capture current state of HTML payloads, processed log, and existing barcode archives | Complete | Confirmed HTML includes requested POs; barcodes folder missing archives. |
| M2 | Create controlled workflow to rerun specific historical POs without disturbing other audit entries | Complete | Backed up log and removed requested POs locally prior to regeneration. |
| M3 | Regenerate and verify archives for POs 27635, 27779, 27922 | Complete | Local generation produced three replacement archives on 2025-10-11. |
| M4 | Restore processed log integrity and document regeneration procedure | In Progress | Log restored with regenerated entries appended; updating docs and ops guidance. |

## Metrics & success criteria
- ✅ Replacement archives produced for each requested PO and stored under `barcodes/`.
- ✅ Processed log reconciled so Azure Function history remains accurate after regeneration.
- ✅ Roadmap and operations guidance describe the recovery workflow for historical purchase orders.

## Risks & mitigations
- **Risk:** Removing processed POs from the log could trigger unintended reprocessing in production.  
  **Mitigation:** Use local backups and avoid modifying deployed storage logs; limit changes to the local copy used for regeneration.
- **Risk:** HTML payload may not include all historical line items.  
  **Mitigation:** Verify HTML coverage before running regeneration and request resend if missing.
- **Risk:** Manual steps introduce inconsistency.  
  **Mitigation:** Document explicit recovery sequence and update operations guide once validated.

## Decisions & open questions
- Re-run will be performed locally with `--no-post` to avoid triggering production email sends.  
- Processed log adjustments will be reversed after regeneration to maintain audit completeness.  
- Pending decision: whether to automate a "force regenerate" mode within tooling for future recoveries.

## Change log
- **2025-10-11:** Generated replacement archives for UPD-PO27635, UPD-PO27779, and UPD-PO27922 after backing up `processed_pos.log`.
- **2025-10-11:** Roadmap created to track historic PO regeneration effort for UPD-PO27635, UPD-PO27779, and UPD-PO27922.
