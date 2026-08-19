# Contributing to ProtoOS

## The contract

1. Offline path must continue to boot and pass the full test suite + `python3 -m protoos.verify`
2. Policy engine, mandate verification, and hash-chained audit remain fail-closed
3. No new wire protocols — adapters only (compose, don't replace)
4. Prefer small, focused changes
5. Update `traceability.json` / `VERIFICATION.md` when requirements change

Read `AGENTS.md` before changing code.

## Setup

```bash
python3 -m unittest discover -s tests -v
python3 demo.py
python3 -m protoos.verify
```

Optional (when cryptography is available): real Ed25519; otherwise HMAC fallback is used.

## PRs

- Small, focused changes
- Describe why / what / how verified
- Update README.md or AGENTS.md when public surfaces change
- Keep `python3 -m protoos.verify` green
