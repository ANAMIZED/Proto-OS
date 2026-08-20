---
name: x402-payments
description: Unified spending controller with x402, MPP sessions, and traditional rails under AP2 mandates and budgets.
version: 0.2.0
license: Apache-2.0
tags: [protoos, x402, mpp, payments, budgets]
---

# x402 / Multi-Rail Payments Skill (ProtoOS)

## When to use
- Paid MCP tools (402 challenge → auto-settle under budget)
- Product checkout via Catalog + AP2 mandates
- High-frequency tool use via MPP prepaid sessions

## Workflow
1. Create budget: `os.wallet.create_budget(did, limit, window=..., categories=...)`
2. For tools: `os.call_tool(..., budget_id=...)` auto-pays on 402
3. For purchases: `os.purchase(...)` builds Intent→Cart→Payment then settles
4. Large amounts trigger `require_approval` (HOTL)

## Rules
- Always attach a budget_id for money-moving paths
- Category and window limits are enforced
- Receipts retained on all rails (x402, MPP, traditional)
- Settlement is audited; ledger is queryable
