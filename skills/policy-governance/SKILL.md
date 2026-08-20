---
name: policy-governance
description: Use ProtoOS PolicyEngine + four-layer stack + AP2 mandates + require_approval for human-in-the-loop. Fail-closed governance for any agent action.
version: 0.2.0
license: Apache-2.0
tags: [protoos, policy, governance, mandates, hotl]
---

# Policy & Governance Skill (ProtoOS)

## When to use
- Any sensitive action (payment.settle, tool.call, delegate)
- Enforcing org/user/platform/legal layers
- AP2 Intent → Cart → Payment mandate chains
- Human-in-the-loop via `require_approval`

## Workflow
1. `os.engine.add_rule(layer, effect, actions, condition)`
2. Sensitive actions go through `_gate` → policy decision is audited
3. `require_approval` returns `PendingApproval`; resolve with `os.approve(...)`
4. MandateStore verifies signatures, linkage, totals, categories, expiry

## Rules
- Default-deny for sensitive actions
- Deny-overrides precedence across layers
- Never weaken kill-switch or audit chain
- Every decision lands in the hash-chained audit log
