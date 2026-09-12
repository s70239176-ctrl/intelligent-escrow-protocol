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
| The evidence acquisition + equivalence design + prompt-injection defense | [`docs/CONSENSUS.md`](docs/CONSENSUS.md) |
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

1. **Evidence acquisition and normalization** — the Seller's
   `deliverable_locator` is never adjudicated at face value. If it's a
   fetchable URI (`http://`, `https://`, `ipfs://`), the contract
   retrieves the actual referenced content via `gl.nondet.web.render`
   (with `ipfs://` normalized to a public gateway URL first) and
   adjudicates *that*, not the Seller's description of it. A failed
   fetch is replaced with a fixed placeholder rather than silently
   trusting the Seller. See `docs/CONSENSUS.md` and the
   `fabricated_description_contradicted_by_evidence` fixture.
2. **Equivalence design** — the adjudication step never lets consensus
   depend on freeform LLM text. It forces a strict two-key JSON schema
   and reaches agreement via `gl.eq_principle.prompt_comparative` keyed
   explicitly on the `decision` field, ignoring `chain_of_thought`
   wording differences between validators. See `docs/CONSENSUS.md`.
3. **Greybox sanitization** — whichever evidence acquisition produced
   (fetched content or plain text) is never interpolated directly into
   the adjudication prompt. It first passes through an isolated
   `gl.nondet.exec_prompt` call that has zero knowledge of the
   acceptance criteria or decision schema, so it has no meaningful
   decision to leak even if fully compromised by injected text. See
   `docs/CONSENSUS.md` and the `prompt_injection_in_fetched_content`
   fixture in `fixtures/`.

## Known limitations / explicitly out of scope

- `gl.nondet.web.render(..., mode="text")` retrieves text-mode content.
  For a fundamentally visual deliverable (an SVG's rendered appearance,
  a PNG mockup), this fetches the underlying markup or surrounding page
  text, not a rendered visual judgment of the image -- a meaningfully
  closer approximation of the real deliverable than trusting an
  unverified Seller description, but not equivalent to a human or
  vision-capable model looking at the artwork itself. See "Known
  residual limitation" in `docs/CONSENSUS.md`.
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
