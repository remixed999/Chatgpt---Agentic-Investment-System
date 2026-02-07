# Production Run Execution Report

## Run Status
FAILED

## Portfolio ID
PORTFOLIO-IMAGE-001

## Holdings Evaluated
5

## Governance / Guards
No governance or guardrail veto detected. The run failed before evaluation due to a CLI argument error.

## Penalties Applied
None.

## Detailed Artifacts
Expected JSON artifacts would be located in `artifacts/prod_run_001/` (summary.json, runlog.json, output_packet.json). These were not produced because the run failed before execution began.

## Failure Details
- The run failed because the local runner rejected the `--snapshot` argument.
- No guard or agent veto caused the failure; it was a command-line argument validation error in the runner.
