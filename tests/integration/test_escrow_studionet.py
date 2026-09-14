"""
tests/integration/test_escrow_studionet.py

Disposable StudioNet lifecycle test. Unlike tests/direct/, this performs
REAL transactions against a live GenLayer StudioNet deployment, including
real (testnet) LLM-backed consensus calls AND real value transfer. Run
this intentionally, not on every commit:

    gltest --network studionet tests/integration/test_escrow_studionet.py -s

This is a stub -- fill in the deployment and account wiring for your
`gltest` / GenLayer SDK version before relying on it. The point of this
file is to prove the FULL lifecycle end-to-end on a live network at
least once before submission, matching the "Verified deployment"
evidence recorded in SUBMISSION.md.

IMPORTANT: see docs/CUSTODY.md for a confirmed, publicly filed GenLayer
platform issue (genlayerlabs/genvm-manager#20) under which
`emit_transfer` may be recorded but not actually executed on some
networks. The balance assertions below are the ONLY place in this
repository that can actually catch that -- tests/direct/ cannot, because
Direct Mode does not simulate value transfer at all. If these balance
assertions fail while every other assertion passes, that is evidence of
the platform issue, not a bug in this contract's logic.
"""

import pytest

ESCROW_AMOUNT = 100
DELIVERY_WINDOW_SECONDS = 7 * 24 * 60 * 60  # 7 days


@pytest.mark.integration
def test_full_lifecycle_happy_path(studionet_client):
    """
    Deploys a fresh escrow, funds it, submits a deliverable, and
    approves it -- the manual, non-adversarial path. No LLM call should
    occur. Confirms the Seller's real GEN balance actually increases.
    """
    seller_balance_before = studionet_client.get_balance(studionet_client.accounts.seller)

    escrow = studionet_client.deploy(
        "contracts/escrow.py",
        args={
            "buyer": studionet_client.accounts.buyer,
            "seller": studionet_client.accounts.seller,
            "amount": ESCROW_AMOUNT,
            "acceptance_criteria": "A vector graphic of a cyberpunk cat",
            "delivery_window_seconds": DELIVERY_WINDOW_SECONDS,
        },
    )

    studionet_client.as_account(studionet_client.accounts.buyer).call(
        escrow, "fund", value=ESCROW_AMOUNT
    )
    assert studionet_client.view(escrow, "get_custody_status")["funded"] is True

    studionet_client.as_account(studionet_client.accounts.seller).call(
        escrow, "submit_deliverable", deliverable_locator="ipfs://Qm.../cat.svg"
    )
    studionet_client.as_account(studionet_client.accounts.buyer).call(escrow, "approve")

    resolution = studionet_client.view(escrow, "get_resolution")
    assert resolution["status"] == "RESOLVED"
    assert resolution["winner"] == "SELLER"

    # The assertion that actually matters for custody, not just state:
    seller_balance_after = studionet_client.get_balance(studionet_client.accounts.seller)
    assert seller_balance_after == seller_balance_before + ESCROW_AMOUNT, (
        "Contract state says RESOLVED/SELLER, but the Seller's real GEN "
        "balance did not increase by the escrowed amount -- see "
        "docs/CUSTODY.md re: genlayerlabs/genvm-manager#20."
    )


@pytest.mark.integration
def test_full_lifecycle_disputed_path(studionet_client):
    """
    Deploys a fresh escrow, funds it, submits a deliverable, disputes
    it, and resolves it via real LLM-backed consensus. Record the
    resulting contract address, transaction hashes, and observed
    balance change in SUBMISSION.md.
    """
    escrow = studionet_client.deploy(
        "contracts/escrow.py",
        args={
            "buyer": studionet_client.accounts.buyer,
            "seller": studionet_client.accounts.seller,
            "amount": ESCROW_AMOUNT,
            "acceptance_criteria": "A 500-word essay on decentralized identity",
            "delivery_window_seconds": DELIVERY_WINDOW_SECONDS,
        },
    )

    studionet_client.as_account(studionet_client.accounts.buyer).call(
        escrow, "fund", value=ESCROW_AMOUNT
    )

    balances_before = {
        "buyer": studionet_client.get_balance(studionet_client.accounts.buyer),
        "seller": studionet_client.get_balance(studionet_client.accounts.seller),
    }

    studionet_client.as_account(studionet_client.accounts.seller).call(
        escrow, "submit_deliverable", deliverable_locator="ipfs://Qm.../unrelated_photo.jpg"
    )
    studionet_client.as_account(studionet_client.accounts.buyer).call(escrow, "dispute")
    studionet_client.as_account(studionet_client.accounts.buyer).call(escrow, "resolve_dispute")

    resolution = studionet_client.view(escrow, "get_resolution")
    assert resolution["status"] == "RESOLVED"
    assert resolution["winner"] in ("SELLER", "BUYER")
    assert resolution["reasoning"] != ""

    winner_key = resolution["winner"].lower()
    balance_after = studionet_client.get_balance(
        getattr(studionet_client.accounts, winner_key)
    )
    assert balance_after == balances_before[winner_key] + ESCROW_AMOUNT, (
        f"Contract state says winner={resolution['winner']}, but that "
        "party's real GEN balance did not increase -- see "
        "docs/CUSTODY.md re: genlayerlabs/genvm-manager#20."
    )


@pytest.mark.integration
def test_timeout_refund_returns_funds_to_buyer(studionet_client):
    """
    Deploys and funds an escrow, lets the delivery window lapse without
    the Seller ever submitting, and confirms claim_timeout_refund()
    actually returns GEN to the Buyer. Requires a short delivery window
    and either waiting it out or your harness's time-control fixture.
    """
    short_window_seconds = 5

    buyer_balance_before = studionet_client.get_balance(studionet_client.accounts.buyer)

    escrow = studionet_client.deploy(
        "contracts/escrow.py",
        args={
            "buyer": studionet_client.accounts.buyer,
            "seller": studionet_client.accounts.seller,
            "amount": ESCROW_AMOUNT,
            "acceptance_criteria": "Anything",
            "delivery_window_seconds": short_window_seconds,
        },
    )
    studionet_client.as_account(studionet_client.accounts.buyer).call(
        escrow, "fund", value=ESCROW_AMOUNT
    )

    studionet_client.wait_seconds(short_window_seconds + 2)

    studionet_client.as_account(studionet_client.accounts.buyer).call(
        escrow, "claim_timeout_refund"
    )

    resolution = studionet_client.view(escrow, "get_resolution")
    assert resolution["status"] == "REFUNDED"

    buyer_balance_after = studionet_client.get_balance(studionet_client.accounts.buyer)
    assert buyer_balance_after == buyer_balance_before, (
        "Contract state says REFUNDED, but the Buyer's net GEN balance "
        "(accounting for gas) did not reflect the refund -- see "
        "docs/CUSTODY.md re: genlayerlabs/genvm-manager#20."
    )
