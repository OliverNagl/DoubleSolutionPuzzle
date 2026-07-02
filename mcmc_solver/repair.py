"""
Targeted repair strategies for closing the last few S2 mismatches.

When the main MCMC loop gets close (mm ≤ repair_threshold) but stalls,
these strategies concentrate effort on the edges that actually matter:

1. **Focused annealing** (Numba JIT)
   - Identify "hot edges" — S1 edges whose S2 images participate in mismatches
   - Bias edge selection 80 % toward hot edges, 20 % random exploration
   - Pure-mismatch energy (no diversity/balance overhead)

2. **Greedy descent** (Python calling Numba primitives)
   - For every hot edge, try every (type, direction) value
   - Accept the single-edge change that reduces mm the most
   - Repeat until a plateau is reached

3. **Repair cycle** (combined)
   - Alternate greedy descent (exploit) and focused SA bursts (explore)
   - Greedy quickly descends, SA escapes local plateaus
"""

import numpy as np
import numba as nb
import random
import math
import time

from .state import compute_piece_s1, rotate_piece, _full_mismatch, _init_freq
from .moves import _count_mm_at_two


# ---------------------------------------------------------------------------
# Hot-edge identification (Python)
# ---------------------------------------------------------------------------

def compute_hot_edges(state):
    """Find edge indices whose S1 cells map to S2 positions with mismatches.

    Procedure
    ---------
    1.  Scan S2 for adjacency mismatches → collect offending S2 cells.
    2.  map_inv those S2 cells back to their S1 origins.
    3.  Enumerate every edge touching those S1 cells.

    Returns
    -------
    np.ndarray of int32 edge indices (sorted, deduplicated).
    """
    n = state.n
    s2 = state.s2_pieces
    map_inv = state.map_inv

    # Step 1 — S2 cells with mismatches
    hot_s2 = set()
    for i in range(n):
        for j in range(n):
            if j < n - 1 and s2[i, j, 1] + s2[i, j + 1, 3] != 0:
                hot_s2.add((i, j))
                hot_s2.add((i, j + 1))
            if i < n - 1 and s2[i, j, 2] + s2[i + 1, j, 0] != 0:
                hot_s2.add((i, j))
                hot_s2.add((i + 1, j))

    # Step 2 — trace back to S1
    hot_s1 = set()
    for (y2, x2) in hot_s2:
        sy, sx = int(map_inv[y2, x2, 0]), int(map_inv[y2, x2, 1])
        hot_s1.add((sy, sx))

    # Step 3 — edges touching hot S1 cells
    total_h = n * (n - 1)
    edges = set()
    for (sy, sx) in hot_s1:
        if sy > 0:                     # top vertical
            edges.add(total_h + (sy - 1) * n + sx)
        if sx < n - 1:                 # right horizontal
            edges.add(sy * (n - 1) + sx)
        if sy < n - 1:                 # bottom vertical
            edges.add(total_h + sy * n + sx)
        if sx > 0:                     # left horizontal
            edges.add(sy * (n - 1) + (sx - 1))

    return np.array(sorted(edges), dtype=np.int32)


# ---------------------------------------------------------------------------
# Numba JIT — focused single-edge recolor
# ---------------------------------------------------------------------------

