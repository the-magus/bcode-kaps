# Tasks: Azure Barcode Generator

**Input**: Design documents from `/specs/002-azure-barcode-generator/
**Prerequisites**: plan.md (required)

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root

## Phase 3.1: Setup
- [x] T001 Create the Azure Function App project structure as defined in `plan.md`.
- [x] T002 Create `requirements.txt` with the following dependencies: `azure-functions`, `beautifulsoup4`, `qrcode`, `Pillow`, `pytest`.
- [x] T003 [P] Configure linting with `ruff`.

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**
- [x] T004 Write a unit test in `tests/test_function_app.py` for parsing HTML variant rows into purchase order and variant data structures.
- [x] T005 Write a unit test in `tests/test_function_app.py` verifying purchase order number extraction and reuse in the zip filename and outbound email subject.
- [x] T006 Write a unit test in `tests/test_function_app.py` for barcode image generation per variant.
- [x] T007 Write a unit test in `tests/test_function_app.py` that confirms all barcodes for a purchase order are bundled into `<PO_NUMBER>.zip`.
- [x] T008 Write a unit test in `tests/test_function_app.py` covering the email sending logic with the zipped attachment and PO-specific subject.
- [x] T009 Write a unit test in `tests/test_function_app.py` ensuring only the configured WMS sender address is accepted.
- [x] T010 Write a unit test in `tests/test_function_app.py` for handling malformed or non-PO emails (log error and notify the administrator).
- [x] T011 Write a unit test in `tests/test_function_app.py` for logging completed purchase orders to Azure Blob Storage.

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [x] T012 Implement the HTML parsing logic in `src/function_app.py` to read variant rows from the WMS email.
- [x] T013 Implement a purchase order metadata helper in `src/function_app.py` to extract PO numbers and share them with downstream functions.
- [x] T014 Implement the barcode generation logic in `src/function_app.py`.
- [x] T015 Implement the zip bundling logic in `src/function_app.py` to write all barcode images for a PO into `<PO_NUMBER>.zip`.
- [x] T016 Implement the email sending logic in `src/function_app.py`, attaching the zip file and using the PO number in the subject.
- [x] T017 Implement the sender verification guard in `src/function_app.py` that enforces the configured WMS email address.
- [x] T018 Implement malformed and non-PO email handling in `src/function_app.py` to skip processing, log the error, and notify the administrator.
- [x] T019 Implement Azure Blob Storage logging in `src/function_app.py` to append completed purchase orders.

## Phase 3.4: Integration
- [x] T020 Implement the orchestrating Azure Function in `src/function_app.py` to coordinate verification, parsing, barcode generation, zipping, emailing, and logging.

## Phase 3.5: Polish
- [x] T021 Update `README.md` with deployment steps, cost-efficient Logic App trigger configuration, and expected throughput guidance.
- [x] T022 Create `docs/operations.md` documenting reliability monitoring, admin notification workflows, and recovery steps.
- [x] T023 Add docstrings to all functions and classes in `src/function_app.py` and related modules.

## Dependencies
- Tests (T004-T011) must be completed before implementation tasks (T012-T019)
- Implementation tasks (T012-T019) block integration work (T020)
- Core and integration tasks must finish before polish and documentation (T021-T023)
