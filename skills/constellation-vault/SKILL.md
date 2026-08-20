---
name: constellation-vault
description: Build the live object graph (Constellation) and export an Obsidian vault with verified wikilinks from a running ProtoOS world.
version: 0.2.0
license: Apache-2.0
tags: [protoos, graph, constellation, vault, observability]
---

# Constellation & Obsidian Vault Skill (ProtoOS)

## When to use
- Visualizing principals, budgets, mandates, receipts, tasks, tools
- Exporting a portable, wikilinked knowledge base of the live world
- Debugging audit / mandate / budget relationships

## Workflow
1. `g = build_graph(os)` → nodes + edges (same vocabulary as web console)
2. `pos = layout(g, seed=42)` → deterministic force layout
3. `to_svg / to_dot / to_json` or `python -m protoos.graph out/`
4. `write_vault_zip(os, "vault.zip")` → notes + tables; `unresolved_links()` must be empty

## Rules
- Layout must stay finite and deterministic for the same seed
- No private key material in vault export
- Audit table in vault must match the hash chain row-for-row
