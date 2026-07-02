"""
Mapping generation for the MCMC double-solution puzzle solver.

Generates a category-preserving bijective mapping π: S1 → S2 with correct
rotations. Corners map to corners, edges to edges, interior to interior.
"""

import random
import numpy as np


# ---------------------------------------------------------------------------
# Category classification
# ---------------------------------------------------------------------------

def _classify_cells(n: int):
    """Classify all cells into corners, edges, and interior.

    Returns three lists of (y, x) tuples.
    """
    corners = []
    edges = []
    interior = []
    for y in range(n):
        for x in range(n):
            on_top = y == 0
            on_bot = y == n - 1
            on_left = x == 0
            on_right = x == n - 1
            border_count = sum([on_top, on_bot, on_left, on_right])
            if border_count >= 2:
                corners.append((y, x))
            elif border_count == 1:
                edges.append((y, x))
            else:
                interior.append((y, x))
    return corners, edges, interior


def _which_side(y: int, x: int, n: int) -> str:
    """Return which border side a border cell belongs to.

    For corners this returns a canonical side used in rotation calculation.
    """
    if y == 0:
        return "top"
    if y == n - 1:
        return "bottom"
    if x == 0:
        return "left"
    if x == n - 1:
        return "right"
    return "interior"


# ---------------------------------------------------------------------------
# Rotation calculation
# ---------------------------------------------------------------------------

# Corners ordered clockwise: TL, TR, BR, BL
_CORNER_ORDER = {
    (0, 0): 0,      # top-left
}


def _corner_index(y: int, x: int, n: int) -> int:
    """Clockwise index of a corner: TL=0, TR=1, BR=2, BL=3."""
    if y == 0 and x == 0:
        return 0
    if y == 0 and x == n - 1:
        return 1
    if y == n - 1 and x == n - 1:
        return 2
    # y == n-1 and x == 0
    return 3


# Side order clockwise: top=0, right=1, bottom=2, left=3
_SIDE_IDX = {"top": 0, "right": 1, "bottom": 2, "left": 3}


def calculate_rotation(source: tuple, target: tuple, n: int) -> int:
    """Calculate the rotation needed when moving *source* to *target*.

    Both are (y, x) tuples. The rotation aligns flat boundary sides.

    For corners: rotation = (target_corner_idx - source_corner_idx) mod 4.
    For edges: rotation = (target_side_idx - source_side_idx) mod 4.
    For interior: rotation can be any value (0–3).

    Returns rotation ∈ {0, 1, 2, 3}.
    """
    src_side = _which_side(source[0], source[1], n)
    tgt_side = _which_side(target[0], target[1], n)

    if src_side == "interior" and tgt_side == "interior":
        # Interior pieces can take any rotation
        return random.randint(0, 3)

    # Corner → corner
    src_border = _count_borders(source[0], source[1], n)
    tgt_border = _count_borders(target[0], target[1], n)
    if src_border >= 2 and tgt_border >= 2:
        si = _corner_index(source[0], source[1], n)
        ti = _corner_index(target[0], target[1], n)
        return (ti - si) % 4

    # Edge → edge
    si = _SIDE_IDX[src_side]
    ti = _SIDE_IDX[tgt_side]
    return (ti - si) % 4


def _count_borders(y: int, x: int, n: int) -> int:
    return sum([y == 0, y == n - 1, x == 0, x == n - 1])


# ---------------------------------------------------------------------------
# Mapping generation
# ---------------------------------------------------------------------------

