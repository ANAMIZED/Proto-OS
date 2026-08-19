# ProtoOS Governance (charter draft)

Per spec principle P7, ProtoOS is intended for a neutral, Linux-Foundation-style
home from day one. Forming a foundation is an organizational act that software
cannot perform (tracked as **deferred** in traceability.json, id P7). This
charter draft is the starting point:

- **License:** Apache-2.0 for all code; specifications under CC-BY-4.0.
- **Technical Steering Committee (TSC):** 5–9 seats, no single employer holding
  a majority; decisions by lazy consensus, fallback 2/3 vote.
- **Working groups:** identity & trust, payments plane, protocol adapters,
  policy & safety, runtime & scheduling. Each owns its adapter conformance
  suites.
- **Contribution:** DCO sign-off; maintainers promoted by sustained review
  record; all design via public RFCs.
- **Protocol neutrality:** ProtoOS composes external protocols (MCP, A2A, AP2,
  x402, MPP, UCP/ACP, AG-UI, ANP); it does not fork them. Adapter changes track
  upstream specs; divergences require a TSC-approved compatibility note.
- **Security:** private disclosure list, 90-day coordinated disclosure,
  mandatory hash-chained audit retained for all reference deployments.
