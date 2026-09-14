# Architecture: State Machine and Extension Points

This document covers the IEP's state machine and how to extend the
primitive. For the consensus/equivalence design (how validators reach
agreement on a subjective decision) and the prompt-injection defense,
see [`docs/CONSENSUS.md`](CONSENSUS.md). For how funds actually move
and a known platform-level risk affecting real payouts, see
[`docs/CUSTODY.md`](CUSTODY.md).

## The State Machine

```
   fund()               submit_deliverable(deliverable_locator)
[caller = Buyer]              [caller must be Seller]
     │                              │
     ▼                              ▼
PENDING (unfunded) ──► PENDING (funded) ─────────────► DELIVERED
                              │                            │  │
              claim_timeout_refund()      approve()        │  │ dispute()
              [caller = Buyer or          [caller = Buyer] │  │ [caller = Buyer or Seller]
               Seller, after deadline]          ┌──────────┘  │
                              │                  ▼             ▼
                              ▼              RESOLVED      DISPUTED
                          REFUNDED       (winner = SELLER)     │
                      (funds → Buyer)                          │ resolve_dispute()
                                                                │ [caller = Buyer or Seller]
                                                                ▼
                                                            RESOLVED
                                                    (winner = SELLER | BUYER,
                                                     funds → winner)
```

- **PENDING (unfunded)** — contract deployed, no funds held yet.
- **PENDING (funded)** — Buyer has called `fund()`; the delivery-window
  clock is running; contract holds the escrowed amount.
- **DELIVERED** — a locator has been submitted; the Buyer has a manual
  window to approve without ever invoking the LLM.
- **DISPUTED** — either party has escalated; the only way out is
  LLM-adjudicated resolution.
- **RESOLVED** — terminal. `winner` and `resolution_reasoning` are
  fixed; funds have been paid out to the winner.
- **REFUNDED** — terminal. Reached only via `claim_timeout_refund()`
  when the Seller never delivered before the deadline; funds returned
  to the Buyer.

Every transition is gated on both the caller's identity — read from
`gl.message.sender_address`, never a caller-supplied argument, so it
cannot be spoofed — and the current `status`/`funded` flags, so the
state machine cannot be skipped or re-entered out of order. `funds_released`
additionally guards every payout path so a given escrow instance can
only pay out once, ever, regardless of which path it exits through.

## State Fields

| Field | Type | Meaning |
| --- | --- | --- |
| `buyer` | `Address` | Party who funds and may approve/dispute the escrow. |
| `seller` | `Address` | Party expected to deliver the work. |
| `amount` | `u256` | Required escrow amount, in wei. `fund()` requires an exact match against `gl.message.value`. |
| `acceptance_criteria` | `str` | Plain-text brief agreed on before delivery. Immutable after construction. |
| `deliverable_locator` | `str` | Set once, by the Seller, via `submit_deliverable`. Either a fetchable URI (`http://`, `https://`, `ipfs://`) or freeform text; never trusted at face value -- see `docs/CONSENSUS.md` for how it's resolved into evidence at adjudication time. |
| `status` | `str` | One of `PENDING`, `DELIVERED`, `DISPUTED`, `RESOLVED`, `REFUNDED`. |
| `winner` | `str` | `""` until resolution; then `"SELLER"` or `"BUYER"`. Stays `""` for a `REFUNDED` outcome. |
| `resolution_reasoning` | `str` | Human-readable justification -- a fixed string for manual approval or timeout refund, or the adjudicator's `chain_of_thought` for a disputed resolution. |
| `funded` | `bool` | Set once `fund()` succeeds. `submit_deliverable` requires this to be `True`. |
| `funds_released` | `bool` | Set the moment any payout path (`approve`, `resolve_dispute`, `claim_timeout_refund`) issues its transfer. Prevents double payout. |
| `delivery_window_seconds` | `u256` | Constructor parameter: how long, from `fund()`, the Seller has to deliver. |
| `delivery_deadline` | `str` | ISO timestamp computed at `fund()` time from `gl.message.datetime + delivery_window_seconds`. |

## Why `approve()` Bypasses the LLM Entirely

Most escrow interactions are not adversarial: the Buyer is satisfied and
just wants funds released. Routing every delivery through LLM
adjudication would add unnecessary consensus overhead and unnecessary
non-determinism to the common case. `approve()` is a pure, deterministic
state transition — no `gl.nondet` call, no consensus round beyond the
normal transaction consensus every GenLayer write already requires.

The LLM path is reserved for exactly the case it exists to solve:
`dispute()` followed by `resolve_dispute()`, when the parties actually
disagree about whether the work meets the brief.

## Why `claim_timeout_refund()` Exists

Without it, a Seller who simply never delivers leaves the escrow stuck
in `PENDING (funded)` forever — there is no other transition out of
that state, since both `approve()` and `dispute()` require `DELIVERED`.
`claim_timeout_refund()` is the deliberate escape hatch: once
`gl.message.datetime` is past `delivery_deadline`, either party can
close the escrow and return funds to the Buyer. See
[`docs/CUSTODY.md`](CUSTODY.md) for which other stuck-state scenarios
are and aren't covered, and why.

## Extending This Primitive

Common extensions builders add on top of the IEP:

- **Multi-milestone escrow** — chain multiple `DELIVERED → RESOLVED`
  cycles with partial fund release per milestone.
- **Appeal windows** — add a `CHALLENGED` state that allows one
  re-adjudication with an expanded prompt (e.g. including counter-arguments
  submitted by the losing party).
- **Evidence attachments** — extend `submit_deliverable` to accept
  multiple IPFS references, each greybox-sanitized independently before
  being concatenated into the adjudication prompt.
- **Reputation weighting** — emit `resolution_reasoning` to an off-chain
  indexer to build Seller/Buyer reputation scores over time.
- **A resolve-retry cap** — if `resolve_dispute()` keeps failing (e.g.
  persistently malformed model output), add a retry counter and an
  automatic default outcome (e.g. refund the Buyer) once a cap is hit,
  rather than leaving the dispute open indefinitely.
- **Cross-contract consumption** — expose an `IIntelligentEscrow`
  `@gl.contract_interface` (see the Handshake primitive's `IHandshake`
  pattern) so marketplaces or routers can query `get_status()` /
  `get_resolution()` from other contracts without trusting an off-chain
  indexer.
