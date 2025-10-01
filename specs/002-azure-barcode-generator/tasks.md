# Tasks: Azure Barcode Generator

**Input**: Design documents from `/specs/002-azure-barcode-generator/
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root

## Phase 3.1: Setup
- [x] T001 Create the Azure Function App project structure as defined in `plan.md`.
- [x] T002 Create `requirements.txt` with the following dependencies: `azure-functions`, `beautifulsoup4`, `python-barcode`, `pytest`.
- [x] T003 [P] Configure linting with `ruff`.

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**
- [x] T004 [P] Write a unit test in `tests/test_function_app.py` for parsing the HTML email body.
- [x] T005 [P] Write a unit test in `tests/test_function_app.py` for generating a barcode.
- [x] T006 [P] Write a unit test in `tests/test_function_app.py` for the email sending logic.
- [x] T007 [P] Write a unit test in `tests/test_function_app.py` for the logging logic.

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [x] T008 Implement the HTML parsing logic in `src/function_app.py`.
- [x] T009 Implement the barcode generation logic in `src/function_app.py`.
- [x] T010 Implement the email sending logic in `src/function_app.py`.
- [x] T011 Implement the logging logic to Azure Blob Storage in `src/function_app.py`.

## Phase 3.4: Integration
- [x] T012 Implement the main function in `src/function_app.py` to orchestrate the parsing, barcode generation, email sending, and logging.

## Phase 3.5: Polish
- [x] T013 [P] Create a `README.md` file with deployment and usage instructions.
- [x] T014 [P] Add docstrings to all functions and classes.

## Dependencies
- Tests (T004-T007) before implementation (T008-T011)
- T008, T009, T010, T011 block T012
- Implementation before polish (T013-T014)
