---
name: multi-agent-workflow
description: Orchestrate multi-agent workflows with discovery, budgeted delegation, TaskGraph, and AG-UI streams on ProtoOS.
version: 0.2.0
license: Apache-2.0
tags: [protoos, multi-agent, workflow, a2a, delegation]
---

# Multi-Agent Workflow Skill (ProtoOS)

## When to use
- Goals that need specialist roles (researcher, supervisor, …)
- Cost-aware discovery + ranking
- Budget-sliced delegation under policy

## Workflow
1. Register agents with handlers + cost metadata
2. `os.discover(query, max_cost=...)` → ranked candidates
3. `os.delegate(from_did, to_did, message, budget_id=slice)` 
4. Task lifecycle (submitted → working → input-required → completed)
5. AG-UI events stream for frontends

## Rules
- Always give each role an explicit budget slice
- Policy gate + kill-switch apply to every delegate/tool call
- Prefer least-privilege capabilities per agent
