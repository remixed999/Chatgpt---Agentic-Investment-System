# IMP-06 — Portfolio Aggregation & Final Output Emission

## Overview
IMP-06 implements portfolio-level aggregation and Chair packet assembly with deterministic outcomes and hash gating aligned to DD-04/DD-08. Aggregation now:

- Builds portfolio summaries from per-holding outcomes and governance results.
- Assembles HoldingPackets only when eligible, omitting scorecards for VETOED/FAILED/SHORT_CIRCUITED holdings.
- Computes canonical hashes only for COMPLETED runs and records them on the committee packet.
- Preserves deterministic ordering for holdings, agent outputs, and guard trails before hashing.

## Aggregation Logic Summary
- Portfolio outcome is determined by governance precedence and G9 partial failure threshold.
- Per-holding outcomes are always recorded in `per_holding_outcomes`.
- HoldingPackets are emitted only when allowed by G10:
  - COMPLETED holdings include scorecards, caps, and penalties.
  - VETOED/FAILED/SHORT_CIRCUITED holdings omit scorecards and carry limitations.
- PortfolioCommitteePacket includes summary counts and limitations for terminal outcomes.

## Packet Eligibility Matrix (G10)
| Portfolio Outcome | PortfolioCommitteePacket | HoldingPackets | FailedRunPacket |
| --- | --- | --- | --- |
| COMPLETED | ✅ (full packet + hashes) | ✅ (eligible holdings) | ❌ |
| VETOED | ✅ (minimal, no hashes) | ❌ | ❌ |
| SHORT_CIRCUITED | ✅ (no hashes) | ✅ (all SHORT_CIRCUITED) | ❌ |
| FAILED | ❌ | ❌ | ✅ |

Holding-level eligibility:
- COMPLETED → full HoldingPacket.
- VETOED → minimal HoldingPacket with limitations.
- FAILED → minimal HoldingPacket with error classification limitations.
- SHORT_CIRCUITED → minimal HoldingPacket with limitations.

## Hash Emission Rules (DD-07/DD-08)
- Canonical hashes are emitted **only** when `portfolio_run_outcome=COMPLETED`.
- Hash bundle fields on the committee packet:
  - `snapshot_hash`
  - `config_hash`
  - `run_config_hash`
  - `committee_packet_hash`
  - `decision_hash`
  - `run_hash`
- Hash fields are excluded from canonical serialization to avoid self-referential hashing.

## Test Mapping
- **TF-01**: Happy path aggregation and hash emission.
- **TF-03**: Short-circuit emission behavior.
- **TF-05**: Vetoed holding omission of scorecard/penalties.
- **TF-12**: Penalty cap enforcement still applied for completed holdings.
- **TF-13**: Canonical hash stability across ordering changes.
- **TF-14**: Partial failure threshold strict comparison.
- **TF-15**: FAILED run emits FailedRunPacket only.
