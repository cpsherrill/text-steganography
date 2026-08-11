from __future__ import annotations

from text_steganography.identify.matcher import (
    evaluate_candidate,
    hamming,
    identify_bits,
    min_pairwise_distance,
)


def test_exact_match_is_consistent():
    slots = [1, 0, 1, 0]
    feasible, contradictions, matches, compared = evaluate_candidate(slots, [1, 0, 1, 0], 4)
    assert feasible is True
    assert contradictions == 0
    assert matches == 4
    assert compared == 4


def test_one_contradiction():
    slots = [1, 0, 1, 0]
    _, contradictions, matches, _ = evaluate_candidate(slots, [1, 1, 1, 0], 4)
    assert contradictions == 1
    assert matches == 3


def test_erased_positions_are_not_evidence():
    slots = [1, None, 1, None]
    _, contradictions, matches, compared = evaluate_candidate(slots, [1, 0, 1, 1], 4)
    assert contradictions == 0  # the differing bits were erased
    assert matches == 2
    assert compared == 2


def test_candidate_longer_than_capacity_is_infeasible():
    slots = [1, 0]
    feasible, _, _, _ = evaluate_candidate(slots, [1, 0, 1], 2)
    assert feasible is False


def test_unique_identification():
    slots = [1, 0, 1, 0, 1, 0]
    result = identify_bits(
        slots,
        [
            (b"A", [1, 0, 1, 0, 1, 0]),  # matches
            (b"B", [1, 0, 1, 0, 1, 1]),  # differs in last bit
            (b"C", [0, 0, 0, 0, 0, 0]),  # differs a lot
        ],
    )
    assert result.unique is True
    assert result.ambiguity == 1
    assert result.consistent[0].payload == b"A"
    assert result.best().payload == b"A"


def test_erasure_creates_ambiguity():
    # erase the one bit that distinguishes A from B
    slots = [1, 0, 1, 0, 1, None]
    result = identify_bits(
        slots,
        [
            (b"A", [1, 0, 1, 0, 1, 0]),
            (b"B", [1, 0, 1, 0, 1, 1]),
            (b"C", [0, 1, 0, 1, 0, 1]),
        ],
    )
    assert result.ambiguity == 2
    consistent_payloads = {m.payload for m in result.consistent}
    assert consistent_payloads == {b"A", b"B"}
    assert result.erased_bits == 1


def test_ranking_orders_by_contradictions():
    slots = [1, 1, 1, 1]
    result = identify_bits(
        slots,
        [
            (b"far", [0, 0, 0, 0]),  # 4 contradictions
            (b"near", [1, 1, 1, 0]),  # 1 contradiction
            (b"exact", [1, 1, 1, 1]),  # 0
        ],
    )
    assert [m.payload for m in result.ranked] == [b"exact", b"near", b"far"]
    assert result.ranking == "distance"


def test_hamming_and_min_pairwise():
    assert hamming([1, 0, 1], [1, 1, 1]) == 1
    assert min_pairwise_distance([[0, 0], [0, 1], [1, 1]]) == 1
    assert min_pairwise_distance([[0, 0]]) is None
