# Deployment Notes

Fill in the specifics for your GenLayer Studio / testnet environment.

## Local simulator

1. Install the GenLayer CLI / Studio per the official GenLayer docs.
2. Point the simulator at `contracts/escrow.py`.
3. Deploy with constructor args:
   ```
   buyer=<address>, seller=<address>, amount=<int>, acceptance_criteria=<str>
   ```

## Testnet

1. Configure your GenLayer testnet RPC endpoint and funded deployer key.
2. Deploy `IntelligentEscrowProtocol` with the same constructor args.
3. Record the deployed contract address for Buyer/Seller integration.

## Wiring the asset layer

`_release_funds` in `escrow.py` is intentionally left abstract. Replace
the `pass` statement with your project's native transfer primitive
(e.g. a `gl.transfer(recipient, amount)` call, or an external ERC-20
`transferFrom` if funds are held outside the contract) before deploying
to mainnet.
