# AGENTS.md — ProtoOS

This file is the contract for any AI coding agent working on this repository.

## What this project is

ProtoOS is a Unified Autonomous Protocols Operating System (reference implementation).
It is a policy-governed control plane that **composes** existing agent protocols —
MCP, A2A, AP2 mandates, x402, MPP, UCP/ACP-style commerce, AG-UI, ANP/DID-style identity —
into one environment where agents are built, discovered, coordinated, authorized, paid, and audited.

Pure Python 3.12 standard library (+ optional `cryptography` for Ed25519). Zero network required.

## How to run & verify

```bash
python3 -m unittest discover -s tests -v
python3 demo.py
python3 -m protoos.verify          # traceability + live smoke + constellation + vault
python3 -m protoos.graph out/      # constellation.{json,dot,svg}
python3 -m protoos.vault vault.zip # Obsidian vault
```

## Hard rules for agents

1. Never break the verify contract (`python3 -m protoos.verify` and the 95 tests must stay green).
2. Fail closed — policy engine, mandate chain verification, and hash-chained audit stay hard.
3. Compose, don't replace — no new wire protocols; adapters only.
4. Keep the offline path fully functional (no network egress required for core tests).
5. Prefer small, focused changes. Update README.md, AGENTS.md, and traceability.json when public surfaces or requirements change.
6. Do not weaken kill switches, rate limits, budget controls, or human-in-the-loop (`require_approval`).

## Surfaces that must stay working

- PolicyEngine + MandateStore (AP2 Intent→Cart→Payment)
- Identity (DID, VC, token exchange)
- Wallet / multi-rail spending (x402, MPP, traditional)
- MCP (server/client, paid tools, OpenAPI→MCP, mux, cache)
- A2A task lifecycle + AG-UI event bus
- Registry (local/federated/well-known + semantic index)
- Orchestration (delegate, budgets, TaskGraph)
- Constellation graph + Obsidian vault
- Hash-chained audit + integrity verification
- Kubernetes CRD shapes in `deploy/k8s/`