def generate_mcmc_mapping(n: int, *, max_fixed_fraction: float = 0.2,
                          max_attempts: int = 100):
    """Generate a random category-preserving mapping for an n×n puzzle.

    Parameters
    ----------
    n : int
        Grid size.
    max_fixed_fraction : float
        Maximum fraction of pieces that stay at the same position with the
        same rotation (fixed points). Mappings with more fixed points are
        rejected and regenerated.
    max_attempts : int
        Number of shuffle attempts before giving up on the fixed-point
        constraint (falls back to best attempt).

    Returns
    -------
    map_fwd : ndarray (n, n, 3) int32
        map_fwd[y, x] = [y2, x2, rotation]
    map_inv : ndarray (n, n, 3) int32
        map_inv[y2, x2] = [y, x, rotation]
    """
    corners, edges, interior = _classify_cells(n)
    total = n * n

    best_fwd = None
    best_fixed = total + 1

    for _ in range(max_attempts):
        map_fwd = np.zeros((n, n, 3), dtype=np.int32)
        map_inv = np.zeros((n, n, 3), dtype=np.int32)

        # Shuffle targets within each category
        corner_targets = list(corners)
        random.shuffle(corner_targets)
        edge_targets = list(edges)
        random.shuffle(edge_targets)
        interior_targets = list(interior)
        random.shuffle(interior_targets)

        fixed = 0

        # Assign corners
        for src, tgt in zip(corners, corner_targets):
            rot = calculate_rotation(src, tgt, n)
            map_fwd[src[0], src[1]] = [tgt[0], tgt[1], rot]
            map_inv[tgt[0], tgt[1]] = [src[0], src[1], rot]
            if src == tgt and rot == 0:
                fixed += 1

        # Assign edges
        for src, tgt in zip(edges, edge_targets):
            rot = calculate_rotation(src, tgt, n)
            map_fwd[src[0], src[1]] = [tgt[0], tgt[1], rot]
            map_inv[tgt[0], tgt[1]] = [src[0], src[1], rot]
            if src == tgt and rot == 0:
                fixed += 1

        # Assign interior
        for src, tgt in zip(interior, interior_targets):
            rot = calculate_rotation(src, tgt, n)
            map_fwd[src[0], src[1]] = [tgt[0], tgt[1], rot]
            map_inv[tgt[0], tgt[1]] = [src[0], src[1], rot]
            if src == tgt and rot == 0:
                fixed += 1

        if fixed < best_fixed:
            best_fixed = fixed
            best_fwd = map_fwd.copy()
            best_inv = map_inv.copy()

        if fixed <= int(max_fixed_fraction * total):
            return map_fwd, map_inv

    # Fall back to best attempt
    return best_fwd, best_inv


def swap_mapping_pair(map_fwd: np.ndarray, map_inv: np.ndarray,
                      cell_a: tuple, cell_b: tuple, n: int):
    """Swap the S2 targets of two cells (must be same category).

    Modifies *map_fwd* and *map_inv* in-place. Returns the old values so the
    caller can undo if needed.

    Returns
    -------
    undo : dict  With keys 'cell_a', 'cell_b', 'old_fwd_a', 'old_fwd_b',
                  'old_inv_a2', 'old_inv_b2'.
    """
    ya, xa = cell_a
    yb, xb = cell_b

    old_fwd_a = map_fwd[ya, xa].copy()
    old_fwd_b = map_fwd[yb, xb].copy()

    tgt_a = (old_fwd_a[0], old_fwd_a[1])  # old target of A
    tgt_b = (old_fwd_b[0], old_fwd_b[1])  # old target of B

    old_inv_a2 = map_inv[tgt_a[0], tgt_a[1]].copy()
    old_inv_b2 = map_inv[tgt_b[0], tgt_b[1]].copy()

    # A now goes to B's old target and vice versa
    rot_a_new = calculate_rotation(cell_a, tgt_b, n)
    rot_b_new = calculate_rotation(cell_b, tgt_a, n)

    map_fwd[ya, xa] = [tgt_b[0], tgt_b[1], rot_a_new]
    map_fwd[yb, xb] = [tgt_a[0], tgt_a[1], rot_b_new]

    map_inv[tgt_b[0], tgt_b[1]] = [ya, xa, rot_a_new]
    map_inv[tgt_a[0], tgt_a[1]] = [yb, xb, rot_b_new]

    return {
        "cell_a": cell_a,
        "cell_b": cell_b,
        "old_fwd_a": old_fwd_a,
        "old_fwd_b": old_fwd_b,
        "old_inv_a2": old_inv_a2,
        "old_inv_b2": old_inv_b2,
        "tgt_a": tgt_a,
        "tgt_b": tgt_b,
    }


def undo_mapping_swap(map_fwd: np.ndarray, map_inv: np.ndarray, undo: dict):
    """Revert a mapping swap using the undo dict from *swap_mapping_pair*."""
    ya, xa = undo["cell_a"]
    yb, xb = undo["cell_b"]
    map_fwd[ya, xa] = undo["old_fwd_a"]
    map_fwd[yb, xb] = undo["old_fwd_b"]
    map_inv[undo["tgt_a"][0], undo["tgt_a"][1]] = undo["old_inv_a2"]
    map_inv[undo["tgt_b"][0], undo["tgt_b"][1]] = undo["old_inv_b2"]
