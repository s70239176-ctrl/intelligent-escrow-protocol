# Custody and Settlement

This document covers how the IEP actually holds and moves funds, and a
known, currently-unresolved platform risk that affects whether payouts
land on-chain today. Read this before deploying with real value.

## Custody model

Deploying the contract does **not** move any funds. Custody is a
separate, explicit step:

1. **Deploy** with `buyer`, `seller`, `amount` (the required escrow
   amount in wei), `acceptance_criteria`, and `delivery_window_seconds`
   (how long the Seller has to deliver once funded).
2. **Buyer calls `fund()`** — a `@gl.public.write.payable` method — and
   sends exactly `amount` in native GEN with that call.
   `gl.message.value` is checked against `self.amount`; a mismatch
   reverts the transaction (standard EVM-equivalent semantics: a
   reverted payable call does not transfer value).
3. Funding starts the delivery-window clock: `fund()` reads
   `gl.message.datetime` (the consensus transaction timestamp, not a
   per-validator wall clock) and stores `delivery_deadline =
   now + delivery_window_seconds`.
4. `submit_deliverable()` now requires `self.funded == True` — the
   Seller cannot be asked to deliver against an unfunded escrow.
5. Settlement happens through exactly one of three paths, each of which
   calls the same internal `_pay_out()`:
   - `approve()` → pays the Seller.
   - `resolve_dispute()` → pays whichever party the LLM-consensus
     adjudication decided.
   - `claim_timeout_refund()` → pays the Buyer back if the Seller never
     submitted a deliverable before `delivery_deadline`.
6. `_pay_out()` sets `funds_released = True` before transferring, and
   every settlement path checks `funds_released` first — funds can only
   leave the contract once, ever, for a given escrow instance.

## The actual transfer mechanism

```python
gl.ContractAt(recipient).emit_transfer(value=self.amount)
```

This is GenLayer's documented pattern for sending native GEN to another
contract or an externally-owned account (EOA) — confirmed against
GenLayer's own "Working with Balances" documentation, not inferred.

## Anti-lockup: `claim_timeout_refund()`

The specific failure mode this closes: **the Seller never delivers, and
funds sit in the contract forever with no way out.** Either party may
call `claim_timeout_refund()` once `gl.message.datetime` (parsed) is
past `delivery_deadline`, provided the escrow is still `PENDING`
(i.e. no deliverable was ever submitted). This pays the full amount back
to the Buyer and moves the escrow to a terminal `REFUNDED` state.

This does **not** cover every conceivable stuck-funds scenario. Two
cases are handled differently, deliberately:

- **Seller delivers, Buyer goes silent (neither approves nor
  disputes).** No new mechanism is needed here: `dispute()` and
  `resolve_dispute()` are both callable by *either* party, so the
  Seller can force adjudication themselves rather than waiting on the
  Buyer indefinitely.
- **A dispute is opened but `resolve_dispute()` keeps failing** (e.g.
  the model returns malformed JSON, tripping the deterministic
  `decision != "SELLER" and decision != "BUYER"` check). The
  transaction simply reverts and no state changes — the dispute remains
  open and retryable. This is not a lock, just a failed attempt; either
  party can call `resolve_dispute()` again.

If you need a stronger guarantee for the `resolve_dispute()`-keeps-
failing case (e.g. a maximum retry count before an automatic default
outcome), that is a reasonable extension not implemented here — see
"Extending This Primitive" in `docs/ARCHITECTURE.md`.

## Known platform-level risk: emitted transfers may not execute

**This is the most important thing in this document.** As of this
writing, there is a confirmed, publicly filed GenLayer platform issue —
[`genlayerlabs/genvm-manager#20`](https://github.com/genlayerlabs/genvm-manager/issues/20)
— reporting that emitted/asynchronous messages, **including
`emit_transfer` calls**, are recorded in the transaction but never
actually executed on the current Asimov/Bradbury testnet (chain id
4221). Independent community projects building GenLayer escrow/payout
contracts have hit and documented the same issue: correctly-written
`emit_transfer` code that follows the exact documented pattern, with
fully-verified gating logic, still did not deliver value on that
testnet at the time they tested it.

**What this means concretely:**

- The gating logic in this contract (who is allowed to call what, when,
  and the deterministic checks around funding/settlement) can be fully
  verified through GenVM Direct Mode / `gltest` without ever hitting
  this issue, because Direct Mode does not simulate value transfer at
  all -- it exercises the state machine, not fund movement.
- The actual `_pay_out()` transfer can **only** be verified by watching
  real GEN balances change on a live network (Studio, localnet, or a
  testnet) after a real settlement call.
- If you deploy this to a network affected by the linked issue, the
  contract may report `funds_released: true` (the internal flag is set
  correctly, and correctly prevents double-payout) while the recipient
  never actually receives the GEN -- because the flag reflects "we
  issued the transfer instruction," not "the transfer was confirmed to
  land."

**Before trusting this contract with real value:**

1. Check the linked issue for its current status -- it may have been
   fixed since this was written.
2. Test the full fund → settle → balance-check cycle on your target
   network (localnet is the safest place to start) and confirm the
   recipient's balance actually increases.
3. If transfers are not landing on your target network, that is a
   platform-level limitation, not a bug in this contract's logic --
   the `resolve_dispute()` / `approve()` / `claim_timeout_refund()`
   decision-making is independently correct and verifiable even while
   this issue is open.

## If you'd rather not carry this risk at all

If verifying real value transfer on your target network isn't practical
right now, or if the linked platform issue is still open, the
alternative is to run this primitive in **decision-only mode**: keep
`fund()` / `_pay_out()` in the contract for when the platform issue is
resolved, but treat `get_resolution()` as the actual deliverable -- an
authoritative, LLM-consensus-adjudicated `SELLER`/`BUYER` decision that
an off-chain process or a separate, already-verified payment rail acts
on. That reframing requires no code change; it's a statement about which
part of the contract you're relying on today.
