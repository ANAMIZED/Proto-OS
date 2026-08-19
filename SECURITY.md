# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | Yes       |

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Report responsibly via a private GitHub security advisory.

Include description, reproduction steps, and impact (policy bypass, mandate forgery, audit-chain tamper, secret leakage, unauthorized settlement).

## Security model

- Policy-first: every sensitive action (tool call, delegation, payment) is gated; default-deny for sensitive operations
- Cryptographic AP2 mandate chains with full verification (signatures, linkage, amounts, categories, expiry)
- Hash-chained audit log with tamper detection
- Human-in-the-loop (`require_approval`) for high-value actions
- Kill switches (scoped and global) and rate limits
- Budgets with hierarchies, categories, windows, and cumulative limits
- Secret hygiene in vault exports (no private key material)
- Offline-first reference implementation; live settlement rails are simulated
