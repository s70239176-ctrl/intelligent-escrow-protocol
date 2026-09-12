# Intelligent Escrow Protocol (IEP)

**A GenLayer Intelligent Contract primitive for decentralized escrow of subjective deliverables, adjudicated by LLM consensus when Buyer and Seller can't agree.**

Escrow answers a question ordinary smart contracts cannot:
> Does this deliverable satisfy a plain-English brief, or does the money go back to whoever paid for it?

It is a **standalone Intelligent Contract primitive**, not a product application. There is intentionally **no frontend and no backend service**. Marketplaces, freelance platforms, bounty boards, and other Intelligent Contracts can consume its escrow state directly.

## Why this exists

Traditional smart-contract escrow only works for objectively verifiable
conditions ("did the oracle report a price above X"). It falls apart the
moment the deliverable is **subjective**:

- a vector graphic may or may not match "cyberpunk cat";
- an essay may or may not actually explain the assigned topic;
- a landing page mockup may be 80% complete and reasonable people could
  disagree whether that's "done."

A normal parser or oracle can't resolve that gap — someone still has to
*judge* the work. Today that someone is a centralized platform, an
expensive arbitrator, or a Discord argument. The Intelligent Escrow
Protocol replaces that bottleneck with GenLayer's LLM-consensus
validators, while keeping a fully manual, LLM-free path for the common
case where Buyer and Seller simply agree.

## Core primitive

A single escrow instance tracks one Buyer, one Seller, one amount, and
one plain-text acceptance criteria string, agreed before delivery:

```
Buyer + Seller + amount + acceptance_criteria
              │
              ▼
   Seller submits deliverable_locator
     (a URI or a text description)
              │
       ┌──────┴──────┐
       ▼             ▼
   Buyer approves   Buyer or Seller disputes
   (no LLM)              │
       │                 ▼
       │        Contract fetches evidence,
       │      then LLM-consensus adjudication
       │                 │
       └────────┬────────┘
                ▼
         funds released to
         SELLER or BUYER
```

Each escrow is a single deployed contract instance — this primitive is
meant to be deployed once per agreement, the same way a single-use
payment channel or a one-off multisig is, not as a shared pooled
contract across unrelated deals.

## Lifecycle

```
   submit_deliverable(deliverable_locator)      [caller must be Seller]
PENDING ─────────────────────────────────────► DELIVERED
                                                    │  │
                        approve()                   │  │ dispute()
                    [caller = Buyer]                │  │ [caller = Buyer or Seller]
                        ┌───────────────────────────┘  │
                        ▼                              ▼
                    RESOLVED                       DISPUTED
                (winner = SELLER)                      │
                                                        │ resolve_dispute()
                                                        │ [caller = Buyer or Seller]
                                                        ▼
                                                    RESOLVED
                                            (winner = SELLER | BUYER)
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for field-by-field
state details and how to extend the state machine.

## What consensus actually does

Handshake-style primitives on GenLayer earn their trust by being
explicit about what the model can and cannot influence. For the IEP:

- **Evidence is acquired, not trusted, per validator.** If
  `deliverable_locator` is a fetchable URI (`http://`, `https://`,
  `ipfs://`), every validator independently retrieves the actual
  referenced content via `gl.nondet.web.render(...)` and adjudicates
  *that*, rather than the Seller's own description of what the link
  contains. An `ipfs://` locator is normalized to a public gateway URL
  before retrieval; a failed fetch is replaced with a fixed placeholder
  that the adjudication prompt is told should favor the Buyer.
- **Sanitization is independent per validator**, and runs on the
  *acquired evidence* — fetched content or plain text, whichever it
  turned out to be — before it ever sees the acceptance criteria or the
  decision schema. An attacker can't target "the leader's sanitizer" or
  "the leader's fetch" alone.
- **Adjudication is independent per validator**, forced into a strict
  two-key JSON schema (`chain_of_thought`, `decision`).
- **Consensus is keyed on `decision` only.** The contract uses
  `gl.eq_principle.prompt_comparative(...)` with an explicit principle
  stating that `chain_of_thought` wording differences never block
  agreement — only the `decision` enum has to match.
- **The deterministic layer still gates the outcome.** A malformed or
  off-schema `decision` value fails the transaction rather than
  defaulting to a winner.

Full write-up, including the threat model, is in
[`docs/CONSENSUS.md`](docs/CONSENSUS.md).

## Security properties

- The Seller's `deliverable_locator` is never adjudicated at face value:
  if it's a URI, the contract fetches the real referenced content;
  either way, only the greybox-sanitized evidence reaches the
  adjudication prompt.
- Every fund-moving method (`approve`, `resolve_dispute`) is gated on
  `gl.message.sender_address`, never a caller-supplied argument.
- A malformed model response fails the transaction; it never falls back
  to a default winner.
- `resolve_dispute()` is only reachable from `DISPUTED`, which is only
  reachable from `DELIVERED`, which requires an actual submitted
  locator — there is no path to adjudicate an empty or missing
  deliverable.
- `_release_funds` is a documented no-op left for integrators to wire to
  their own asset layer, so this primitive makes no unaudited claims
  about a specific token mechanism.

## Repository layout

```
contracts/escrow.py                     Intelligent Contract
fixtures/                               Sample acceptance criteria + deliverable locators used in tests
scripts/local_helper_check.py           Deterministic structural checks without GenVM
scripts/preflight.py                    Submission invariant checks
scripts/deploy_studionet.sh             Minimal StudioNet deploy helper
tests/direct/                           Direct Mode state-machine + prompt-injection tests
tests/integration/                      Disposable StudioNet lifecycle proof
docs/ARCHITECTURE.md                    State machine and extension points
docs/CONSENSUS.md                       Equivalence design, greybox sanitization, threat model
SUBMISSION.md                           Reviewer-oriented submission notes
```

## Tests

Deterministic, no GenVM or LLM required:

```bash
python scripts/local_helper_check.py
python scripts/preflight.py
```

GenLayer Direct Mode suite:

```bash
python -m pip install -r requirements-test.txt
pytest tests/direct -q
```

The Direct Mode suite covers state-machine transitions, access control
on every write method, and a prompt-injection-resistance case built from
the `prompt_injection_in_fetched_content` and
`fabricated_description_contradicted_by_evidence` fixtures.

Disposable StudioNet lifecycle proof (real transactions — run
intentionally):

```bash
gltest --network studionet tests/integration/test_escrow_studionet.py -s
```

## Deployment

```bash
genlayer network set studionet
genlayer deploy --contract contracts/escrow.py
```

Or use the helper script:

```bash
./scripts/deploy_studionet.sh <buyer_address> <seller_address> <amount> "<acceptance_criteria>"
```

Deploy args:

| Field | Type | Example |
| --- | --- | --- |
| `buyer` | string (address) | `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266` |
| `seller` | string (address) | `0x70997970C51812dc3A010C7d01b50e0d17dc79C8` |
| `amount` | int | `100` |
| `acceptance_criteria` | string | `A vector graphic of a cyberpunk cat` |

Record the deployed contract address and transaction hash in
[`SUBMISSION.md`](SUBMISSION.md).

## Why this is a primitive, not an app

The IEP does not run a marketplace, host a dashboard, index disputes, or
manage multiple concurrent deals. It answers one reusable question per
deployed instance:
> **Given this brief and this deliverable, who should the escrowed funds go to?**

That decision can be consumed by freelance marketplaces, bounty boards,
generative-art commissions, or any other Intelligent Contract that needs
subjective adjudication without trusting a centralized arbitrator.

## License

MIT — see [`LICENSE`](LICENSE).
