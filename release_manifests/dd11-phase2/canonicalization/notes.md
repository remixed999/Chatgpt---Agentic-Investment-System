# Canonicalization & Hash Validation Evidence

- Canonical JSON serialization is enforced via `stable_json_dumps`/canonical hash functions used in packet emission and replay hashing.
- Hashes for committee/decision/run are present only when outcome is COMPLETED (see hash_validation.json).
- Hash inputs are derived from decision payload (committee packet + holding packets) and configuration hashes, excluding non-decision fields by construction in hashing utilities.
- Hash stability confirmed across deterministic replay (see hash_validation.json and replay_diff.txt).
