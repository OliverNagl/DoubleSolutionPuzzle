"""
Move operators for the MCMC solver, with Numba-JIT inner loop.

Two move types:
  1. Single-edge recolor  (95 % of moves) — O(1) per move
  2. Mapping swap          (5 % of moves)  — O(1) per move

The hot inner loop (propose + delta + accept/reject) is compiled with Numba
for maximum throughput.
"""

import random
import math
import numpy as np
import numba as nb

from .state import compute_piece_s1, rotate_piece, _side_val


# -----------------------------------------------------------------------
# Numba-JIT: core inner MCMC loop
# -----------------------------------------------------------------------

@nb.njit(cache=True)
def _nb_propose_and_step(
    # Edge arrays (modified in-place on accept)
    h_type, h_dir, v_type, v_dir,
    # Piece caches (modified in-place)
    s1_pieces, s2_pieces,
    # Mapping arrays (read-only for recolor moves)
    map_fwd, map_inv,
    # Scalar parameters
    n, K,
    # Type frequency array (modified in-place)
    type_freq,
    # Temperature
    T,
    # Energy weights
    w_mm, w_div, w_bal,
):
    """Propose a single-edge recolor move, compute delta, decide accept/reject.

    Returns
    -------
    accepted : int  (1 = accepted, 0 = rejected, -1 = identity/skipped)
    delta_mm : int  Change in mismatch count (valid only if accepted == 1).
    """
    total_h = n * (n - 1)
    total_v = (n - 1) * n
    total_edges = total_h + total_v

    edge_idx = np.random.randint(0, total_edges)

    # Decode edge
    if edge_idx < total_h:
        is_horiz = True
        ei = edge_idx // (n - 1)
        ej = edge_idx % (n - 1)
        old_t = h_type[ei, ej]
        old_d = h_dir[ei, ej]
        # Two S1 cells sharing this horizontal edge
        cA_y, cA_x = ei, ej
        cB_y, cB_x = ei, ej + 1
    else:
        is_horiz = False
        vidx = edge_idx - total_h
        ei = vidx // n
        ej = vidx % n
        old_t = v_type[ei, ej]
        old_d = v_dir[ei, ej]
        # Two S1 cells sharing this vertical edge
        cA_y, cA_x = ei, ej
        cB_y, cB_x = ei + 1, ej

    # New random type/direction
    new_t = np.random.randint(1, K + 1)
    new_d = np.random.randint(0, 2)
    if new_t == old_t and new_d == old_d:
        return -1, 0  # identity move, skip

    # --- Lookup S2 positions for the two affected S1 cells ---
    s2A_y = map_fwd[cA_y, cA_x, 0]
    s2A_x = map_fwd[cA_y, cA_x, 1]
    s2A_r = map_fwd[cA_y, cA_x, 2]
    s2B_y = map_fwd[cB_y, cB_x, 0]
    s2B_x = map_fwd[cB_y, cB_x, 1]
    s2B_r = map_fwd[cB_y, cB_x, 2]

    # --- Count old mismatches at affected S2 positions ---
    old_mm = _count_mm_at_two(n, s2_pieces, s2A_y, s2A_x, s2B_y, s2B_x)

    # --- Save old piece values for potential revert ---
    old_s1A = (s1_pieces[cA_y, cA_x, 0], s1_pieces[cA_y, cA_x, 1],
               s1_pieces[cA_y, cA_x, 2], s1_pieces[cA_y, cA_x, 3])
    old_s1B = (s1_pieces[cB_y, cB_x, 0], s1_pieces[cB_y, cB_x, 1],
               s1_pieces[cB_y, cB_x, 2], s1_pieces[cB_y, cB_x, 3])
    old_s2A = (s2_pieces[s2A_y, s2A_x, 0], s2_pieces[s2A_y, s2A_x, 1],
               s2_pieces[s2A_y, s2A_x, 2], s2_pieces[s2A_y, s2A_x, 3])
    old_s2B = (s2_pieces[s2B_y, s2B_x, 0], s2_pieces[s2B_y, s2B_x, 1],
               s2_pieces[s2B_y, s2B_x, 2], s2_pieces[s2B_y, s2B_x, 3])

    # --- Tentatively apply edge change ---
    if is_horiz:
        h_type[ei, ej] = new_t
        h_dir[ei, ej] = new_d
    else:
        v_type[ei, ej] = new_t
        v_dir[ei, ej] = new_d

    # --- Recompute S1 pieces for affected cells ---
    tA, rA, bA, lA = compute_piece_s1(cA_y, cA_x, n, h_type, h_dir, v_type, v_dir)
    s1_pieces[cA_y, cA_x, 0] = tA
    s1_pieces[cA_y, cA_x, 1] = rA
    s1_pieces[cA_y, cA_x, 2] = bA
    s1_pieces[cA_y, cA_x, 3] = lA

    tB, rB, bB, lB = compute_piece_s1(cB_y, cB_x, n, h_type, h_dir, v_type, v_dir)
    s1_pieces[cB_y, cB_x, 0] = tB
    s1_pieces[cB_y, cB_x, 1] = rB
    s1_pieces[cB_y, cB_x, 2] = bB
    s1_pieces[cB_y, cB_x, 3] = lB

    # --- Recompute S2 pieces for affected positions ---
    rt, rr, rb, rl = rotate_piece(tA, rA, bA, lA, s2A_r)
    s2_pieces[s2A_y, s2A_x, 0] = rt
    s2_pieces[s2A_y, s2A_x, 1] = rr
    s2_pieces[s2A_y, s2A_x, 2] = rb
    s2_pieces[s2A_y, s2A_x, 3] = rl

    rt2, rr2, rb2, rl2 = rotate_piece(tB, rB, bB, lB, s2B_r)
    s2_pieces[s2B_y, s2B_x, 0] = rt2
    s2_pieces[s2B_y, s2B_x, 1] = rr2
    s2_pieces[s2B_y, s2B_x, 2] = rb2
    s2_pieces[s2B_y, s2B_x, 3] = rl2

    # --- Count new mismatches ---
    new_mm = _count_mm_at_two(n, s2_pieces, s2A_y, s2A_x, s2B_y, s2B_x)
    delta_mm = new_mm - old_mm

    # --- Diversity delta (simple: check type_freq changes) ---
    # old diversity
    old_k_used = 0
    for t in range(1, K + 1):
        if type_freq[t] > 0:
            old_k_used += 1
    # tentative freq update
    type_freq[old_t] -= 1
    type_freq[new_t] += 1
    new_k_used = 0
    for t in range(1, K + 1):
        if type_freq[t] > 0:
            new_k_used += 1
    # revert freq for now
    type_freq[old_t] += 1
    type_freq[new_t] -= 1

    K_min = max(1, int(0.8 * K))
    old_div = max(0, K_min - old_k_used) ** 2
    new_div = max(0, K_min - new_k_used) ** 2

    # --- Balance delta ---
    total_edges_count = 2 * n * (n - 1)
    f_max = int(np.ceil(1.5 * total_edges_count / K))

    old_bal = 0
    new_bal = 0
    for t in range(1, K + 1):
        freq = type_freq[t]
        if freq > f_max:
            old_bal += freq - f_max
        # tentative
        freq2 = freq
        if t == old_t:
            freq2 -= 1
        if t == new_t:
            freq2 += 1
        if freq2 > f_max:
            new_bal += freq2 - f_max

    # --- Total delta energy ---
    delta_E = w_mm * delta_mm + w_div * (new_div - old_div) + w_bal * (new_bal - old_bal)

    # --- Metropolis acceptance ---
    accept = False
    if delta_E <= 0.0:
        accept = True
    else:
        threshold = math.exp(-delta_E / max(T, 1e-10))
        if np.random.random() < threshold:
            accept = True

    if accept:
        # Commit: update type_freq
        type_freq[old_t] -= 1
        type_freq[new_t] += 1
        return 1, delta_mm
    else:
        # Revert edge change
        if is_horiz:
            h_type[ei, ej] = old_t
            h_dir[ei, ej] = old_d
        else:
            v_type[ei, ej] = old_t
            v_dir[ei, ej] = old_d

        # Revert S1 pieces
        s1_pieces[cA_y, cA_x, 0] = old_s1A[0]
        s1_pieces[cA_y, cA_x, 1] = old_s1A[1]
        s1_pieces[cA_y, cA_x, 2] = old_s1A[2]
        s1_pieces[cA_y, cA_x, 3] = old_s1A[3]

        s1_pieces[cB_y, cB_x, 0] = old_s1B[0]
        s1_pieces[cB_y, cB_x, 1] = old_s1B[1]
        s1_pieces[cB_y, cB_x, 2] = old_s1B[2]
        s1_pieces[cB_y, cB_x, 3] = old_s1B[3]

        # Revert S2 pieces
        s2_pieces[s2A_y, s2A_x, 0] = old_s2A[0]
        s2_pieces[s2A_y, s2A_x, 1] = old_s2A[1]
        s2_pieces[s2A_y, s2A_x, 2] = old_s2A[2]
        s2_pieces[s2A_y, s2A_x, 3] = old_s2A[3]

        s2_pieces[s2B_y, s2B_x, 0] = old_s2B[0]
        s2_pieces[s2B_y, s2B_x, 1] = old_s2B[1]
        s2_pieces[s2B_y, s2B_x, 2] = old_s2B[2]
        s2_pieces[s2B_y, s2B_x, 3] = old_s2B[3]

        return 0, 0


