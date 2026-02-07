Rollback plan (DO NOT EXECUTE):
1. Stop production orchestration runs.
2. Restore release bundle manifest to last-known-good: config/release_bundle/release_manifest.json.
3. Rehydrate config bundle from the same release artifacts.
4. Validate hashes with config/release_manifest.json.
5. Replay TF-01 fixture to confirm deterministic hashes match Phase 3 baselines.
