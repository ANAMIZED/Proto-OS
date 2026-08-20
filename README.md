# ProtoOS v0.2.0 — Unified Autonomous Protocols Operating System

[![CI](https://github.com/ANAMIZED/Proto-OS/actions/workflows/ci.yml/badge.svg)](https://github.com/ANAMIZED/Proto-OS/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-95%20OK-brightgreen.svg)](TEST_REPORT.txt)
[![Requirements](https://img.shields.io/badge/requirements-53%2F53-brightgreen.svg)](VERIFICATION.md)
[![MCP](https://img.shields.io/badge/MCP-server-purple.svg)](protoos/mcp.py)
[![SDK](https://img.shields.io/badge/SDK-Python-green.svg)](protoos/sdk/)
[![CLI](https://img.shields.io/badge/CLI-protoos-orange.svg)](protoos/cli.py)
[![API](https://img.shields.io/badge/API-HTTP%2FJSON--RPC%2BSSE-009688.svg)](protoos/httpapi.py)
[![x402](https://img.shields.io/badge/x402-commerce-green.svg)](protoos/wallet.py)

**Reference implementation** of a policy-governed control plane that **composes** existing agent protocols — MCP, A2A, AP2 mandates, x402, MPP, UCP/ACP-style commerce, AG-UI, ANP/DID-style identity — into one environment where agents are built, discovered, coordinated, authorized, paid, and audited.

Pure Python 3.12 standard library (+ optional `cryptography` for Ed25519, with OS-verified HMAC fallback). Zero network required.

*Related:* [OpenMesha](https://github.com/ANAMIZED/OpenMesha) · [rui](https://github.com/ANAMIZED/rui) · [server-os](https://github.com/ANAMIZED/server-os)

## Surfaces

| Surface | Entry |
|---------|-------|
| **CLI** | `protoos status` · `protoos verify` · `protoos graph` · `protoos vault` |
| **SDK** | `from protoos.sdk import ProtoOSClient` |
| **MCP Server** | `protoos-mcp` / `protoos/mcp.py` (JSON-RPC, paid tools, mux, OpenAPI→MCP) |
| **HTTP/JSON-RPC + SSE** | `protoos/httpapi.py` (`/mcp`, `/a2a`, `/agui/<run>`, `/.well-known/agents`) |
| **Multi-agent workflows** | discovery + budgeted `delegate` + TaskGraph + AG-UI |
| **Skills** | `skills/*/SKILL.md` (policy, x402, multi-agent, constellation, mcp) |
| **Constellation + Vault** | `python -m protoos.graph` · `python -m protoos.vault` |
| **CI** | `.github/workflows/ci.yml` |
| **AGENTS.md** | Coding-agent contract at repo root |
| **Requirement audit** | `traceability.json` · `VERIFICATION.md` · `python -m protoos.verify` |

## New in 0.2.0 — Constellation & Obsidian vault

The world is now a first-class graph, at parity with the web console's Constellation tab.

- `protoos.graph.build_graph(os)` derives the live object graph — principals, budgets, MCP servers/tools, AP2 mandate chains, receipts, tasks, pending approvals — with the same node-type/edge-kind vocabulary as the browser build (parity-checked: **MATCH**).
- `protoos.graph.layout(graph, seed=…)` is a deterministic force layout. Exports: `to_json`, `to_dot`, `to_svg`.
- `protoos.vault.write_vault[_zip](os, dest)` writes an Obsidian vault of wikilinked notes; `unresolved_links()` proves integrity.
- Hardening: `AuditLog.append` deep-copies payloads; `TraditionalRail` retains receipts.

```bash
python3 -m protoos.graph out/        # constellation.{json,dot,svg}
python3 -m protoos.vault vault.zip   # Obsidian vault
python3 demo.py                      # also writes both artifacts
python3 -m protoos.cli status
```

## Quickstart

```bash
python3 -m unittest discover -s tests   # 95 tests
python3 demo.py                          # end-to-end scenario
python3 -m protoos.verify                # traceability audit + live smoke
pip install -e ".[crypto]"               # optional Ed25519
protoos status
```

```python
from protoos import ProtoOS, Catalog
from protoos.sdk import ProtoOSClient

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
| CLI | `protoos/cli.py` |
| SDK | `protoos/sdk/` |
| Constellation graph | `protoos/graph.py` |
| Obsidian vault export | `protoos/vault.py` |
| Kubernetes CRDs + Deployment | `deploy/k8s/` |
| Skills | `skills/` |
| Requirement audit | `traceability.json`, `VERIFICATION.md`, `protoos/verify.py` |

## What "reference implementation" means here

Every protocol surface named by the spec is **working and tested in-process**:
JSON-RPC MCP with paid tools, the A2A task lifecycle, the full AP2
Intent→Cart→Payment mandate chain, x402 challenge/settle with an in-process
facilitator, MPP prepaid sessions, AG-UI event streams over SSE, DID
documents and well-known publication. This sandbox has **no network egress,
no Kubernetes cluster, and no external SDKs**, so anything that requires the
open internet is implemented against local/loopback equivalents and explicitly
marked `partial` or `deferred` in `traceability.json` — nothing is silently
omitted.

## Production hardening path

1. **Rust control plane (X1):** module boundaries here mirror the intended services; the Python build is the executable specification.
2. **Storage (X3):** in-memory + JSONL → etcd/Postgres / object storage / vector DB.
3. **Rails (M1/X6):** official x402/MPP/AP2 SDKs slot into the existing rail seams.
4. **Transports (X4/X5):** add gRPC/QUIC beside `httpapi.py`.
5. **Sandboxing (G4):** replace `SandboxedExecutor` with container/microVM isolation.

## Design principles

1. Compose, don't replace
2. Policy-first autonomy (every sensitive action gated)
3. Cryptographic mandates + hash-chained audit
4. Human-in-the-loop as a first-class primitive
5. Multi-rail everything (tools, messaging, payments, identity)
6. Offline-first reference with honest partial/deferred markers

## License

Apache-2.0. Governance charter draft: [`GOVERNANCE.md`](GOVERNANCE.md).