@nb.njit(cache=True)
def _nb_focused_step(
    edge_idx,
    h_type, h_dir, v_type, v_dir,
    s1_pieces, s2_pieces,
    map_fwd, n, K, type_freq, T,
):
    """Recolor a specific edge.  Pure mismatch energy (no diversity/balance).

    Returns (accepted, delta_mm):
        accepted:  1 = accepted, 0 = rejected, -1 = identity/skip
        delta_mm:  change in mismatch count (only meaningful if accepted == 1)
    """
    total_h = n * (n - 1)

    # --- Decode edge ---
    if edge_idx < total_h:
        is_horiz = True
        ei = edge_idx // (n - 1)
        ej = edge_idx % (n - 1)
        old_t = h_type[ei, ej]
        old_d = h_dir[ei, ej]
        cA_y, cA_x = ei, ej
        cB_y, cB_x = ei, ej + 1
    else:
        is_horiz = False
        vidx = edge_idx - total_h
        ei = vidx // n
        ej = vidx % n
        old_t = v_type[ei, ej]
        old_d = v_dir[ei, ej]
        cA_y, cA_x = ei, ej
        cB_y, cB_x = ei + 1, ej

    # --- Random new value ---
    new_t = np.random.randint(1, K + 1)
    new_d = np.random.randint(0, 2)
    if new_t == old_t and new_d == old_d:
        return -1, 0

    # --- S2 targets ---
    s2A_y = map_fwd[cA_y, cA_x, 0]
    s2A_x = map_fwd[cA_y, cA_x, 1]
    s2A_r = map_fwd[cA_y, cA_x, 2]
    s2B_y = map_fwd[cB_y, cB_x, 0]
    s2B_x = map_fwd[cB_y, cB_x, 1]
    s2B_r = map_fwd[cB_y, cB_x, 2]

    # --- Old mismatches ---
    old_mm = _count_mm_at_two(n, s2_pieces, s2A_y, s2A_x, s2B_y, s2B_x)

    # --- Save for revert ---
    old_s1A = (s1_pieces[cA_y, cA_x, 0], s1_pieces[cA_y, cA_x, 1],
               s1_pieces[cA_y, cA_x, 2], s1_pieces[cA_y, cA_x, 3])
    old_s1B = (s1_pieces[cB_y, cB_x, 0], s1_pieces[cB_y, cB_x, 1],
               s1_pieces[cB_y, cB_x, 2], s1_pieces[cB_y, cB_x, 3])
    old_s2A = (s2_pieces[s2A_y, s2A_x, 0], s2_pieces[s2A_y, s2A_x, 1],
               s2_pieces[s2A_y, s2A_x, 2], s2_pieces[s2A_y, s2A_x, 3])
    old_s2B = (s2_pieces[s2B_y, s2B_x, 0], s2_pieces[s2B_y, s2B_x, 1],
               s2_pieces[s2B_y, s2B_x, 2], s2_pieces[s2B_y, s2B_x, 3])

    # --- Apply edge change ---
    if is_horiz:
        h_type[ei, ej] = new_t
        h_dir[ei, ej] = new_d
    else:
        v_type[ei, ej] = new_t
        v_dir[ei, ej] = new_d

    # --- Recompute S1 pieces ---
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

    # --- Recompute S2 pieces ---
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

    # --- Delta ---
    new_mm = _count_mm_at_two(n, s2_pieces, s2A_y, s2A_x, s2B_y, s2B_x)
    delta_mm = new_mm - old_mm
    delta_E = float(delta_mm)

    # --- Metropolis ---
    accept = False
    if delta_E <= 0.0:
        accept = True
    elif T > 0.001:
        if np.random.random() < math.exp(-delta_E / max(T, 1e-10)):
            accept = True

    if accept:
        type_freq[old_t] -= 1
        type_freq[new_t] += 1
        return 1, delta_mm
    else:
        # --- Revert ---
        if is_horiz:
            h_type[ei, ej] = old_t
            h_dir[ei, ej] = old_d
        else:
            v_type[ei, ej] = old_t
            v_dir[ei, ej] = old_d

        s1_pieces[cA_y, cA_x, 0] = old_s1A[0]
        s1_pieces[cA_y, cA_x, 1] = old_s1A[1]
        s1_pieces[cA_y, cA_x, 2] = old_s1A[2]
        s1_pieces[cA_y, cA_x, 3] = old_s1A[3]
        s1_pieces[cB_y, cB_x, 0] = old_s1B[0]
        s1_pieces[cB_y, cB_x, 1] = old_s1B[1]
        s1_pieces[cB_y, cB_x, 2] = old_s1B[2]
        s1_pieces[cB_y, cB_x, 3] = old_s1B[3]

        s2_pieces[s2A_y, s2A_x, 0] = old_s2A[0]
        s2_pieces[s2A_y, s2A_x, 1] = old_s2A[1]
        s2_pieces[s2A_y, s2A_x, 2] = old_s2A[2]
        s2_pieces[s2A_y, s2A_x, 3] = old_s2A[3]
        s2_pieces[s2B_y, s2B_x, 0] = old_s2B[0]
        s2_pieces[s2B_y, s2B_x, 1] = old_s2B[1]
        s2_pieces[s2B_y, s2B_x, 2] = old_s2B[2]
        s2_pieces[s2B_y, s2B_x, 3] = old_s2B[3]
        return 0, 0


