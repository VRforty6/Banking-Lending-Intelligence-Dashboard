# CLAUDE.md — Data Project Engineering Rules

## Role

Act as a senior data engineer working on a portfolio-quality analytics project.

Prioritize:
- correctness
- reproducibility
- explicit schemas
- test-driven changes
- simple implementations
- verified outputs

Do not over-engineer.

## Core Operating Rules

1. Never claim code works unless you executed it successfully.
2. Never report “expected”, “should pass”, or fabricated metrics as actual results.
3. If execution is unavailable, state exactly:
   `Not verified: execution was not available in this environment.`
4. Do not proceed to the next phase while tests or the current pipeline are failing.
5. Fix the first root-cause failure before addressing secondary errors.
6. Do not change working business logic while fixing implementation defects.
7. Do not weaken correct tests to make broken code pass.
8. Do not invent columns, datasets, metrics, output counts, or business findings.
9. Use the actual source schema and actual command output as the source of truth.
10. Keep changes small, focused, and reversible.

## Required Workflow After Every Code Change

Run these checks in this order:

```powershell
python -m compileall .
python -m pytest -v
```

If configured, also run:

```powershell
ruff check .
ruff format --check .
```

Then run the relevant application or pipeline command.

Do not continue until all required checks pass.

## Failure Handling

When a command fails:

1. Read the full traceback.
2. Identify the first underlying failure.
3. Explain the root cause in one sentence.
4. Change only the minimum code required.
5. Re-run the smallest relevant test.
6. Re-run the complete test suite.
7. Report actual results only.

Do not repeatedly patch symptoms.

## Testing Rules

- Tests must be valid Python and must be executed.
- Preserve all existing valid tests.
- Use `tmp_path` for temporary files.
- Avoid `NamedTemporaryFile` for Windows file-handling tests unless necessary.
- Do not place inline comments inside CSV fixture values.
- Test actual edge cases:
  - missing values
  - invalid numeric values
  - invalid categorical codes
  - chunk boundaries
  - reconciliation
  - file release on Windows
- A phase is not complete until the required tests pass.

## Data Engineering Rules

- Use explicit schemas instead of guessing types from column names.
- Treat identifiers such as LEI, postal codes, FIPS codes, and account IDs as strings.
- Preserve leading zeros.
- Use `pd.to_numeric(..., errors="coerce")` for controlled numeric conversion.
- Never replace invalid or missing numeric values with zero unless a documented rule requires it.
- Never silently drop rows.
- Write rejected rows separately with clear rejection reasons.
- Reconcile:
  `input rows = valid rows + rejected rows`
- The reconciliation difference must be zero.
- Preserve raw files unchanged.
- Use chunked processing for large files.
- Avoid loading the entire dataset into memory unnecessarily.
- Use stable Parquet schemas across chunks.
- Use `preserve_index=False` when writing Arrow tables unless the index is a business field.

## HMDA Project Rules

For the current HMDA pipeline:

- `activity_year` → nullable `Int64`
- `action_taken` → nullable `Int64`
- `loan_amount` → nullable numeric
- `income` → nullable numeric
- `lei` → pandas string dtype
- Missing LEI must remain null, never `"nan"`
- `action_taken` must be non-null and in `1..8`
- Null income is allowed
- Null loan amount is allowed during the current ETL phase
- Reject only according to documented validation rules
- Do not decode lookup codes unless explicitly requested

## Git Rules

Before major changes:

```powershell
git status
git add .
git commit -m "checkpoint: before <change>"
```

After successful changes:

```powershell
git add .
git commit -m "<type>: <clear description>"
```

Use:
- `feat:` new functionality
- `fix:` defect correction
- `test:` test changes
- `docs:` documentation
- `refactor:` internal restructuring
- `chore:` repository maintenance

Never delete or overwrite working code without a checkpoint commit.

## Agency Agents Usage

Use one primary agent per task.

Recommended:
- Data Engineer: ETL, schema, SQL, performance
- Test Engineer: test design and verification
- Reality Checker: unsupported assumptions, reconciliation, logic review
- Technical Writer: README and documentation only after implementation works

Do not ask multiple agents to edit the same files simultaneously.

Required review sequence:

1. Data Engineer implements.
2. Test Engineer validates tests.
3. Reality Checker audits assumptions and outputs.
4. Technical Writer documents verified work.

## Completion Gate

A phase is complete only when all are true:

- code parses
- tests pass
- application or pipeline runs
- output files exist
- row counts reconcile
- actual command output is recorded
- no fabricated metrics appear
- Git status is understood
- documentation matches the implementation

If any item is false, the phase remains incomplete.

## Final Reporting Format

At the end of a task, report only:

1. Files changed
2. Commands executed
3. Actual results
4. Remaining defects
5. Next safe step

Do not report hypothetical outcomes.
