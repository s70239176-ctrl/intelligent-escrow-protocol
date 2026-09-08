# Submission Notes: Intelligent Escrow Protocol (IEP)

Reviewer-oriented notes: what this is, what to run, and what to look at
first.

## What this is

A standalone GenLayer Intelligent Contract primitive: decentralized
escrow for subjective deliverables, with a manual happy path and an
LLM-consensus-adjudicated dispute path. One contract, no frontend, no
backend service, no external dependencies beyond the GenLayer SDK.

## Where to look first

| If you want to see... | Look at |
| --- | --- |
| The contract itself | [`contracts/escrow.py`](contracts/escrow.py) |
| The state machine | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| The equivalence design + prompt-injection defense | [`docs/CONSENSUS.md`](docs/CONSENSUS.md) |
| Test cases, including adversarial ones | [`tests/direct/test_escrow.py`](tests/direct/test_escrow.py) |
| Sample inputs used across tests | [`fixtures/`](fixtures/) |

## What to run

Deterministic, no GenVM or LLM required:

```bash
python scripts/local_helper_check.py
python scripts/preflight.py
```

GenLayer Direct Mode test suite (requires a local GenVM simulator /
`gltest` Direct Mode backend):

```bash
python -m pip install -r requirements-test.txt
pytest tests/direct -q
```

Disposable StudioNet lifecycle proof (real testnet transactions, real
LLM-backed consensus calls -- run intentionally, not on every commit):

```bash
gltest --network studionet tests/integration/test_escrow_studionet.py -s
```

## Architectural patterns this submission specifically demonstrates

1. **Equivalence design** — the adjudication step never lets consensus
   depend on freeform LLM text. It forces a strict two-key JSON schema
   and reaches agreement via `gl.eq_principle.prompt_comparative` keyed
   explicitly on the `decision` field, ignoring `chain_of_thought`
   wording differences between validators. See `docs/CONSENSUS.md`.
2. **Greybox sanitization** — the Seller's untrusted payload is never
   interpolated directly into the adjudication prompt. It first passes
   through an isolated `gl.nondet.exec_prompt` call that has zero
   knowledge of the acceptance criteria or decision schema, so it has no
   meaningful decision to leak even if fully compromised by injected
   text. See `docs/CONSENSUS.md` and the `prompt_injection_attempt`
   fixture in `fixtures/`.

## Known limitations / explicitly out of scope

- `_release_funds` in `contracts/escrow.py` is a documented no-op. This
  primitive is deliberately asset-agnostic; wiring it to a specific
  token/transfer mechanism is left to integrators.
- There is no appeal/re-adjudication path once `resolve_dispute()`
  settles a case. See "Extending This Primitive" in
  `docs/ARCHITECTURE.md` for how a `CHALLENGED` state could be added.
- `tests/integration/test_escrow_studionet.py` is a stub with the
  deployment/account wiring left for the integrator's specific
  `gltest`/SDK version -- it documents the intended lifecycle proof
  rather than being a drop-in runnable test.

## Verified deployment

_Fill in after deploying to StudioNet:_

- Contract address: `TBD`
- Deploy transaction: `TBD`
- Deployer: `TBD`
- Network: StudioNet
