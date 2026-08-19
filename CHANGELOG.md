# Changelog

## [0.2.0] — 2026-08-19

### Added

- Constellation graph model (`protoos.graph`): live object graph of principals, budgets, MCP servers/tools, mandates, receipts, tasks, approvals
- Deterministic force layout + JSON / Graphviz DOT / standalone SVG exports
- Obsidian vault export (`protoos.vault`): wikilinked notes + policy/audit/feed tables; link integrity and secret hygiene checks
- Cross-build parity with web console Constellation vocabulary (MATCH)

### Fixed / Hardened

- `AuditLog.append` now deep-copies payloads (closes aliasing hole that could break the hash chain)
- `TraditionalRail` retains receipts consistently with x402/MPP rails

### Verification

- 95 tests OK
- 53/53 requirements dispositioned (38 implemented, 11 partial, 4 deferred)
- Live smoke + constellation + vault round-trip: PASS

## [0.1.0]

- Initial reference implementation of the Proto architecture
