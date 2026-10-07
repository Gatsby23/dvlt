import numpy as np
import pytest

from dvlt.scripts.preprocess.scannetpp.structure import face_structure_labels


def test_face_structure_labels_uses_full_semantic_majority_before_mapping() -> None:
    # IDs: wall, floor, ceiling, chair, table, unlabeled.
    labels = np.array([0, 1, 2, 3, 4, -1], dtype=np.int32)
    faces = np.array(
        [
            [0, 0, 3],  # wall majority
            [1, 4, 1],  # floor majority
            [3, 2, 2],  # ceiling majority
            [3, 4, 0],  # all differ: first valid is chair, so other
            [0, 3, 4],  # all differ: first valid is wall
            [5, 5, 5],  # unlabeled
            [0, 3, 3],  # chair majority beats wall
            [5, 0, 4],  # first valid is wall
        ],
        dtype=np.int32,
    )
    result = face_structure_labels(labels, faces, ["wall", "floor", "ceiling", "chair", "table"])
    np.testing.assert_array_equal(result, np.array([1, 2, 3, 0, 1, 0, 0, 1], dtype=np.uint8))


def test_face_structure_labels_rejects_missing_classes_and_mismatched_faces() -> None:
    labels = np.array([0, 1, 2])
    with pytest.raises(ValueError, match="Missing structural classes"):
        face_structure_labels(labels, np.array([[0, 1, 2]]), ["wall", "floor"])
    with pytest.raises(ValueError, match="outside the semantic label array"):
        face_structure_labels(labels, np.array([[0, 1, 3]]), ["wall", "floor", "ceiling"])
