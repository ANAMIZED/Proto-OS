# PROTO — Build Verification & Requirements Audit

**Scope statement (read first).** This is a complete, tested *reference implementation* of the Proto spec, built in an offline sandbox (no network egress, no Kubernetes cluster, no external SDKs). Every protocol surface runs in-process/loopback. A literal production build of items that require the outside world — the Rust control plane, live payment networks, live did:web resolution, a real cluster, foundation formation — is not achievable here and is **not claimed**. What *is* claimed: every single requirement in the spec document is dispositioned below — none omitted — and everything marked `implemented` or `partial` is exercised by the automated test suite.

## Summary

- Requirements dispositioned: **53/53 (100%)**
  - implemented: **38**
  - partial: **11**
  - deferred: **4**
- Automated tests: **95 tests, result: OK**
- Audit-chain + live smoke: `python3 -m protoos.verify` → PASS


## 0.2.0 addendum — Constellation & Obsidian vault (all files upgraded)

Six new requirements (C1–C3, V1–V3) bring the Python reference to feature parity with
the web console's Constellation view; all are **implemented** and tested (19 new tests).

| ID | Requirement | Evidence |
|---|---|---|
| C1 | Constellation graph model from a live OS (principals, budgets, servers/tools, mandates, receipts, tasks, approvals) | `protoos/graph.py::build_graph`; `tests/test_graph.py` |
| C2 | Deterministic force layout (same seed ⇒ same constellation; velocity-clamped, finite) | `layout`; `test_layout_deterministic_and_finite` |
| C3 | Exports: JSON, Graphviz DOT, standalone SVG in the ledger palette | `to_json/to_dot/to_svg`; `python3 -m protoos.graph` |
| V1 | Obsidian vault: wikilinked notes for every identity/budget/mandate/receipt/task + policy/audit/feed tables; dir or zip | `protoos/vault.py`; `tests/test_vault.py` |
| V2 | Link integrity (every `[[wikilink]]` resolves) and secret hygiene (no private key material exported) | `unresolved_links`; hygiene test |
| V3 | Vault reflects ledger truth: audit table row-for-row with the chain, verdict recomputed at export | `test_audit_note_matches_chain` |

**Cross-build parity.** The JS console and the Python package derive the same graph
vocabulary from their demo worlds — node types `appr,bud,id,mnd,rcp,srv,task,tool` and
edge kinds `chain,money,own,struct,vc` — verified mechanically: **MATCH**.

**Hardening surfaced by this work (fixed):** the new demo world exposed a real
aliasing hole — a caller mutating a dict after passing it to `AuditLog.append()` could
retroactively break the hash chain. `append` now deep-copies payloads on ingest
(regression-covered by `test_audit_note_matches_chain`). `TraditionalRail` now retains
receipts like the x402/MPP rails so the constellation and vault see every settlement.

**Extended self-verification.** `python3 -m protoos.verify` now also builds the
constellation (finite layout asserted), generates the vault, checks wikilink
integrity, and validates a zip roundtrip on the same live smoke world before printing
`RESULT: PASS`.

Additional reproduce commands:

```bash
python3 -m protoos.graph out/        # constellation.{json,dot,svg}
python3 -m protoos.vault vault.zip   # Obsidian vault export + link check
```

### Status meanings

- **implemented** — behavior fully working and tested in this build (in-process/loopback transports where the spec names a wire protocol)
- **partial** — core mechanism working and tested; a named sub-aspect is stubbed, simulated, or reduced in scope
- **deferred** — cannot be completed in this offline sandbox (no network egress, no cluster, no external SDKs) or is an organizational/process item; disposition and forward path documented

## Reproduce

```bash
python3 -m unittest discover -s tests -v
python3 demo.py
python3 -m protoos.verify
```

## Requirement-by-requirement disposition

