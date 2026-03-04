# MsFang Design (Approved)

This document captures the approved design used to implement v1.

## Approved Sections
1. System boundary: thin control-plane wrapper and adapter contracts.
2. Ticket/state/gate model with deterministic transitions.
3. Upgrade intelligence loop with approval-driven apply.
4. Repo structure with minimal config surface.
5. Phased implementation and acceptance criteria.

## Key Decisions
- Durable memory is Hermes-only.
- Channels in v1 are Slack + CLI.
- OS/package/service operations are Red-gated by default.
- Owner identity is one logical operator mapped across channels.
- Runtime homes are isolated under `~/.msfang/*`.
