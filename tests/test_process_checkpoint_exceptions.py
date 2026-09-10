from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from process_checkpoint import apply_normalization_exceptions  # noqa: E402


SCHEMA = {
    "candidate_grain": ["timestamp", "generator_id"],
    "value_column": "estimated_generation_mw",
}


def exception(rows: int = 4, keys: int = 2, conflicts: int = 1) -> dict:
    return {
        "source": "state_estimation",
        "month": "2016-06",
        "action": "drop_ambiguous_duplicate_timestamp",
        "timestamps": ["2016-06-03T17:20:00"],
        "reason": "test",
        "evidence": {
            "rows_at_timestamp": rows,
            "unique_candidate_keys": keys,
            "conflicting_candidate_keys": conflicts,
        },
    }


def test_drop_ambiguous_full_snapshot_duplicate() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2016-06-03 17:15",
                    "2016-06-03 17:15",
                    "2016-06-03 17:20",
                    "2016-06-03 17:20",
                    "2016-06-03 17:20",
                    "2016-06-03 17:20",
                    "2016-06-03 17:25",
                    "2016-06-03 17:25",
                ]
            ),
            "generator_id": ["A", "B", "A", "A", "B", "B", "A", "B"],
            "estimated_generation_mw": [1.0, 2.0, 1.1, 1.2, 2.0, 2.0, 1.3, 2.1],
        }
    )

    result, applied = apply_normalization_exceptions(
        frame,
        SCHEMA,
        "state_estimation",
        "2016-06",
        exceptions=[exception()],
    )

    assert not result["timestamp"].eq(pd.Timestamp("2016-06-03 17:20")).any()
    assert len(result) == 4
    assert applied == [
        {
            "action": "drop_ambiguous_duplicate_timestamp",
            "timestamp": "2016-06-03T17:20:00",
            "rows_removed": 4,
            "unique_candidate_keys": 2,
            "conflicting_candidate_keys": 1,
            "exact_candidate_keys": 1,
            "reason": "test",
            "evidence": {
                "rows_at_timestamp": 4,
                "unique_candidate_keys": 2,
                "conflicting_candidate_keys": 1,
            },
        }
    ]


def test_exception_rejects_partial_duplicate_snapshot() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2016-06-03 17:20", "2016-06-03 17:20", "2016-06-03 17:20"]
            ),
            "generator_id": ["A", "A", "B"],
            "estimated_generation_mw": [1.0, 1.1, 2.0],
        }
    )

    with pytest.raises(RuntimeError, match="exactly two rows"):
        apply_normalization_exceptions(
            frame,
            SCHEMA,
            "state_estimation",
            "2016-06",
            exceptions=[exception(rows=3, keys=2, conflicts=1)],
        )
