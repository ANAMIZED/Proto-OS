# ProtoOS v0.2.0 — Unified Autonomous Protocols Operating System

[![CI](https://github.com/ANAMIZED/ProtoOS/actions/workflows/ci.yml/badge.svg)](https://github.com/ANAMIZED/ProtoOS/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-95%20OK-brightgreen.svg)](TEST_REPORT.txt)
[![Requirements](https://img.shields.io/badge/requirements-53%2F53-brightgreen.svg)](VERIFICATION.md)

**Reference implementation** of a policy-governed control plane that **composes** existing agent protocols — MCP, A2A, AP2 mandates, x402, MPP, UCP/ACP-style commerce, AG-UI, ANP/DID-style identity — into one environment where agents are built, discovered, coordinated, authorized, paid, and audited.

Pure Python 3.12 standard library (+ optional `cryptography` for Ed25519, with OS-verified HMAC fallback). Zero network required.

*Related:* [OpenMesha](https://github.com/ANAMIZED/OpenMesha) · [rui](https://github.com/ANAMIZED/rui) · [server-os](https://github.com/ANAMIZED/server-os)

## New in 0.2.0 — Constellation & Obsidian vault

The world is now a first-class graph, at parity with the web console's Constellation tab.

- `protoos.graph.build_graph(os)` derives the live object graph — principals, budgets, MCP servers/tools, AP2 mandate chains, receipts, tasks, pending approvals — with the same node-type/edge-kind vocabulary as the browser build (parity-checked: **MATCH**).
- `protoos.graph.layout(graph, seed=…)` is a deterministic force layout: identical worlds and seeds produce identical constellations. Exports: `to_json`, `to_dot` (Graphviz), `to_svg` (standalone snapshot in the ledger palette).
- `protoos.vault.write_vault[_zip](os, dest)` writes the world as an Obsidian vault: every identity, budget, mandate, receipt, and task becomes a wikilinked markdown note; policy rules/decisions, the hash-chained audit table, and the AG-UI feed become tables. `unresolved_links()` proves every `[[wikilink]]` resolves.
- Hardening found by the new demo world: `AuditLog.append` now **deep-copies payloads**, closing an aliasing hole where a caller mutating a dict it had logged could retroactively break the hash chain. `TraditionalRail` now retains receipts like the other rails.

```bash
python3 -m protoos.graph out/        # constellation.{json,dot,svg}
python3 -m protoos.vault vault.zip   # Obsidian vault (or a directory path)
python3 demo.py                      # now also writes both artifacts
```

## Quickstart

```bash
python3 -m unittest discover -s tests   # 95 tests
python3 demo.py                          # end-to-end scenario
python3 -m protoos.verify                # traceability audit + live smoke
```

```python
from protoos import ProtoOS, Catalog

os_ = ProtoOS()
os_.engine.add_rule("user", "allow", ["payment.settle"], "amount <= 200")
os_.engine.add_rule("org", "require_approval", ["payment.settle"], "amount > 50")

casey  = os_.create_user("casey")
shop   = os_.create_merchant("shop")
budget = os_.wallet.create_budget(casey.did, 500.0, window=(300.0, 86400))

catalog = Catalog(shop.did, "shop")
catalog.add("bk1", "Distributed Systems 101", 10.00, "USD", "digital")

receipt = os_.purchase(casey.did, catalog, [{"sku": "bk1", "qty": 2}],
                       intent_text="buy two intro ebooks", max_amount=100,
                       budget_id=budget.id, categories=["digital"])
# Intent Mandate -> checkout -> Cart Mandate -> Payment Mandate
# -> policy + budget -> x402 settle -> hash-chained audit
```

## Spec → module map

| Spec box | Module |
|---|---|
| Policy Engine + Mandate Store | `protoos/policy.py` |
| Orchestrator / Task Graph | `protoos/runtime.py`, `protoos/core.py` |
| Identity & Credential Service | `protoos/identity.py` |
| Discovery & Registry | `protoos/registry.py` |
| Observability & Audit | `protoos/audit.py` |
| Wallet / Spending Controller | `protoos/wallet.py` |
| MCP adapter (+OpenAPI→MCP, federation, cache) | `protoos/mcp.py` |
| A2A adapter + AG-UI event bus | `protoos/a2a.py` |
| UCP/ACP-style commerce | `protoos/commerce.py` |
| HTTP/JSON-RPC + SSE transport | `protoos/httpapi.py` |
| Control-plane facade (`ProtoOS`) | `protoos/core.py` |
| Constellation graph | `protoos/graph.py` |
| Obsidian vault export | `protoos/vault.py` |
| Kubernetes CRDs + Deployment | `deploy/k8s/` |
| Requirement audit | `traceability.json`, `VERIFICATION.md`, `protoos/verify.py` |

## What "reference implementation" means here

Every protocol surface named by the spec is **working and tested in-process**:
JSON-RPC MCP with paid tools, the A2A task lifecycle, the full AP2
Intent→Cart→Payment mandate chain, x402 challenge/settle with an in-process
facilitator, MPP prepaid sessions, AG-UI event streams over SSE, DID
documents and well-known publication. This sandbox has **no network egress,
no Kubernetes cluster, and no external SDKs**, so anything that requires the
open internet (live did:web resolution, real crypto/banking settlement,
certified conformance against published external specs) is implemented against
local/loopback equivalents and explicitly marked `partial` or `deferred` in
`traceability.json` — nothing is silently omitted.

## Production hardening path

1. **Rust control plane (X1):** module boundaries here mirror the intended services (policy, mandates, wallet, registry, transport); the Python build is the executable specification and test oracle for the port.
2. **Storage (X3):** in-memory dicts + JSONL exports are isolated per subsystem — swap for etcd/Postgres (control state), object storage (manifests), and a vector DB behind `SemanticIndex`.
3. **Rails (M1/X6):** `X402Rail`/`MPPRail`/`TraditionalRail` keep the authorize/settle seams where official SDKs slot in.
4. **Transports (X4/X5):** loopback HTTP+SSE ships; add gRPC/QUIC listeners beside `httpapi.py`.
5. **Sandboxing (G4):** replace `SandboxedExecutor` with container/microVM isolation in the agent runtime.

## Design principles

1. Compose, don't replace
2. Policy-first autonomy (every sensitive action gated)
3. Cryptographic mandates + hash-chained audit
4. Human-in-the-loop as a first-class primitive
5. Multi-rail everything (tools, messaging, payments, identity)
6. Offline-first reference with honest partial/deferred markers

## License

Apache-2.0. Governance charter draft: [`GOVERNANCE.md`](GOVERNANCE.md).