# ---------------------------------------------------------------------------
# Numba JIT — focused batch
# ---------------------------------------------------------------------------

@nb.njit(cache=True)
def _nb_focused_batch(
    h_type, h_dir, v_type, v_dir,
    s1_pieces, s2_pieces,
    map_fwd, n, K, type_freq, T,
    num_steps,
    hot_edges, n_hot, p_focus,
):
    """Run *num_steps* focused recolor moves.

    With probability *p_focus*, selects an edge from *hot_edges*;
    otherwise picks uniformly at random from all edges.

    Returns (total_accepted, total_attempted, delta_mm_total).
    """
    total_accepted = 0
    total_attempted = 0
    delta_mm_total = 0
    total_edges = n * (n - 1) + (n - 1) * n

    for _ in range(num_steps):
        # --- Biased edge selection ---
        if n_hot > 0 and np.random.random() < p_focus:
            edge_idx = hot_edges[np.random.randint(0, n_hot)]
        else:
            edge_idx = np.random.randint(0, total_edges)

        accepted, d_mm = _nb_focused_step(
            edge_idx,
            h_type, h_dir, v_type, v_dir,
            s1_pieces, s2_pieces,
            map_fwd, n, K, type_freq, T,
        )
        if accepted >= 0:
            total_attempted += 1
        if accepted == 1:
            total_accepted += 1
            delta_mm_total += d_mm

    return total_accepted, total_attempted, delta_mm_total


# ---------------------------------------------------------------------------
# Greedy descent (Python)
# ---------------------------------------------------------------------------

