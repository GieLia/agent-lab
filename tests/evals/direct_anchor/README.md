# Direct Research Anchor

E2 baseline for measuring the value added by later orchestration.

The anchor intentionally uses:

- one model invocation;
- one Researcher role;
- one fixed mission;
- one fixed source packet;
- no external tools;
- no Critic;
- no Evidence Verifier;
- no Synthesizer;
- no LangGraph retry loop.

The human reference is never included in the model prompt.

Future graph implementations should be compared against
the same mission and source packet.
