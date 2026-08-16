# cuec-review

> **Cubiczan stack** — [CHP](https://github.com/Cubiczan/consensus-hardening-protocol) · [control-spine](https://github.com/Cubiczan/control-spine) · **You are here:** `cuec-review`

**SOC 1 / CUEC review workflow.** The complementary user-entity controls in a service auditor's report have to be extracted, assigned to a named owner, mapped to an internal control, and evidenced for the period the SOC actually covers. Most close teams never do this step. It is a recurring third-party / service-org finding on listed-company 10-Qs.

This is not a PDF parser and not `agent-governance`. Extraction is an input. The engine tests whether the register is complete enough to be evidence.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## What it produces

| Artefact | What a tester samples |
|---|---|
| Vendor SOC register | In-scope service orgs vs AP / IT vendor list |
| CUEC register | Owner, mapped internal control, period evidence reference |
| Expiry calendar | SOC period end and bridge-letter coverage vs the entity reporting date |
| Exception log | Qualified opinions, SOC exceptions, unmapped CUECs, coverage gaps |

## Findings the engine raises

- `SOC-EXPIRED` — report does not cover the entity period and no bridge letter fills the gap
- `SOC-OPINION` — opinion is not unqualified
- `SOC-EXCEPTION` — exceptions listed in the report, carried into the pack
- `CUEC-NO-OWNER` / `CUEC-UNMAPPED` / `CUEC-GAP` / `CUEC-NO-REF`
- `CUEC-NONE-EXTRACTED` — SOC on file, zero CUECs in the register

## Quick start

```bash
pip install -e ".[dev]"
pytest -q
cuec-review examples/register.json \
  --as-of 2026-06-30 --period-start 2026-01-01 --period-end 2026-06-30 \
  --period-label "H1 2026" --owner "Controller"
```

Exit code 2 when the spine is `PROVISIONAL_LOCK` or `HALT` — typically a named owner on a pack that still has CUEC or coverage gaps. Unsigned exploration is `EXPLORING` (exit 0) and is **not evidence**. Only `LOCKED` is evidence.

## Compliance spine

Vendored `control-spine`. Open findings are blocking: they cannot reach `LOCKED`. A controller who signs a gap pack gets `PROVISIONAL_LOCK`, not a clean opinion.