| ID | Requirement (from spec) | Status | Evidence | Notes |
|---|---|---|---|---|
| P1 | Compose, don't replace: adapters/extensions over new wire formats | **implemented** | protoos/mcp.py, a2a.py, wallet.py, commerce.py; all adapter tests | No new wire format introduced; Unified Agent Card is a superset manifest, not a protocol. |
| P2 | Policy-first autonomy: every tool call, delegation, payment through policy engine with cryptographic mandates and audit trails | **implemented** | protoos/policy.py, core.py:_gate, wallet.py:precheck; tests test_G2_*, test_I3_*, test_M1_* | Sensitive actions default-deny; every decision written to hash-chained audit. |
| P3 | Layered sovereignty: fully local/enterprise, federated, and open-internet (ANP/DID) modes | **partial** | registry.py LocalRegistry/FederatedRegistry/WellKnownDirectory; identity.py register_web_alias; tests test_D2_*, test_I1_did_document_and_web_alias_wellknown | Open mode publishes /.well-known/agent.json and did:web docs to a local root — live internet resolution deferred (egress disabled). |
| P4 | Kubernetes-native by default, with optional lighter-weight runtimes | **partial** | deploy/k8s/crds.yaml + control-plane.yaml; registry.py CRD-shaped records; the whole package runs as the lighter-weight runtime | CRDs and Deployment manifests provided and CRD shapes exercised in tests; applying to a live cluster deferred (no cluster in sandbox). |
| P5 | Multi-rail everything: tools (MCP), messaging (A2A+ANP), payments (x402+MPP+traditional), identity (DIDs+TAP+enterprise IdP) | **implemented** | mcp.py, a2a.py, wallet.py rails, identity.py EnterpriseIdPStub; tests test_T1_*, test_R1_*, test_M1/M4_*, test_I2_* | — |
| P6 | Human-in-the-loop as a first-class primitive (AG-UI + mandate types) | **implemented** | core.py PendingApproval/_gate/approve, a2a.py HUMAN_INPUT_* events; tests test_M1_E2E_large_purchase_requires_human_then_settles, test_U2_E2E_human_declines_no_money_moves | require_approval is a policy effect; approvals stream over AG-UI and resolve/settle atomically. |
| P7 | Open governance under a Linux-Foundation-style neutral foundation from day one | **deferred** | GOVERNANCE.md, LICENSE | Organizational/legal process; cannot be executed by software in a sandbox. Charter draft included. |
| C1 | Control plane: Policy Engine + Mandate Store | **implemented** | protoos/policy.py; tests TestPolicyEngine, TestMandates | — |
| C2 | Control plane: Orchestrator / Task Graph | **implemented** | runtime.py TaskGraph, core.py run/delegate; tests test_R3_taskgraph_dag_order_and_cycle, TestOrchestration | — |
| C3 | Control plane: Identity & Credential Service | **implemented** | identity.py; tests TestIdentity | — |
| C4 | Control plane: Discovery & Registry | **implemented** | registry.py; tests TestRegistry, test_D3_R2_discover_then_select_by_cost | — |
| C5 | Control plane: Observability & Audit | **implemented** | audit.py; tests TestAuditAndTracing, test_C5_export_and_verify_integrity | — |
| C6 | Control plane: Wallet / Spending Controller | **implemented** | wallet.py; tests TestWallet, TestToolsAndPayments | — |
| C7 | Protocol adapter tier: MCP, A2A, AGP / AP2, x402, MPP, TAP / UCP-ACP / AG-UI, ANP, DIDs | **partial** | mcp.py, a2a.py, wallet.py, commerce.py, identity.py, registry.py; all adapter tests | All named surfaces have working reference-shaped, in-process adapters. AGP appears as routing inspiration (rank_candidates), not a wire adapter; adapters are not certified conformant against published external specs (egress disabled). |
| C8 | Application layer: agent frameworks (LangGraph, CrewAI, ADK, ARC/LMOS DSLs) on top | **partial** | core.py OSContext + A2A handler contract; every e2e test agent is written against it | Stable handler/OSContext contract any framework can target; concrete third-party bindings deferred (packages not installable offline). |
| I1 | Identity: W3C DIDs (did:web, did:key, ANP did:wba variants) + Verifiable Credentials | **implemented** | identity.py Identity/did documents/register_web_alias/issue_vc; tests test_I1_* | did:proto is a did:key-style key-hash method; did:web/wba documents publish to a local well-known root — live HTTP resolution deferred (egress disabled). |
| I2 | Bridge to enterprise: OAuth 2.1 / OIDC + TAP-style agent identity | **partial** | identity.py EnterpriseIdPStub.bridge_to_proto; test_I2_oidc_tap_bridge | OIDC-shaped assertion -> Proto session token with act provenance; full OAuth 2.1 flows against a real IdP deferred. |
| I3 | AP2 Mandates (Intent, Cart, Payment) as first-class objects stored and verified by the OS | **implemented** | policy.py MandateStore.verify_chain; tests TestMandates, test_I3_E2E_mandate_category_blocks_purchase | Chain checks: signatures, linkage, totals, intent max, categories, currency, expiry. |
| I4 | Cryptographic identity at creation; short-lived session credentials; RFC 8693-style token exchange | **implemented** | identity.py issue_token/exchange_token/revoke_token, core.py create_agent; tests test_I4_* | Ed25519 in this environment; OS-verified HMAC fallback when `cryptography` is absent. |
| D1 | Unified Agent Card / Capability Manifest — superset of A2A cards, MCP manifests, UCP profiles, ANP/LMOS descriptions (JSON-LD preferred) | **implemented** | registry.py UnifiedAgentCard; test_D1_card_superset_roundtrip | JSON-LD-lite: @context field carried; full JSON-LD expansion not required by any consumer in this build. |
| D2 | Multi-backend registry: local Kubernetes CRDs (LMOS-style), federated directories (AGNTCY-like), open search (ANP), well-known URLs | **implemented** | registry.py LocalRegistry/FederatedRegistry/WellKnownDirectory; tests test_D2_*; httpapi.py /.well-known/agents | Well-known served over loopback HTTP too. |
| D3 | Semantic + vector search over capabilities under policy constraints | **implemented** | registry.py SemanticIndex (TF-IDF cosine) with `where` filter; tests test_D3_* | Vectorization is TF-IDF (stdlib); swapping in learned embeddings is an isolated seam (requires model download — egress disabled). |
| R1 | Task and workflow model extending the A2A Task lifecycle | **implemented** | a2a.py states submitted/working/input-required/completed/failed/canceled; tests TestA2A | — |
| R2 | Hierarchical routing inspired by AGP: capability announcements, policy matching, cost-aware selection | **partial** | registry.py rank_candidates + SemanticIndex.where, core.py discover; tests test_R2_cost_aware_ranking, test_D3_R2_discover_then_select_by_cost | Capability+policy+cost selection implemented; multi-tier AGP gateway topology/announcement gossip deferred. |
| R3 | Supervisor agents or declarative graphs delegate via A2A while the OS enforces budgets and policies | **implemented** | core.py delegate (policy gate, budget slices), runtime.py TaskGraph; test_R3_E2E_delegate_with_budget_slice | — |
| R4 | Native support for short-lived tasks and long-running sessions | **implemented** | a2a.py input-required parking/resume, runtime.py SessionManager; tests test_R1_input_required_resume_long_running, test_R4_session_manager_long_running | — |
| T1 | First-class MCP client and server support, including paid MCP tools via x402/MPP wrappers | **implemented** | mcp.py MCPServer/MCPClient, core.py call_tool auto-payment; tests test_T1_*, test_M1_E2E_paid_tool_autopays_x402_under_budget, test_M4_E2E_paid_tool_via_mpp_session | 402-coded error carries an x402 challenge; OS pays via budgeted x402 or an MPP session and retries. |
| T2 | Automatic OpenAPI -> MCP conversion and federation of multiple MCP servers | **implemented** | mcp.py openapi_to_mcp, MCPMux; tests test_T2_* | Converter accepts a live transport; default offline transport returns structured simulated calls (egress disabled). |
| T3 | Resource and prompt caching with policy-based access control | **implemented** | mcp.py ResourceCache (LRU + policy gate); test_T3_resource_cache_policy_and_lru | — |
| M1 | Unified spending controller: AP2 authorization, then settlement via x402 (crypto/micro), MPP (multi-rail/sessions), or traditional rails | **implemented** | wallet.py SpendingController.precheck/settle + three rails; tests test_M1_* | Facilitator/clearing are in-process simulations; connecting real crypto or banking networks deferred (egress disabled). |
| M2 | UCP/ACP for product discovery and checkout flows | **implemented** | commerce.py Catalog.search/checkout feeding CartMandates; purchase-flow e2e tests | Reference-shaped; not certified against external UCP/ACP specs. |
| M3 | Built-in budget hierarchies, category controls, time windows, cumulative limits | **implemented** | wallet.py Budget/check_budget/spent roll-up; tests test_M3_* | Spend rolls up ancestors; windows are rolling. |
| M4 | MPP-style sessions for high-frequency tool or API use | **implemented** | wallet.py MPPRail open/charge/close+refund; tests test_M4_* | — |
| U1 | AG-UI as the standard event stream to frontends | **implemented** | a2a.py AGUIBus, httpapi.py SSE endpoint; tests TestAGUI, test_X4_http_jsonrpc_wellknown_and_sse | — |
| U2 | Generative UI patterns, shared state, human approvals, multi-client (web, mobile, terminal, chat) | **partial** | AGUIBus state deltas + multi-subscriber, approvals over the stream; tests test_U1/U2_* | Shared state, approvals and multi-client subscription implemented; rendered generative-UI component library deferred (event payloads carry the data). |
| G1 | Declarative policy language (CEL-like) + higher-level DSL, evaluated on every sensitive action | **implemented** | policy.py safe_eval (whitelisted AST) + Rule schema; tests test_G1_* | No eval(); attribute access, calls and arithmetic are rejected. |
| G2 | Four-layer policy stack: platform, legal/jurisdictional, organization, personal/user | **implemented** | policy.py LAYERS + deny-overrides precedence; tests test_G2_* | — |
| G3 | Complete hash-chained audit log of every mandate, tool call, delegation and payment | **implemented** | audit.py AuditLog.verify; emission sites across policy/wallet/core/a2a; tests test_G3_* | Tamper detection returns the first bad index. |
| G4 | Sandboxing, rate limits, and kill switches | **partial** | runtime.py RateLimiter/KillSwitch/SandboxedExecutor; tests test_G4_* | Rate limits and scoped/global kill switches fully implemented; sandboxing is in-process capability scoping — OS/container-level isolation deferred to the production runtime. |
| O1 | OpenTelemetry everywhere + agent-specific traces (task graphs, tool latency, settlement, policy decisions) | **implemented** | audit.py Tracer spans over run/tool/purchase/graph; tests test_O1_*; export via ProtoOS.export | OTel-shaped spans exported as JSONL; OTLP network exporter deferred (egress disabled). |
| X1 | Control plane in Rust | **deferred** | README.md porting notes | cargo cannot fetch crates offline and std-only Rust lacks JSON/HTTP. The Python reference is the executable specification; module boundaries mirror the intended Rust services. |
| X2 | Pluggable agent runtimes (Python/TS preferred) | **partial** | Python runtime throughout; A2A handler contract is language-neutral over the HTTP JSON-RPC surface | TypeScript runtime deferred (npm registry unreachable). |
| X3 | Storage: etcd/Postgres control plane; object storage + vector DB for manifests and memory | **deferred** | In-memory stores + JSONL/well-known file persistence; storage touchpoints isolated per subsystem | No etcd/Postgres/object-store services in sandbox; swap-in points documented in README. |
| X4 | Transport: HTTP/JSON-RPC + SSE baseline | **implemented** | httpapi.py (/mcp, /a2a JSON-RPC; /agui SSE; /.well-known/agents); test_X4_http_jsonrpc_wellknown_and_sse | Loopback only (egress disabled). |
| X5 | gRPC and QUIC optional transports | **deferred** | — | Explicitly optional in spec; grpcio/QUIC libs not installable offline. |
| X6 | Crypto: standard libraries + existing x402/MPP/AP2 SDKs | **partial** | Ed25519 via `cryptography` (standard library-grade), HMAC fallback; rails implemented natively | Official external x402/MPP/AP2 SDKs unavailable offline; native implementations follow the flows described in the spec document. |
| X7 | Open-source under Apache 2.0 (or equivalent), neutral-foundation governed | **partial** | LICENSE (Apache-2.0), GOVERNANCE.md | License applied; foundation formation is an organizational process (see P7). |

## Deferred items — why, and the forward path

- **P7 — Open governance under a Linux-Foundation-style neutral foundation from day one**: Organizational/legal process; cannot be executed by software in a sandbox. Charter draft included.
- **X1 — Control plane in Rust**: cargo cannot fetch crates offline and std-only Rust lacks JSON/HTTP. The Python reference is the executable specification; module boundaries mirror the intended Rust services.
- **X3 — Storage: etcd/Postgres control plane; object storage + vector DB for manifests and memory**: No etcd/Postgres/object-store services in sandbox; swap-in points documented in README.
- **X5 — gRPC and QUIC optional transports**: Explicitly optional in spec; grpcio/QUIC libs not installable offline.

*Generated by tools/gen_verification.py from traceability.json; the JSON file is the machine-readable source of truth consumed by `python3 -m protoos.verify`.*