@nb.njit(cache=True)
def _count_mm_at_two(n, s2, ay, ax, by, bx):
    """Count S2 mismatches touching positions (ay,ax) and/or (by,bx).

    Each internal adjacency is counted at most once.
    Uses a small fixed-size dedup buffer (max 8 adjacencies).
    """
    DY = np.array([-1, 0, 1, 0], dtype=np.int32)
    DX = np.array([0, 1, 0, -1], dtype=np.int32)
    MY_SIDE = np.array([0, 1, 2, 3], dtype=np.int32)
    TH_SIDE = np.array([2, 3, 0, 1], dtype=np.int32)

    count = 0
    # Dedup: encode each edge as a unique int64 key
    seen = np.empty(16, dtype=np.int64)
    n_seen = 0

    for pidx in range(2):
        if pidx == 0:
            py, px = ay, ax
        else:
            py, px = by, bx

        for k in range(4):
            ny = py + DY[k]
            nx = px + DX[k]
            if 0 <= ny < n and 0 <= nx < n:
                # Canonical key: encode smaller-position-first
                if py < ny or (py == ny and px < nx):
                    key = py * (n + 1) * 10 + px * 10 + MY_SIDE[k]
                else:
                    key = ny * (n + 1) * 10 + nx * 10 + TH_SIDE[k]

                already = False
                for si in range(n_seen):
                    if seen[si] == key:
                        already = True
                        break
                if already:
                    continue
                seen[n_seen] = key
                n_seen += 1

                if s2[py, px, MY_SIDE[k]] + s2[ny, nx, TH_SIDE[k]] != 0:
                    count += 1

    return count


