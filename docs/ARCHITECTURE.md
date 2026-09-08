# Architecture: State Machine and Extension Points

This document covers the IEP's state machine and how to extend the
primitive. For the consensus/equivalence design (how validators reach
agreement on a subjective decision) and the prompt-injection defense,
see [`docs/CONSENSUS.md`](CONSENSUS.md).

## The State Machine

```
        submit_deliverable(payload)      [caller must be Seller]
PENDING ─────────────────────────────► DELIVERED
                                            │  │
                        approve()           │  │ dispute()
                    [caller = Buyer]        │  │ [caller = Buyer or Seller]
                        ┌───────────────────┘  │
                        ▼                      ▼
                    RESOLVED               DISPUTED
                (winner = SELLER)              │
                                                │ resolve_dispute()
                                                │ [caller = Buyer or Seller]
                                                ▼
                                            RESOLVED
                                    (winner = SELLER | BUYER)
```

- **PENDING** — funds are locked, contract is waiting for the Seller.
- **DELIVERED** — a payload has been submitted; the Buyer has a manual
  window to approve without ever invoking the LLM.
- **DISPUTED** — either party has escalated; the only way out is
  LLM-adjudicated resolution.
- **RESOLVED** — terminal. `winner` and `resolution_reasoning` are fixed.

Every transition is gated on both the caller's identity — read from
`gl.message.sender_address`, never a caller-supplied argument, so it
cannot be spoofed — and the current `status`, so the state machine
cannot be skipped or re-entered out of order.

## State Fields

| Field | Type | Meaning |
| --- | --- | --- |
| `buyer` | `Address` | Party who funded the escrow. |
| `seller` | `Address` | Party expected to deliver the work. |
| `amount` | `u256` | Escrowed amount. |
| `acceptance_criteria` | `str` | Plain-text brief agreed on before delivery. Immutable after construction. |
| `deliverable_payload` | `str` | Set once, by the Seller, via `submit_deliverable`. |
| `status` | `str` | One of `PENDING`, `DELIVERED`, `DISPUTED`, `RESOLVED`. |
| `winner` | `str` | `""` until resolution; then `"SELLER"` or `"BUYER"`. |
| `resolution_reasoning` | `str` | Human-readable justification -- either a fixed string for manual approval, or the adjudicator's `chain_of_thought` for a disputed resolution. |

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
- **Cross-contract consumption** — expose an `IIntelligentEscrow`
  `@gl.contract_interface` (see the Handshake primitive's `IHandshake`
  pattern) so marketplaces or routers can query `get_status()` /
  `get_resolution()` from other contracts without trusting an off-chain
  indexer.
