---
name: mcp-adapters
description: Run MCP servers/clients, paid tools via x402/MPP, OpenAPI→MCP conversion, federation (mux), and policy-gated resource cache on ProtoOS.
version: 0.2.0
license: Apache-2.0
tags: [protoos, mcp, adapters, openapi, federation]
---

# MCP Adapters Skill (ProtoOS)

## When to use
- Exposing or calling tools via JSON-RPC MCP
- Paid tools that return 402 challenges
- Federating multiple MCP servers under one mux
- Caching resources under policy

## Workflow
1. `server = os.make_mcp_server(name, payee_did=...)`
2. `server.add_tool(...)` (optionally priced)
3. `os.mount_mcp(prefix, server)`
4. `os.call_tool(agent_did, "prefix.tool", args, budget_id=...)`
5. OpenAPI → MCP: `openapi_to_mcp(spec_or_url)`

## Rules
- Paid tools auto-settle under budget when possible
- ResourceCache is LRU + policy-gated
- Compose existing MCP; do not invent new wire formats