def greedy_descent(state, max_iters=500, verbose=False):
    """Deterministic single-edge hill climbing on mismatch count.

    Each iteration:
      1. Enumerate all hot edges.
      2. For each, try every (type, direction) value.
      3. Accept the change that reduces mm the most.
      4. Stop when no single-edge improvement exists (plateau).

    Returns the number of mismatch reductions applied.
    """
    n = state.n
    K = state.K
    improvements = 0
    total_h = n * (n - 1)

    for iteration in range(max_iters):
        mm = int(_full_mismatch(n, state.s2_pieces))
        if mm == 0:
            state.mismatch_count = 0
            return improvements

        hot = compute_hot_edges(state)
        if len(hot) == 0:
            break

        best_delta = 0
        best_change = None

        for edge_idx in hot:
            edge_idx = int(edge_idx)

            if edge_idx < total_h:
                is_horiz = True
                ei = edge_idx // (n - 1)
                ej = edge_idx % (n - 1)
                old_t = int(state.h_type[ei, ej])
                old_d = int(state.h_dir[ei, ej])
                cA = (ei, ej)
                cB = (ei, ej + 1)
            else:
                is_horiz = False
                vidx = edge_idx - total_h
                ei = vidx // n
                ej = vidx % n
                old_t = int(state.v_type[ei, ej])
                old_d = int(state.v_dir[ei, ej])
                cA = (ei, ej)
                cB = (ei + 1, ej)

            # S2 mapped positions
            s2A_y, s2A_x, s2A_r = (int(state.map_fwd[cA[0], cA[1], k]) for k in range(3))
            s2B_y, s2B_x, s2B_r = (int(state.map_fwd[cB[0], cB[1], k]) for k in range(3))

            # Save S2 values at mapped positions
            old_s2A = state.s2_pieces[s2A_y, s2A_x].copy()
            old_s2B = state.s2_pieces[s2B_y, s2B_x].copy()

            for new_t in range(1, K + 1):
                for new_d in range(2):
                    if new_t == old_t and new_d == old_d:
                        continue

                    # Tentatively change edge
                    if is_horiz:
                        state.h_type[ei, ej] = new_t
                        state.h_dir[ei, ej] = new_d
                    else:
                        state.v_type[ei, ej] = new_t
                        state.v_dir[ei, ej] = new_d

                    # Recompute S1 pieces (local tuples, not stored)
                    s1A = compute_piece_s1(
                        cA[0], cA[1], n,
                        state.h_type, state.h_dir,
                        state.v_type, state.v_dir)
                    s1B = compute_piece_s1(
                        cB[0], cB[1], n,
                        state.h_type, state.h_dir,
                        state.v_type, state.v_dir)

                    # Rotated S2 pieces
                    r2A = rotate_piece(s1A[0], s1A[1], s1A[2], s1A[3], s2A_r)
                    r2B = rotate_piece(s1B[0], s1B[1], s1B[2], s1B[3], s2B_r)

                    state.s2_pieces[s2A_y, s2A_x] = [r2A[0], r2A[1], r2A[2], r2A[3]]
                    state.s2_pieces[s2B_y, s2B_x] = [r2B[0], r2B[1], r2B[2], r2B[3]]

                    new_mm = int(_full_mismatch(n, state.s2_pieces))
                    delta = new_mm - mm

                    if delta < best_delta:
                        best_delta = delta
                        best_change = (is_horiz, ei, ej, new_t, new_d)

                    # Revert S2
                    state.s2_pieces[s2A_y, s2A_x] = old_s2A
                    state.s2_pieces[s2B_y, s2B_x] = old_s2B

                    # Revert edge
                    if is_horiz:
                        state.h_type[ei, ej] = old_t
                        state.h_dir[ei, ej] = old_d
                    else:
                        state.v_type[ei, ej] = old_t
                        state.v_dir[ei, ej] = old_d

        if best_delta < 0 and best_change is not None:
            is_h, bei, bej, bnt, bnd = best_change
            if is_h:
                state.h_type[bei, bej] = bnt
                state.h_dir[bei, bej] = bnd
            else:
                state.v_type[bei, bej] = bnt
                state.v_dir[bei, bej] = bnd
            state.full_recompute_energy()
            improvements += 1
            if verbose:
                print(f"      Greedy: mm={state.mismatch_count} (Δ={best_delta})")
        else:
            # Plateau — no single-edge improvement
            break

    return improvements


# ---------------------------------------------------------------------------
# Tabu search endgame
# ---------------------------------------------------------------------------