@nb.njit(cache=True)
def _nb_run_batch(
    h_type, h_dir, v_type, v_dir,
    s1_pieces, s2_pieces,
    map_fwd, map_inv,
    n, K,
    type_freq,
    T,
    num_steps,
    w_mm, w_div, w_bal,
):
    """Run *num_steps* recolor moves in a tight Numba loop.

    Returns
    -------
    total_accepted : int
    total_attempted : int
    delta_mm_total : int  (cumulative change in mismatch count)
    """
    total_accepted = 0
    total_attempted = 0
    delta_mm_total = 0

    for _ in range(num_steps):
        accepted, d_mm = _nb_propose_and_step(
            h_type, h_dir, v_type, v_dir,
            s1_pieces, s2_pieces,
            map_fwd, map_inv,
            n, K,
            type_freq,
            T,
            w_mm, w_div, w_bal,
        )
        if accepted >= 0:
            total_attempted += 1
        if accepted == 1:
            total_accepted += 1
            delta_mm_total += d_mm

    return total_accepted, total_attempted, delta_mm_total


# -----------------------------------------------------------------------
# Python-level MoveEngine (wraps Numba inner loop + mapping swaps)
# -----------------------------------------------------------------------

class MoveEngine:
    """Orchestrates moves on an MCMCState.

    The hot path (single-edge recolor) runs through Numba JIT.
    Mapping swaps are handled in Python (rare, ~5 % of moves).
    """

    def __init__(self, state):
        self.state = state
        self.n = state.n

        # Pre-classify cells for mapping swaps
        self._corners = []
        self._edges = []
        self._interior = []
        n = state.n
        for y in range(n):
            for x in range(n):
                b = sum([y == 0, y == n - 1, x == 0, x == n - 1])
                if b >= 2:
                    self._corners.append((y, x))
                elif b == 1:
                    self._edges.append((y, x))
                else:
                    self._interior.append((y, x))

    # ------------------------------------------------------------------
    # Batch recolor (Numba hot loop)
    # ------------------------------------------------------------------

    def run_recolor_batch(self, num_steps: int, T: float):
        """Run *num_steps* single-edge recolor moves via Numba.

        Returns (accepted, attempted, delta_mm_total).
        """
        s = self.state
        return _nb_run_batch(
            s.h_type, s.h_dir, s.v_type, s.v_dir,
            s.s1_pieces, s.s2_pieces,
            s.map_fwd, s.map_inv,
            np.int32(s.n), np.int32(s.K),
            s.type_freq,
            T,
            num_steps,
            s.w_mismatch, s.w_diversity, s.w_balance,
        )

    # ------------------------------------------------------------------
    # Single recolor (Python, for calibration)
    # ------------------------------------------------------------------

    def propose_recolor_py(self):
        """Python-only single recolor move for calibration.

        Returns (delta_E, undo_data) or None.
        """
        s = self.state
        n = s.n
        total_h = n * (n - 1)
        total_v = (n - 1) * n
        edge_idx = random.randrange(total_h + total_v)

        if edge_idx < total_h:
            is_horiz = True
            ei, ej = divmod(edge_idx, n - 1)
            old_t, old_d = int(s.h_type[ei, ej]), int(s.h_dir[ei, ej])
            cell_A, cell_B = (ei, ej), (ei, ej + 1)
        else:
            is_horiz = False
            vidx = edge_idx - total_h
            ei, ej = divmod(vidx, n)
            old_t, old_d = int(s.v_type[ei, ej]), int(s.v_dir[ei, ej])
            cell_A, cell_B = (ei, ej), (ei + 1, ej)

        new_t = random.randint(1, s.K)
        new_d = random.randint(0, 1)
        if (new_t, new_d) == (old_t, old_d):
            return None

        s2A = tuple(s.map_fwd[cell_A[0], cell_A[1]])
        s2B = tuple(s.map_fwd[cell_B[0], cell_B[1]])

        old_mm = int(_count_mm_at_two(
            n, s.s2_pieces, s2A[0], s2A[1], s2B[0], s2B[1]))

        # Save for undo
        old_s1A = s.s1_pieces[cell_A[0], cell_A[1]].copy()
        old_s1B = s.s1_pieces[cell_B[0], cell_B[1]].copy()
        old_s2A = s.s2_pieces[s2A[0], s2A[1]].copy()
        old_s2B = s.s2_pieces[s2B[0], s2B[1]].copy()

        # Tentatively apply
        if is_horiz:
            s.h_type[ei, ej] = new_t
            s.h_dir[ei, ej] = new_d
        else:
            s.v_type[ei, ej] = new_t
            s.v_dir[ei, ej] = new_d

        tA, rA, bA, lA = compute_piece_s1(
            cell_A[0], cell_A[1], n, s.h_type, s.h_dir, s.v_type, s.v_dir)
        s.s1_pieces[cell_A[0], cell_A[1]] = [tA, rA, bA, lA]

        tB, rB, bB, lB = compute_piece_s1(
            cell_B[0], cell_B[1], n, s.h_type, s.h_dir, s.v_type, s.v_dir)
        s.s1_pieces[cell_B[0], cell_B[1]] = [tB, rB, bB, lB]

        rt, rr, rb, rl = rotate_piece(tA, rA, bA, lA, s2A[2])
        s.s2_pieces[s2A[0], s2A[1]] = [rt, rr, rb, rl]

        rt2, rr2, rb2, rl2 = rotate_piece(tB, rB, bB, lB, s2B[2])
        s.s2_pieces[s2B[0], s2B[1]] = [rt2, rr2, rb2, rl2]

        new_mm = int(_count_mm_at_two(
            n, s.s2_pieces, s2A[0], s2A[1], s2B[0], s2B[1]))
        delta_mm = new_mm - old_mm

        # Diversity/balance delta
        old_div = s.diversity_pen
        old_bal = s.balance_pen
        s.type_freq[old_t] -= 1
        s.type_freq[new_t] += 1
        new_div = s.compute_diversity_penalty()
        new_bal = s.compute_balance_penalty()
        s.type_freq[old_t] += 1
        s.type_freq[new_t] -= 1

        delta_E = (s.w_mismatch * delta_mm
                   + s.w_diversity * (new_div - old_div)
                   + s.w_balance * (new_bal - old_bal))

        undo = {
            "is_horiz": is_horiz, "ei": ei, "ej": ej,
            "old_t": old_t, "old_d": old_d, "new_t": new_t, "new_d": new_d,
            "cell_A": cell_A, "cell_B": cell_B,
            "s2A": s2A, "s2B": s2B,
            "old_s1A": old_s1A, "old_s1B": old_s1B,
            "old_s2A": old_s2A, "old_s2B": old_s2B,
            "delta_mm": delta_mm,
            "new_div": new_div, "new_bal": new_bal,
            "old_div": old_div, "old_bal": old_bal,
        }
        return delta_E, undo

    def accept_recolor_py(self, undo):
        s = self.state
        s.mismatch_count += undo["delta_mm"]
        s.type_freq[undo["old_t"]] -= 1
        s.type_freq[undo["new_t"]] += 1
        s.diversity_pen = undo["new_div"]
        s.balance_pen = undo["new_bal"]

    def reject_recolor_py(self, undo):
        s = self.state
        d = undo
        if d["is_horiz"]:
            s.h_type[d["ei"], d["ej"]] = d["old_t"]
            s.h_dir[d["ei"], d["ej"]] = d["old_d"]
        else:
            s.v_type[d["ei"], d["ej"]] = d["old_t"]
            s.v_dir[d["ei"], d["ej"]] = d["old_d"]

        s.s1_pieces[d["cell_A"][0], d["cell_A"][1]] = d["old_s1A"]
        s.s1_pieces[d["cell_B"][0], d["cell_B"][1]] = d["old_s1B"]
        s.s2_pieces[d["s2A"][0], d["s2A"][1]] = d["old_s2A"]
        s.s2_pieces[d["s2B"][0], d["s2B"][1]] = d["old_s2B"]

    # ------------------------------------------------------------------
    # Mapping swap (Python-only, infrequent)
    # ------------------------------------------------------------------

    def propose_mapping_swap(self):
        """Propose swapping two pieces' S2 targets (same category).

        Returns (delta_E, undo_data) or None.
        """
        from .mapping import swap_mapping_pair, undo_mapping_swap

        s = self.state
        n = s.n

        # Pick a category
        r = random.random()
        if r < 0.1 and len(self._corners) >= 2:
            pool = self._corners
        elif r < 0.5 and len(self._edges) >= 2:
            pool = self._edges
        elif len(self._interior) >= 2:
            pool = self._interior
        elif len(self._edges) >= 2:
            pool = self._edges
        else:
            return None

        a, b = random.sample(pool, 2)

        # S2 positions before swap
        old_tgt_a = tuple(s.map_fwd[a[0], a[1]])
        old_tgt_b = tuple(s.map_fwd[b[0], b[1]])

        # Collect old mismatches at both old targets
        old_mm_a = int(_count_mm_at_two(
            n, s.s2_pieces, old_tgt_a[0], old_tgt_a[1], old_tgt_b[0], old_tgt_b[1]))

        # Save old S2 pieces at target positions
        old_s2_at_tgtA = s.s2_pieces[old_tgt_a[0], old_tgt_a[1]].copy()
        old_s2_at_tgtB = s.s2_pieces[old_tgt_b[0], old_tgt_b[1]].copy()

        # Perform the mapping swap
        swap_undo = swap_mapping_pair(s.map_fwd, s.map_inv, a, b, n)

        # Recompute S2 pieces at the two target positions
        new_tgt_a = tuple(s.map_fwd[a[0], a[1]])  # a now maps to old b's target
        new_tgt_b = tuple(s.map_fwd[b[0], b[1]])  # b now maps to old a's target

        # Piece A at its new S2 position
        s1A = s.s1_pieces[a[0], a[1]]
        rt, rr, rb, rl = rotate_piece(
            int(s1A[0]), int(s1A[1]), int(s1A[2]), int(s1A[3]), int(new_tgt_a[2]))
        s.s2_pieces[new_tgt_a[0], new_tgt_a[1]] = [rt, rr, rb, rl]

        # Piece B at its new S2 position
        s1B = s.s1_pieces[b[0], b[1]]
        rt2, rr2, rb2, rl2 = rotate_piece(
            int(s1B[0]), int(s1B[1]), int(s1B[2]), int(s1B[3]), int(new_tgt_b[2]))
        s.s2_pieces[new_tgt_b[0], new_tgt_b[1]] = [rt2, rr2, rb2, rl2]

        # Count new mismatches
        new_mm = int(_count_mm_at_two(
            n, s.s2_pieces, new_tgt_a[0], new_tgt_a[1], new_tgt_b[0], new_tgt_b[1]))
        delta_mm = new_mm - old_mm_a

        delta_E = 10.0 * delta_mm  # mapping swaps don't change diversity/balance

        undo = {
            "type": "mapping_swap",
            "swap_undo": swap_undo,
            "delta_mm": delta_mm,
            "old_s2_at_tgtA": old_s2_at_tgtA,
            "old_s2_at_tgtB": old_s2_at_tgtB,
            "old_tgt_a": old_tgt_a,
            "old_tgt_b": old_tgt_b,
        }
        return delta_E, undo

    def accept_mapping_swap(self, undo):
        """Commit a mapping swap."""
        self.state.mismatch_count += undo["delta_mm"]

    def reject_mapping_swap(self, undo):
        """Revert a mapping swap."""
        from .mapping import undo_mapping_swap
        s = self.state
        undo_mapping_swap(s.map_fwd, s.map_inv, undo["swap_undo"])
        # Restore old S2 pieces at the original target positions
        ota = undo["old_tgt_a"]
        otb = undo["old_tgt_b"]
        s.s2_pieces[ota[0], ota[1]] = undo["old_s2_at_tgtA"]
        s.s2_pieces[otb[0], otb[1]] = undo["old_s2_at_tgtB"]
