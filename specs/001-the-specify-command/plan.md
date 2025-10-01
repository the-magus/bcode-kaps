# Implementation Plan: The /specify command

**Branch**: `001-the-specify-command` | **Date**: 2025-10-01 | **Spec**: `specs/001-the-specify-command/spec.md`
**Input**: Feature specification from `/specs/001-the-specify-command/spec.md`

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
Create a feature specification from a natural language description. The technical approach is to use a shell script to create a new feature branch and a `spec.md` file from a template.

## Technical Context
**Language/Version**: Bash
**Primary Dependencies**: `git`, `bash`
**Storage**: files
**Testing**: `bats`
**Target Platform**: Linux
**Project Type**: single project
**Performance Goals**: no specific requirements
**Constraints**: Not applicable for this feature.
**Scale/Scope**: Not applicable for this feature.

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
specs/001-the-specify-command/
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
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Single project structure.

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: `bats` for testing the bash script.
   - Rationale: `bats` is a TAP-compliant testing framework for Bash. It is simple and easy to use.
   - Alternatives considered: `shellcheck` (linter, not a testing framework).

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - No entities for this feature.

2. **Generate API contracts** from functional requirements:
   - No API contracts for this feature.

3. **Generate contract tests** from contracts:
   - No contract tests for this feature.

4. **Extract test scenarios** from user stories:
   - Create a `quickstart.md` with instructions on how to use the `/specify` command.

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/bash/update-agent-context.sh gemini`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove any arguments.
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (quickstart.md)
- Create a task to write a `README.md` for the `create-new-feature.sh` script.
- Create a task to write `bats` tests for the `create-new-feature.sh` script.
- Create a task to update the `GEMINI.md` file with the documentation for the `/specify` command.

**Ordering Strategy**:
- TDD order: Tests before implementation 
- Dependency order: Documentation and tests before implementation.

**Estimated Output**: 3-5 numbered, ordered tasks in tasks.md

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