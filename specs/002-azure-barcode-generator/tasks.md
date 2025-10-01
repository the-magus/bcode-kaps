# Tasks: Azure Barcode Generator

**Input**: Design documents from `/specs/002-azure-barcode-generator/
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root

## Phase 3.1: Setup
- [ ] T001 Create the Azure Function App project structure as defined in `plan.md`.
- [ ] T002 Create `requirements.txt` with the following dependencies: `azure-functions`, `beautifulsoup4`, `python-barcode`, `pytest`.
- [ ] T003 [P] Configure linting with `ruff`.

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**
- [ ] T004 [P] Write a unit test in `tests/test_function_app.py` for parsing the HTML email body.
- [ ] T005 [P] Write a unit test in `tests/test_function_app.py` for generating a barcode.
- [ ] T006 [P] Write a unit test in `tests/test_function_app.py` for the email sending logic.
- [ ] T007 [P] Write a unit test in `tests/test_function_app.py` for the logging logic.

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [ ] T008 Implement the HTML parsing logic in `src/function_app.py`.
- [ ] T009 Implement the barcode generation logic in `src/function_app.py`.
- [ ] T010 Implement the email sending logic in `src/function_app.py`.
- [ ] T011 Implement the logging logic to Azure Blob Storage in `src/function_app.py`.

## Phase 3.4: Integration
- [ ] T012 Implement the main function in `src/function_app.py` to orchestrate the parsing, barcode generation, email sending, and logging.

## Phase 3.5: Polish
- [ ] T013 [P] Create a `README.md` file with deployment and usage instructions.
- [ ] T014 [P] Add docstrings to all functions and classes.

## Dependencies
- Tests (T004-T007) before implementation (T008-T011)
- T008, T009, T010, T011 block T012
- Implementation before polish (T013-T014)
