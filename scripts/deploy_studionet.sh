#!/usr/bin/env bash
# scripts/deploy_studionet.sh
#
# Minimal StudioNet deploy + fund helper for the Intelligent Escrow
# Protocol. Requires the GenLayer CLI to be installed and authenticated.
# Deployment does NOT move funds -- funding is a separate, explicit
# `fund` call the Buyer must make afterward. See docs/CUSTODY.md before
# relying on real value transfer.
#
# Usage:
#   ./scripts/deploy_studionet.sh <buyer_address> <seller_address> <amount> <delivery_window_seconds> <acceptance_criteria>
#
# Example (100 wei escrow, 7-day delivery window):
#   ./scripts/deploy_studionet.sh \
#     0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 \
#     0x70997970C51812dc3A010C7d01b50e0d17dc79C8 \
#     100 \
#     604800 \
#     "A vector graphic of a cyberpunk cat"

set -euo pipefail

if [ "$#" -ne 5 ]; then
  echo "Usage: $0 <buyer_address> <seller_address> <amount> <delivery_window_seconds> <acceptance_criteria>"
  exit 1
fi

BUYER="$1"
SELLER="$2"
AMOUNT="$3"
DELIVERY_WINDOW_SECONDS="$4"
CRITERIA="$5"

echo "==> Selecting StudioNet"
genlayer network set studionet

echo "==> Deploying Intelligent Escrow Protocol (unfunded)"
genlayer deploy \
  --contract contracts/escrow.py \
  --args "{\"buyer\": \"${BUYER}\", \"seller\": \"${SELLER}\", \"amount\": ${AMOUNT}, \"acceptance_criteria\": \"${CRITERIA}\", \"delivery_window_seconds\": ${DELIVERY_WINDOW_SECONDS}}"

echo "==> Deploy complete. Record the printed contract address and transaction hash in SUBMISSION.md."
echo
echo "==> Next step (run as the Buyer account, separately):"
echo "    genlayer call --contract <deployed_address> --method fund --value ${AMOUNT}"
echo
echo "==> Before trusting this with real value, read docs/CUSTODY.md --"
echo "    there is a known, currently-open GenLayer platform issue"
echo "    (genlayerlabs/genvm-manager#20) that can affect whether"
echo "    emit_transfer payouts actually land on some networks."
