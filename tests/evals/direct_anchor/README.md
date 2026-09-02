# Direct Research Anchors

This directory contains frozen direct-research baselines used
to measure the value added by later orchestration.

A frozen baseline is historical evidence.

It must not be silently regenerated or improved after review.
Known defects are preserved explicitly so later systems can be
compared against the exact original artifact.


## E2 — Internal Source-Packet Direct Anchor

Case:

`state_storage_boundary_v1`

Purpose:

Measure a single Researcher against a fixed internal source
packet before adding orchestration.

The E2 anchor intentionally uses:

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

Frozen baseline:

`baselines/state_storage_boundary_v1/`


## E4.5 — Real External-Web Direct Anchor

Case:

`external_web_research_v1`

Purpose:

Measure a single real Researcher using the platform's guarded
external-web research boundary before adding multi-agent
orchestration.

The E4.5 anchor intentionally uses:

- one Researcher role;
- Claude with the `reasoning` tool profile;
- zero Claude-native tools;
- Agent Lab `research-readonly` runtime authorization;
- only `web.search` and `web.fetch` capabilities;
- real Brave Search;
- guarded public-web fetch;
- fetch only from URLs discovered by authorized search;
- runtime-owned Source provenance;
- canonical WorkerResult;
- worker and tool invocation telemetry;
- no Critic;
- no Evidence Verifier;
- no Synthesizer;
- no LangGraph research orchestration.

Frozen baseline:

`baselines/external_web_research_v1/`

The first verified run is intentionally preserved with known
claim-evidence semantic-coverage defects. Those defects are part
of the baseline and must not be corrected by regenerating it.


## Comparison Rule

Future research architectures should be evaluated against the
appropriate frozen baseline rather than replacing the baseline
with a newer model output.

Improvements should be demonstrated through new evaluation runs,
not by mutating historical baseline artifacts.
