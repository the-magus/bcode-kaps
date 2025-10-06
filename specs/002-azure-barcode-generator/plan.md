# Implementation Plan: Azure Barcode Generator

**Branch**: `002-azure-barcode-generator` | **Date**: 2025-10-01 | **Spec**: `specs/002-azure-barcode-generator/spec.md`
**Input**: Feature specification from `/specs/002-azure-barcode-generator/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from file system structure or context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
An Azure Function App that automates sending barcode images to a supplier (Kaps) for new purchase orders. It's triggered by an email from a WMS, parses variant details from the email body, generates barcode images, zips them, and emails the zip file to Kaps.

## Technical Context
**Language/Version**: Python 3.11
**Primary Dependencies**: Azure Functions SDK for Python, BeautifulSoup, qrcode, Pillow, smtplib
**Storage**: Azure Blob Storage
**Testing**: pytest
**Target Platform**: Azure
**Project Type**: Single project
**Performance Goals**: No specific performance requirements.
**Constraints**: Must be cost-efficient.
**Scale/Scope**: 2-3 purchase orders per day, with an average of 30 variants per purchase order.

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

*   **I. First Principles Approach**: Does the plan break down the problem to its fundamental truths? - PASS
*   **II. Thorough Documentation**: Does the plan include tasks for creating a README, and adding docstrings to every file, class, and function, and comments where necessary? - PASS
*   **III. Testing**: Does the plan include tasks for writing tests, preferably using TDD? - PASS
*   **IV. Verify > Assumptions**: Does the plan have steps to verify assumptions? - PASS
*   **V. AI Must Ask Clarifying Questions**: Is the plan clear enough for an AI to execute, or does it need more clarification? - PASS
*   **VI. KISS: Keep It Simple, Stupid**: Is the proposed solution the simplest possible? - PASS
*   **VII. Simple Explanations**: Are the explanations in the plan simple and easy to understand? - PASS

## Project Structure

### Documentation (this feature)
```
specs/002-azure-barcode-generator/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
src/
├── function_app.py
├── requirements.txt
├── host.json
└── local.settings.json

tests/
├── test_function_app.py
```

**Structure Decision**: Single project structure for an Azure Function App.

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - Research the best way to trigger an Azure Function from an email (e.g., Logic Apps, Power Automate, or a custom solution).
   - Research the best Python libraries for HTML parsing, barcode generation, and email sending.

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: Use Azure Logic Apps to trigger the Azure Function. It's a serverless and cost-effective way to connect to an email inbox and trigger a workflow.
   - Rationale: Logic Apps provide a visual designer and pre-built connectors for various email services, making it easy to set up the trigger. It's more cost-effective than running a continuous process to check for emails.
   - Alternatives considered: Power Automate (similar to Logic Apps, but more focused on end-user automation), custom solution with IMAP/POP3 (more complex to implement and maintain).

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Define the `PurchaseOrder` and `Variant` entities with their attributes.

2. **Generate API contracts** from functional requirements:
   - No external APIs to define.

3. **Generate contract tests** from contracts:
   - No contract tests for this feature.

4. **Extract test scenarios** from user stories:
   - Create a `quickstart.md` with instructions on how to deploy the Azure Function App and configure the Logic App trigger.

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/bash/update-agent-context.sh gemini`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove any arguments.

**Output**: data-model.md, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks for:
  - Setting up the Azure Function App project structure.
  - Implementing the HTML parsing logic.
  - Implementing the barcode generation logic.
  - Implementing the email sending logic.
  - Implementing the logging logic to Azure Blob Storage.
  - Writing unit tests for each component.
  - Creating a README.md file with deployment and usage instructions.

**Ordering Strategy**:
- TDD order: Tests before implementation 
- Dependency order: Data parsing, barcode generation, email sending, logging.

**Estimated Output**: 10-15 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
|           |            |                                     |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [X] Phase 0: Research complete (/plan command)
- [X] Phase 1: Design complete (/plan command)
- [ ] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [X] Initial Constitution Check: PASS
- [X] Post-Design Constitution Check: PASS
- [X] All NEEDS CLARIFICATION resolved
- [ ] Complexity deviations documented

---
*Based on Constitution v1.0.2 - See `/.specify/memory/constitution.md`*