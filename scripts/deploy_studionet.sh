#!/usr/bin/env bash
# scripts/deploy_studionet.sh
#
# Minimal StudioNet deploy helper for the Intelligent Escrow Protocol.
# Requires the GenLayer CLI to be installed and authenticated.
#
# Usage:
#   ./scripts/deploy_studionet.sh <buyer_address> <seller_address> <amount> <acceptance_criteria>
#
# Example:
#   ./scripts/deploy_studionet.sh \
#     0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 \
#     0x70997970C51812dc3A010C7d01b50e0d17dc79C8 \
#     100 \
#     "A vector graphic of a cyberpunk cat"

set -euo pipefail

if [ "$#" -ne 4 ]; then
  echo "Usage: $0 <buyer_address> <seller_address> <amount> <acceptance_criteria>"
  exit 1
fi

BUYER="$1"
SELLER="$2"
AMOUNT="$3"
CRITERIA="$4"

echo "==> Selecting StudioNet"
genlayer network set studionet

echo "==> Deploying Intelligent Escrow Protocol"
genlayer deploy \
  --contract contracts/escrow.py \
  --args "{\"buyer\": \"${BUYER}\", \"seller\": \"${SELLER}\", \"amount\": ${AMOUNT}, \"acceptance_criteria\": \"${CRITERIA}\"}"

echo "==> Deploy complete. Record the printed contract address and transaction hash in SUBMISSION.md."
