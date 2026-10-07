"""Map ScanNet++ mesh vertex semantics to wall/floor/ceiling face labels."""

import numpy as np


STRUCTURE_CLASSES = {"wall": 1, "floor": 2, "ceiling": 3}


def face_structure_labels(vertex_labels: np.ndarray, faces: np.ndarray, semantic_classes: list[str]) -> np.ndarray:
    """Return one structural label per face, using the source script's vertex majority vote.

    Labels are 0 for other/unlabeled, 1 for wall, 2 for floor, and 3 for ceiling.
    When three valid vertex labels differ, the first valid vertex wins.
    """
    vertex_labels = np.asarray(vertex_labels)
    faces = np.asarray(faces)
    if faces.ndim != 2 or faces.shape[1] != 3:
        raise ValueError("Expected triangular mesh faces with shape (N, 3)")
    if np.any(faces < 0) or np.any(faces >= len(vertex_labels)):
        raise ValueError("Mesh faces refer to vertices outside the semantic label array")

    names = {name.strip().lower(): index for index, name in enumerate(semantic_classes)}
    missing = STRUCTURE_CLASSES.keys() - names.keys()
    if missing:
        raise ValueError(f"Missing structural classes: {sorted(missing)}")

    tri = vertex_labels[faces]
    first, second, third = tri[:, 0], tri[:, 1], tri[:, 2]
    first_valid, second_valid, third_valid = first >= 0, second >= 0, third >= 0

    # Mirror the three-vertex vote in DataTools/scannetpp/dslr/depth_render.py.
    chosen = np.where(first_valid, first, np.where(second_valid, second, np.where(third_valid, third, -1)))
    second_third_majority = second_valid & third_valid & (second == third)
    chosen = np.where(second_third_majority, second, chosen)
    first_third_majority = first_valid & third_valid & (first == third)
    chosen = np.where(first_third_majority, first, chosen)
    first_second_majority = first_valid & second_valid & (first == second)
    chosen = np.where(first_second_majority, first, chosen)

    structure = np.zeros(len(faces), dtype=np.uint8)
    for name, value in STRUCTURE_CLASSES.items():
        structure[chosen == names[name]] = value
    return structure