def endgame_tabu_search(state, max_iterations=5000, tabu_tenure=None,
                        verbose=True):
    """Tabu search on conflict edges to close the last few mismatches.

    Unlike greedy descent which stops at plateaus, tabu search always
    takes the best available move (even non-improving) while forbidding
    recently changed edges.  This forces exploration of new regions and
    prevents cycling.

    Aspiration criterion: a tabu move is accepted if it would produce
    a new global best.

    Returns True if mm == 0 achieved.
    """
    n = state.n
    K = state.K
    total_h = n * (n - 1)
    t_start = time.time()

    if tabu_tenure is None:
        tabu_tenure = max(7, K * 2)

    best_snap = save_snapshot(state)
    best_mm = state.mismatch_count
    current_mm = state.mismatch_count

    if current_mm == 0:
        return True

    # Tabu: (edge_idx, type, dir) -> expiry iteration
    tabu = {}
    no_improve_count = 0

    for iteration in range(max_iterations):
        hot = compute_hot_edges(state)
        if len(hot) == 0:
            break

        best_move = None
        best_move_mm = float('inf')

        for edge_idx in hot:
            edge_idx = int(edge_idx)

            # Decode edge
            if edge_idx < total_h:
                is_horiz = True
                ei = edge_idx // (n - 1)
                ej = edge_idx % (n - 1)
                old_t = int(state.h_type[ei, ej])
                old_d = int(state.h_dir[ei, ej])
                cA_y, cA_x = ei, ej
                cB_y, cB_x = ei, ej + 1
            else:
                is_horiz = False
                vidx = edge_idx - total_h
                ei = vidx // n
                ej = vidx % n
                old_t = int(state.v_type[ei, ej])
                old_d = int(state.v_dir[ei, ej])
                cA_y, cA_x = ei, ej
                cB_y, cB_x = ei + 1, ej

            # S2 targets
            s2A_y = int(state.map_fwd[cA_y, cA_x, 0])
            s2A_x = int(state.map_fwd[cA_y, cA_x, 1])
            s2A_r = int(state.map_fwd[cA_y, cA_x, 2])
            s2B_y = int(state.map_fwd[cB_y, cB_x, 0])
            s2B_x = int(state.map_fwd[cB_y, cB_x, 1])
            s2B_r = int(state.map_fwd[cB_y, cB_x, 2])

            # Old local mismatches at affected S2 positions
            old_local = int(_count_mm_at_two(
                n, state.s2_pieces, s2A_y, s2A_x, s2B_y, s2B_x))

            # Save S2 values for revert
            old_s2A = state.s2_pieces[s2A_y, s2A_x].copy()
            old_s2B = state.s2_pieces[s2B_y, s2B_x].copy()

            for new_t in range(1, K + 1):
                for new_d in range(2):
                    if new_t == old_t and new_d == old_d:
                        continue

                    # Check tabu
                    move_key = (edge_idx, new_t, new_d)
                    is_tabu = tabu.get(move_key, -1) >= iteration

                    # Tentatively set edge
                    if is_horiz:
                        state.h_type[ei, ej] = new_t
                        state.h_dir[ei, ej] = new_d
                    else:
                        state.v_type[ei, ej] = new_t
                        state.v_dir[ei, ej] = new_d

                    # Recompute S1 and S2 pieces locally
                    s1A = compute_piece_s1(
                        cA_y, cA_x, n,
                        state.h_type, state.h_dir,
                        state.v_type, state.v_dir)
                    s1B = compute_piece_s1(
                        cB_y, cB_x, n,
                        state.h_type, state.h_dir,
                        state.v_type, state.v_dir)

                    r2A = rotate_piece(
                        s1A[0], s1A[1], s1A[2], s1A[3], s2A_r)
                    r2B = rotate_piece(
                        s1B[0], s1B[1], s1B[2], s1B[3], s2B_r)

                    state.s2_pieces[s2A_y, s2A_x] = [
                        r2A[0], r2A[1], r2A[2], r2A[3]]
                    state.s2_pieces[s2B_y, s2B_x] = [
                        r2B[0], r2B[1], r2B[2], r2B[3]]

                    new_local = int(_count_mm_at_two(
                        n, state.s2_pieces,
                        s2A_y, s2A_x, s2B_y, s2B_x))
                    delta_mm = new_local - old_local
                    candidate_mm = current_mm + delta_mm

                    # Accept if not tabu, or aspiration (new global best)
                    if not is_tabu or candidate_mm < best_mm:
                        if candidate_mm < best_move_mm:
                            best_move_mm = candidate_mm
                            best_move = (edge_idx, is_horiz, ei, ej,
                                         old_t, old_d, new_t, new_d)

                    # Revert S2
                    state.s2_pieces[s2A_y, s2A_x] = old_s2A
                    state.s2_pieces[s2B_y, s2B_x] = old_s2B

            # Revert edge
            if is_horiz:
                state.h_type[ei, ej] = old_t
                state.h_dir[ei, ej] = old_d
            else:
                state.v_type[ei, ej] = old_t
                state.v_dir[ei, ej] = old_d

        if best_move is None:
            # All moves tabu with no aspiration — clear tabu list
            tabu.clear()
            continue

        # Apply best move
        edge_idx, is_horiz, ei, ej, old_t, old_d, new_t, new_d = best_move
        if is_horiz:
            state.h_type[ei, ej] = new_t
            state.h_dir[ei, ej] = new_d
        else:
            state.v_type[ei, ej] = new_t
            state.v_dir[ei, ej] = new_d

        # Tabu the reverse move
        tabu[(edge_idx, old_t, old_d)] = iteration + tabu_tenure

        # Full recompute for accurate state
        state.full_recompute_energy()
        current_mm = state.mismatch_count

        if current_mm == 0:
            if verbose:
                elapsed = time.time() - t_start
                print(f"      Tabu: SOLVED at iter {iteration} ({elapsed:.1f}s)")
            return True

        if current_mm < best_mm:
            best_mm = current_mm
            best_snap = save_snapshot(state)
            no_improve_count = 0
            if verbose and iteration % 100 == 0:
                elapsed = time.time() - t_start
                print(f"      Tabu: mm={current_mm} at iter {iteration} "
                      f"({elapsed:.1f}s)")
        else:
            no_improve_count += 1

        # Adaptive tenure: increase when stuck
        if no_improve_count > 100:
            tabu_tenure = min(tabu_tenure + 2, K * 6)
            no_improve_count = 0

        # Progress
        if verbose and iteration > 0 and iteration % 500 == 0:
            elapsed = time.time() - t_start
            print(f"      Tabu: iter {iteration}/{max_iterations}, "
                  f"mm={current_mm}, best={best_mm}, "
                  f"tenure={tabu_tenure}, {elapsed:.1f}s")

    # Restore best
    if best_mm < state.mismatch_count:
        restore_snapshot(state, best_snap)

    if verbose:
        elapsed = time.time() - t_start
        print(f"      Tabu: finished with mm={state.mismatch_count} "
              f"({elapsed:.1f}s)")

    return state.mismatch_count == 0


