from __future__ import annotations

from typing import List

from src.core.guards.base import Guard
from src.core.guards.guards_g0_g10 import (
    G0InputSchemaGuard,
    G10ArtifactCompletenessGuard,
    G1IdentityContextGuard,
    G2ProvenanceGuard,
    G3FreshnessGuard,
    G4RegistryCompletenessGuard,
    G5AgentConformanceGuard,
    G6GovernancePrecedenceGuard,
    G7DeterminismGuard,
    G8EmissionEligibilityGuard,
    G9PartialFailureGuard,
)


def build_guard_registry() -> List[Guard]:
    return [
        G0InputSchemaGuard(),
        G1IdentityContextGuard(),
        G2ProvenanceGuard(),
        G3FreshnessGuard(),
        G4RegistryCompletenessGuard(),
        G5AgentConformanceGuard(),
        G6GovernancePrecedenceGuard(),
        G7DeterminismGuard(),
        G8EmissionEligibilityGuard(),
        G9PartialFailureGuard(),
        G10ArtifactCompletenessGuard(),
    ]
