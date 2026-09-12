"""
tests/integration/test_escrow_studionet.py

Disposable StudioNet lifecycle test. Unlike tests/direct/, this performs
REAL transactions against a live GenLayer StudioNet deployment, including
real (testnet) LLM-backed consensus calls. Run this intentionally, not on
every commit:

    gltest --network studionet tests/integration/test_escrow_studionet.py -s

This is a stub -- fill in the deployment and account wiring for your
`gltest` / GenLayer SDK version before relying on it. The point of this
file is to prove the FULL lifecycle end-to-end on a live network at least
once before submission, matching the "Verified deployment" evidence
recorded in SUBMISSION.md.
"""

import pytest


@pytest.mark.integration
def test_full_lifecycle_happy_path(studionet_client):
    """
    Deploys a fresh escrow, submits a deliverable, and approves it --
    the manual, non-adversarial path. No LLM call should occur.
    """
    escrow = studionet_client.deploy(
        "contracts/escrow.py",
        args={
            "buyer": studionet_client.accounts.buyer,
            "seller": studionet_client.accounts.seller,
            "amount": 100,
            "acceptance_criteria": "A vector graphic of a cyberpunk cat",
        },
    )

    studionet_client.as_account(studionet_client.accounts.seller).call(
        escrow, "submit_deliverable", deliverable_locator="ipfs://Qm.../cat.svg"
    )
    studionet_client.as_account(studionet_client.accounts.buyer).call(escrow, "approve")

    resolution = studionet_client.view(escrow, "get_resolution")
    assert resolution["status"] == "RESOLVED"
    assert resolution["winner"] == "SELLER"


@pytest.mark.integration
def test_full_lifecycle_disputed_path(studionet_client):
    """
    Deploys a fresh escrow, submits a deliverable, disputes it, and
    resolves it via real LLM-backed consensus. Record the resulting
    contract address and transaction hashes in SUBMISSION.md.
    """
    escrow = studionet_client.deploy(
        "contracts/escrow.py",
        args={
            "buyer": studionet_client.accounts.buyer,
            "seller": studionet_client.accounts.seller,
            "amount": 100,
            "acceptance_criteria": "A 500-word essay on decentralized identity",
        },
    )

    studionet_client.as_account(studionet_client.accounts.seller).call(
        escrow, "submit_deliverable", deliverable_locator="ipfs://Qm.../unrelated_photo.jpg"
    )
    studionet_client.as_account(studionet_client.accounts.buyer).call(escrow, "dispute")
    studionet_client.as_account(studionet_client.accounts.buyer).call(escrow, "resolve_dispute")

    resolution = studionet_client.view(escrow, "get_resolution")
    assert resolution["status"] == "RESOLVED"
    assert resolution["winner"] in ("SELLER", "BUYER")
    assert resolution["reasoning"] != ""
