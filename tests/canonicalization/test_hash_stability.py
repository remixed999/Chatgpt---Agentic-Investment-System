from __future__ import annotations

from src.core.canonicalization import canonical_json_dumps, hash_decision_payload


def test_ordering_rules_stabilize_lists() -> None:
    payload_a = {
        "holdings": [
            {"identity": {"holding_id": "B"}, "weight": 0.5},
            {"identity": {"holding_id": "A"}, "weight": 0.5},
        ],
        "agent_outputs": [
            {"agent_name": "ZZ"},
            {"agent_name": "AA"},
        ],
        "penalty_items": [
            {"category": "B", "reason": "late", "source_agent": "X"},
            {"category": "A", "reason": "miss", "source_agent": "DIO"},
        ],
    }
    payload_b = {
        "penalty_items": list(reversed(payload_a["penalty_items"])),
        "agent_outputs": list(reversed(payload_a["agent_outputs"])),
        "holdings": list(reversed(payload_a["holdings"])),
    }

    assert hash_decision_payload(payload_a) == hash_decision_payload(payload_b)


def test_excluded_fields_do_not_change_hash() -> None:
    payload_a = {"run_id": "A", "retrieval_timestamp": "2024-01-01T00:00:00Z", "value": 1}
    payload_b = {"run_id": "B", "retrieval_timestamp": "2024-02-01T00:00:00Z", "value": 1}

    assert hash_decision_payload(payload_a) == hash_decision_payload(payload_b)


def test_no_exponent_notation_in_canonical_json() -> None:
    encoded = canonical_json_dumps({"small": 1e-6, "trail": 1.2300})

    assert "e-" not in encoded
    assert "e+" not in encoded


def test_logical_inputs_same_hash_with_different_ordering() -> None:
    payload_a = {"b": 2, "a": 1}
    payload_b = {"a": 1, "b": 2}

    assert hash_decision_payload(payload_a) == hash_decision_payload(payload_b)
