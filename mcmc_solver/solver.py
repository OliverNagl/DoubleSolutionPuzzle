"""
Main MCMC solver loop with adaptive temperature, restarts, and multi-level
recovery strategy.

The hot inner loop delegates to Numba-compiled functions in moves.py.
"""

import math
import random
import time
import numpy as np

from .state import MCMCState, _full_mismatch, _init_freq, _recompute_all
from .mapping import generate_mcmc_mapping
from .moves import MoveEngine, _nb_run_batch, _count_mm_at_two
from .repair import (
    repair_phase, save_snapshot, restore_snapshot,
    compute_hot_edges, _nb_focused_batch,
)


class MCMCSolver:
    """MCMC double-solution puzzle solver.

    Usage
    -----
    >>> solver = MCMCSolver(n=10, K=6)
    >>> result = solver.solve()
    >>> if result is not None:
    ...     state = result
    """

    def __init__(
        self,
        n: int,
        K: int,
        *,
        max_mapping_attempts: int = 20,
        max_restarts_per_mapping: int = 10,
        max_steps: int | None = None,
        patience: int = 200_000,
        T_final: float = 0.05,
        batch_size: int = 1000,
        max_reheats: int = 8,
        reheat_factor: float = 1.5,
        repair_threshold: int | None = None,
        w_mismatch: float = 10.0,
        w_diversity: float = 1.0,
        w_balance: float = 0.5,
        w_identical: float = 0.0,
        track_identical: bool = False,
        verbose: bool = True,
        # Legacy params (ignored, kept for backward compat)
        p_recolor: float = 0.95,
        p_swap: float = 0.05,
    ):
        self.n = n
        self.K = K
        self.max_mapping_attempts = max_mapping_attempts
        self.max_restarts = max_restarts_per_mapping
        self.max_steps = max_steps or max(200 * n ** 4, 10_000_000)
        self.patience = patience
        self.T_final = T_final
        self.batch_size = batch_size
        self.max_reheats = max_reheats
        self.reheat_factor = reheat_factor
        self.w_mismatch = w_mismatch
        self.w_diversity = w_diversity
        self.w_balance = w_balance
        self.w_identical = w_identical
        self.track_identical = track_identical
        self.verbose = verbose

        # Repair mode: kick in when mm ≤ this threshold.
        # Old default n*(n-1) is far too high for large n — greedy
        # descent in repair is O(hot_edges × 2K) per iteration, so
        # keep the threshold low to let MCMC do the bulk of the work.
        if repair_threshold is not None:
            self.repair_threshold = repair_threshold
        else:
            self.repair_threshold = max(2 * n, 20)

        # Global best tracking (across restarts/mappings)
        self._global_best_snap = None
        self._global_best_mm = float('inf')
        self._global_best_mapping = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def solve(self) -> MCMCState | None:
        """Run the multi-level MCMC search. Returns state or None."""
        # Reset global best tracking
        self._global_best_snap = None
        self._global_best_mm = float('inf')
        self._global_best_mapping = None

        for m_attempt in range(self.max_mapping_attempts):
            if self.verbose:
                print(f"\n{'='*60}")
                print(f"  Mapping attempt {m_attempt + 1}/{self.max_mapping_attempts}")
                print(f"{'='*60}")

            map_fwd, map_inv = generate_mcmc_mapping(self.n)

            # Count fixed points
            fixed = 0
            for y in range(self.n):
                for x in range(self.n):
                    fy, fx, fr = map_fwd[y, x]
                    if fy == y and fx == x and fr == 0:
                        fixed += 1
            if self.verbose:
                total = self.n ** 2
                displaced = total - fixed
                print(f"  Fixed points: {fixed}/{total}  "
                      f"({displaced} displaced, {100*displaced/total:.0f}%)")

            for restart in range(self.max_restarts):
                result = self._run_mcmc(map_fwd, map_inv, restart)
                if result is not None:
                    return result

            if self.verbose:
                print(f"  Mapping {m_attempt + 1} exhausted after "
                      f"{self.max_restarts} restarts")

        # ----------------------------------------------------------
        # Final repair attempt on global best
        # ----------------------------------------------------------
        if (self._global_best_mm > 0
                and self._global_best_mm <= self.repair_threshold
                and self._global_best_snap is not None):
            if self.verbose:
                print(f"\n{'='*60}")
                print(f"  Final repair attempt (global best mm={self._global_best_mm})")
                print(f"{'='*60}")
            fwd, inv = self._global_best_mapping
            state = MCMCState(self.n, self.K, fwd, inv,
                             w_mismatch=self.w_mismatch,
                             w_diversity=self.w_diversity,
                             w_balance=self.w_balance,
                             w_identical=self.w_identical,
                             track_identical=self.track_identical)
            restore_snapshot(state, self._global_best_snap)
            if repair_phase(state, verbose=self.verbose):
                return state

        if self.verbose:
            print("\nFailed to find a solution.")
        return None

    # ------------------------------------------------------------------
    # Single MCMC run
    # ------------------------------------------------------------------

    def _run_mcmc(self, map_fwd, map_inv, restart_idx):
        """Single MCMC run with geometric cooling on a given mapping."""
        state = MCMCState(self.n, self.K, map_fwd, map_inv,
                         w_mismatch=self.w_mismatch,
                         w_diversity=self.w_diversity,
                         w_balance=self.w_balance,
                         w_identical=self.w_identical,
                         track_identical=self.track_identical)

        if restart_idx > 0:
            self._partial_randomize(state, fraction=0.3)

        engine = MoveEngine(state)

        # Best-state checkpoint
        best_snapshot = None
        repair_attempts = 0
        hot_edges = None
        hot_edges_step = -100000

        # Warm up Numba (first call triggers compilation)
        if restart_idx == 0:
            self._warmup_numba(engine, state)

        # --- Geometric cooling setup ---
        T0 = self._calibrate_T0(engine)
        T = T0
        n_batches = max(1, self.max_steps // self.batch_size)
        cool_factor = (self.T_final / T0) ** (1.0 / n_batches)

        best_energy = state.energy
        best_mm = state.mismatch_count
        best_T = T
        stagnation = 0
        reheat_count = 0

        total_accepted = 0
        total_attempted = 0

        t_start = time.time()
        step = 0

        if self.verbose:
            print(f"  Restart {restart_idx}: initial mm={state.mismatch_count}, "
                  f"E={state.energy:.1f}, T0={T:.3f}, "
                  f"cool_factor={cool_factor:.6f}")

        while step < self.max_steps:
            # ----------------------------------------------------------
            # Run a batch of recolor moves (pure recolor, no swaps)
            # ----------------------------------------------------------
            batch = min(self.batch_size, self.max_steps - step)

            # Use conflict-biased (focused) batches when mismatches exist
            if state.mismatch_count > 0:
                if (hot_edges is None
                        or step - hot_edges_step > 5 * self.batch_size):
                    hot_edges = compute_hot_edges(state)
                    hot_edges_step = step
                if hot_edges is not None and len(hot_edges) > 0:
                    total_adj = 2 * state.n * (state.n - 1)
                    frac = state.mismatch_count / total_adj
                    if frac > 0.3:
                        p_focus = 0.3
                    elif frac > 0.1:
                        p_focus = 0.5
                    else:
                        p_focus = 0.8
                    # _nb_focused_step uses raw delta_mm as energy
                    # (not 10*delta_mm), so scale T by mismatch weight.
                    acc, att, d_mm = _nb_focused_batch(
                        state.h_type, state.h_dir,
                        state.v_type, state.v_dir,
                        state.s1_pieces, state.s2_pieces,
                        state.map_fwd,
                        np.int32(state.n), np.int32(state.K),
                        state.type_freq, T / 10.0,
                        batch, hot_edges,
                        np.int32(len(hot_edges)), p_focus,
                    )
                else:
                    acc, att, d_mm = engine.run_recolor_batch(batch, T)
            else:
                hot_edges = None
                acc, att, d_mm = engine.run_recolor_batch(batch, T)

            state.mismatch_count += d_mm
            step += batch
            total_accepted += acc
            total_attempted += att

            # Sync diversity/balance (cheap)
            state.diversity_pen = state.compute_diversity_penalty()
            state.balance_pen = state.compute_balance_penalty()

            # ----------------------------------------------------------
            # Geometric cooling
            # ----------------------------------------------------------
            T *= cool_factor
            T = max(T, self.T_final)

            # ----------------------------------------------------------
            # Track best & check for solution
            # ----------------------------------------------------------
            cur_E = state.energy
            if cur_E < best_energy:
                best_energy = cur_E
                best_T = T
                stagnation = 0

            # Track best mismatch count independently of total energy.
            # Energy includes diversity/balance penalties that can mask
            # genuine mismatch improvements.
            if state.mismatch_count < best_mm:
                best_mm = state.mismatch_count
                best_T = T
                stagnation = 0
                if best_mm > 0:
                    best_snapshot = save_snapshot(state)
                    if best_mm < self._global_best_mm:
                        self._global_best_mm = best_mm
                        self._global_best_snap = save_snapshot(state)
                        self._global_best_mapping = (
                            state.map_fwd.copy(), state.map_inv.copy())
            elif cur_E >= best_energy:
                stagnation += batch

            if state.mismatch_count == 0:
                elapsed = time.time() - t_start
                if self.verbose:
                    K_used = int(np.count_nonzero(state.type_freq[1:]))
                    print(f"  >>> SOLVED at step {step:,}, {elapsed:.1f}s, "
                          f"E={cur_E:.1f}, K_used={K_used}/{self.K}")
                if state.diversity_pen == 0:
                    return state
                if self.verbose:
                    print(f"      (diversity penalty {state.diversity_pen} > 0, "
                          f"continuing...)")

            # ----------------------------------------------------------
            # Stagnation handling (progressive recovery)
            # ----------------------------------------------------------
            # Adaptive patience: when mm is low, improvements are rare
            # but valuable, so wait longer.  Scale patience up as mm
            # drops below half the total adjacencies.
            total_adj = 2 * state.n * (state.n - 1)
            if best_mm < total_adj // 4:
                # Low-mm regime: multiply patience by up to 5×
                progress_ratio = max(best_mm, 1) / max(total_adj // 4, 1)
                adaptive_patience = int(
                    self.patience * (1.0 + 4.0 * (1.0 - progress_ratio)))
            else:
                adaptive_patience = self.patience

            if stagnation > adaptive_patience:
                stagnation = 0
                reheat_count += 1

                # If close to solution, prioritize repair
                if (best_mm > 0
                        and best_mm <= self.repair_threshold
                        and best_snapshot is not None
                        and repair_attempts < 3):
                    repair_attempts += 1
                    if self.verbose:
                        print(f"    Repair attempt #{repair_attempts} "
                              f"(best_mm={best_mm})...")
                    restore_snapshot(state, best_snapshot)
                    if repair_phase(state, verbose=self.verbose):
                        return state
                    # Repair may have improved
                    if state.mismatch_count < best_mm:
                        best_mm = state.mismatch_count
                        best_energy = state.energy
                        best_snapshot = save_snapshot(state)
                        if best_mm < self._global_best_mm:
                            self._global_best_mm = best_mm
                            self._global_best_snap = save_snapshot(state)
                            self._global_best_mapping = (
                                state.map_fwd.copy(), state.map_inv.copy())

                if reheat_count > self.max_reheats:
                    if self.verbose:
                        elapsed = time.time() - t_start
                        idp = state.count_identical_pieces()
                        print(f"  Restart {restart_idx}: stuck at mm={best_mm}, "
                              f"idp={idp}, step={step:,}, {elapsed:.1f}s")
                    return None

                # Restore best state
                if best_snapshot is not None:
                    restore_snapshot(state, best_snapshot)
                    hot_edges = None

                # Swap bursts only when mm is still high — they are
                # too destructive when the state is nearly solved.
                if reheat_count > 3 and best_mm > total_adj // 8:
                    self._swap_burst(engine, state)
                    if self.verbose:
                        print(f"    Swap burst applied, "
                              f"mm={state.mismatch_count}")
                    if state.mismatch_count < best_mm:
                        best_mm = state.mismatch_count
                        best_energy = state.energy
                        best_snapshot = save_snapshot(state)

                # Reheat — controlled by reheat_factor.
                #   reheat_factor=1.5 is mild, 3–5 is aggressive,
                #   10+ essentially restarts from high temperature.
                # Always uses the full factor; best state is saved so
                # we can always restore if the reheat overshoots.
                rf = self.reheat_factor
                T = max(best_T * rf, 1.0)

                # Recompute cooling for remaining budget
                remaining = max(1, (self.max_steps - step) // self.batch_size)
                cool_factor = max(
                    0.99,
                    (self.T_final / max(T, 0.01)) ** (1.0 / remaining))

                if self.verbose:
                    elapsed = time.time() - t_start
                    print(f"    Reheat #{reheat_count}, T={T:.3f}, "
                          f"best_mm={best_mm}, patience={adaptive_patience:,}, "
                          f"{elapsed:.1f}s")

            # ----------------------------------------------------------
            # Progress log
            # ----------------------------------------------------------
            if self.verbose and step > 0 and step % 500_000 < self.batch_size:
                elapsed = time.time() - t_start
                rate = total_accepted / max(total_attempted, 1)
                idp_str = ""
                if state.track_identical or state.w_identical > 0:
                    state.identical_pieces = state.count_identical_pieces()
                    idp_str = f", idp={state.identical_pieces}"
                print(f"    Step {step//1000:,}K: mm={state.mismatch_count}, "
                      f"best={best_mm}, T={T:.3f}, "
                      f"acc={rate:.2f}{idp_str}, {elapsed:.1f}s")

        # ----------------------------------------------------------
        # End of main loop: try repair on best state
        # ----------------------------------------------------------
        if (best_mm > 0
                and best_mm <= self.repair_threshold
                and best_snapshot is not None
                and repair_attempts < 3):
            if self.verbose:
                print(f"  End-of-run repair (best_mm={best_mm})...")
            restore_snapshot(state, best_snapshot)
            if repair_phase(state, verbose=self.verbose):
                return state

        if self.verbose:
            elapsed = time.time() - t_start
            idp = state.count_identical_pieces()
            print(f"  Restart {restart_idx}: max steps ({self.max_steps:,}) "
                  f"reached, best_mm={best_mm}, idp={idp}, {elapsed:.1f}s")
        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _calibrate_T0(self, engine: MoveEngine, n_samples: int = 500) -> float:
        """Estimate a good starting temperature by sampling move costs."""
        deltas = []
        for _ in range(n_samples):
            result = engine.propose_recolor_py()
            if result is not None:
                delta_E, undo = result
                deltas.append(abs(delta_E))
                engine.reject_recolor_py(undo)

        if not deltas:
            return 5.0

        deltas.sort()
        median_delta = deltas[len(deltas) // 2]
        T0 = median_delta / math.log(3)  # ~75% acceptance for median-cost move
        # Floor: ensure T0 is high enough to accept single-mismatch moves
        return max(T0, 10.0)

    def _partial_randomize(self, state: MCMCState, fraction: float = 0.3):
        """Randomize a fraction of all edges, then recompute everything."""
        n = state.n
        for i in range(n):
            for j in range(n - 1):
                if random.random() < fraction:
                    state.h_type[i, j] = random.randint(1, state.K)
                    state.h_dir[i, j] = random.randint(0, 1)
        for i in range(n - 1):
            for j in range(n):
                if random.random() < fraction:
                    state.v_type[i, j] = random.randint(1, state.K)
                    state.v_dir[i, j] = random.randint(0, 1)
        state.full_recompute_energy()

    def _warmup_numba(self, engine: MoveEngine, state: MCMCState):
        """Trigger Numba compilation with a tiny run, then revert state."""
        if self.verbose:
            print("  [Numba JIT compilation on first run…]", end=" ", flush=True)
        t0 = time.time()
        # Save state
        h_t = state.h_type.copy()
        h_d = state.h_dir.copy()
        v_t = state.v_type.copy()
        v_d = state.v_dir.copy()
        s1 = state.s1_pieces.copy()
        s2 = state.s2_pieces.copy()
        tf = state.type_freq.copy()

        # Run a tiny batch to trigger compilation
        engine.run_recolor_batch(10, 1.0)

        # Restore
        state.h_type[:] = h_t
        state.h_dir[:] = h_d
        state.v_type[:] = v_t
        state.v_dir[:] = v_d
        state.s1_pieces[:] = s1
        state.s2_pieces[:] = s2
        state.type_freq[:] = tf
        state.full_recompute_energy()

        if self.verbose:
            print(f"done ({time.time() - t0:.1f}s)")

    def _swap_burst(self, engine: MoveEngine, state: MCMCState,
                    n_steps: int = 3000):
        """Run a burst of mapping-swap + recolor moves to diversify.

        Only used during deep stagnation to escape local minima by
        exploring alternative mapping structures.
        """
        T_swap = 5.0
        for _ in range(n_steps):
            if random.random() < 0.3 and len(engine._interior) >= 2:
                result = engine.propose_mapping_swap()
                if result is not None:
                    delta_E, undo = result
                    if delta_E <= 0 or random.random() < math.exp(
                            -delta_E / max(T_swap, 1e-10)):
                        engine.accept_mapping_swap(undo)
                    else:
                        engine.reject_mapping_swap(undo)
            else:
                result = engine.propose_recolor_py()
                if result is not None:
                    delta_E, undo = result
                    if delta_E <= 0 or random.random() < math.exp(
                            -delta_E / max(T_swap, 1e-10)):
                        engine.accept_recolor_py(undo)
                    else:
                        engine.reject_recolor_py(undo)
        state.full_recompute_energy()