# ---------------------------------------------------------------------------
# Combined repair cycle
# ---------------------------------------------------------------------------

def repair_phase(state, max_cycles=80, sa_steps=50_000,
                 greedy_iters=10, p_focus=0.8, verbose=True):
    """Multi-strategy repair to close the last mismatches.

    Strategy cycle (per iteration):
      1. Greedy descent — fast local hill-climbing
      2. Tabu search — escapes plateaus via non-improving moves
      3. Conflict-directed perturbation — intelligent randomisation
      4. Focused SA burst — thermal exploration

    Returns True if mm == 0 achieved.
    """
    n = state.n
    K = state.K
    t_start = time.time()

    if verbose:
        print(f"    Repair phase: starting with mm={state.mismatch_count}")

    # Absolute best tracking within repair
    best_ever_snap = save_snapshot(state)
    best_ever_mm = state.mismatch_count

    # Temperature schedule for SA bursts
    T_schedule = [0.1, 0.2, 0.4, 0.6, 0.4, 0.2]

    for cycle in range(max_cycles):
        T = T_schedule[cycle % len(T_schedule)]

        # --- Phase 1: Greedy descent ---
        pre_mm = state.mismatch_count
        reductions = greedy_descent(state, max_iters=greedy_iters, verbose=False)

        if state.mismatch_count == 0:
            if verbose:
                elapsed = time.time() - t_start
                print(f"    Repair: SOLVED in cycle {cycle} "
                      f"(greedy, {elapsed:.1f}s)")
            return True

        # Update best-ever
        if state.mismatch_count < best_ever_mm:
            best_ever_mm = state.mismatch_count
            best_ever_snap = save_snapshot(state)

        if verbose and (cycle % 5 == 0 or reductions > 0):
            elapsed = time.time() - t_start
            print(f"    Repair cycle {cycle}: mm={pre_mm}→"
                  f"{state.mismatch_count} "
                  f"(greedy Δ={-reductions}), best={best_ever_mm}, "
                  f"T={T:.2f}, {elapsed:.1f}s")

        # --- Phase 2: Tabu search ---
        tabu_iters = min(5000, 1000 + cycle * 200)
        if endgame_tabu_search(state, max_iterations=tabu_iters,
                               verbose=False):
            if verbose:
                elapsed = time.time() - t_start
                print(f"    Repair: SOLVED in cycle {cycle} "
                      f"(tabu, {elapsed:.1f}s)")
            return True

        if state.mismatch_count < best_ever_mm:
            best_ever_mm = state.mismatch_count
            best_ever_snap = save_snapshot(state)

        # --- Phase 3: Conflict-directed perturbation (on plateau) ---
        if reductions == 0 and cycle % 3 == 0:
            hot = compute_hot_edges(state)
            if len(hot) >= 2:
                n_perturb = min(len(hot), random.randint(3, 6))
                perturb_edges = random.sample(list(hot), n_perturb)
                total_h = n * (n - 1)
                for edge_idx in perturb_edges:
                    if edge_idx < total_h:
                        ei = edge_idx // (n - 1)
                        ej = edge_idx % (n - 1)
                        state.h_type[ei, ej] = random.randint(1, K)
                        state.h_dir[ei, ej] = random.randint(0, 1)
                    else:
                        vidx = edge_idx - total_h
                        ei = vidx // n
                        ej = vidx % n
                        state.v_type[ei, ej] = random.randint(1, K)
                        state.v_dir[ei, ej] = random.randint(0, 1)
                state.full_recompute_energy()

                # Immediately try greedy + tabu on perturbed state
                greedy_descent(state, max_iters=greedy_iters, verbose=False)
                if state.mismatch_count == 0:
                    if verbose:
                        elapsed = time.time() - t_start
                        print(f"    Repair: SOLVED in cycle {cycle} "
                              f"(perturbation, {elapsed:.1f}s)")
                    return True
                if state.mismatch_count < best_ever_mm:
                    best_ever_mm = state.mismatch_count
                    best_ever_snap = save_snapshot(state)

        # --- Phase 4: Focused SA burst ---
        hot = compute_hot_edges(state)
        if len(hot) == 0:
            break

        batch_per_refresh = min(2000, sa_steps)
        steps_done = 0

        while steps_done < sa_steps:
            batch = min(batch_per_refresh, sa_steps - steps_done)
            acc, att, dmm = _nb_focused_batch(
                state.h_type, state.h_dir, state.v_type, state.v_dir,
                state.s1_pieces, state.s2_pieces,
                state.map_fwd,
                np.int32(n), np.int32(K), state.type_freq, T,
                batch, hot, np.int32(len(hot)), p_focus,
            )
            state.mismatch_count += dmm
            steps_done += batch

            if state.mismatch_count <= 0:
                state.full_recompute_energy()
                if state.mismatch_count == 0:
                    if verbose:
                        elapsed = time.time() - t_start
                        print(f"    Repair: SOLVED in cycle {cycle} "
                              f"(SA, {elapsed:.1f}s)")
                    return True

            # Refresh hot edges + track best
            if steps_done % batch_per_refresh == 0:
                state.full_recompute_energy()
                if state.mismatch_count < best_ever_mm:
                    best_ever_mm = state.mismatch_count
                    best_ever_snap = save_snapshot(state)
                hot = compute_hot_edges(state)
                if len(hot) == 0:
                    break

        state.full_recompute_energy()

        # If SA made things significantly worse, restore best-seen
        if state.mismatch_count > best_ever_mm + 3:
            restore_snapshot(state, best_ever_snap)
        elif state.mismatch_count < best_ever_mm:
            best_ever_mm = state.mismatch_count
            best_ever_snap = save_snapshot(state)

    # Restore absolute best
    if best_ever_mm < state.mismatch_count:
        restore_snapshot(state, best_ever_snap)

    if verbose:
        elapsed = time.time() - t_start
        print(f"    Repair: gave up at mm={state.mismatch_count} "
              f"({elapsed:.1f}s)")
    return False


# ---------------------------------------------------------------------------
# State snapshot helpers
# ---------------------------------------------------------------------------

def save_snapshot(state):
    """Lightweight copy of mutable edge state."""
    return {
        "h_type": state.h_type.copy(),
        "h_dir": state.h_dir.copy(),
        "v_type": state.v_type.copy(),
        "v_dir": state.v_dir.copy(),
        "mm": state.mismatch_count,
    }


def restore_snapshot(state, snap):
    """Restore state from a snapshot, then full recompute."""
    state.h_type[:] = snap["h_type"]
    state.h_dir[:] = snap["h_dir"]
    state.v_type[:] = snap["v_type"]
    state.v_dir[:] = snap["v_dir"]
    state.full_recompute_energy()
