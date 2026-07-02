"""
Quick visual check for MCMC-generated solutions.

Usage:
    python mcmc_solver/visualize.py                         # auto-detect latest
    python mcmc_solver/visualize.py --id 1771503632         # specific solution id
    python mcmc_solver/visualize.py --s0 path/to/S0.npy --s1 path/to/S1.npy --map path/to/Map.npy
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import argparse
import glob
import os
import re


def load_mcmc_solution(solution_dir="Solutions", uid=None):
    """Load an MCMC solution by uid, or auto-detect the latest one."""
    if uid is None:
        # Find the latest MCMC file by timestamp in filename
        pattern = os.path.join(solution_dir, "Solution_*_0_*.npy")
        files = glob.glob(pattern)
        if not files:
            raise FileNotFoundError(f"No solution files found in {solution_dir}/")
        # Extract uid (last number) and pick the largest
        def extract_uid(f):
            m = re.search(r'_(\d+)\.npy$', f)
            return int(m.group(1)) if m else 0
        files.sort(key=extract_uid)
        latest = files[-1]
        m = re.search(r'Solution_(\d+)_(\d+)_0_(\d+)\.npy$', os.path.basename(latest))
        n, m_val, uid = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        # Find files matching this uid
        pattern = os.path.join(solution_dir, f"Solution_*_*_0_{uid}.npy")
        files = glob.glob(pattern)
        if not files:
            raise FileNotFoundError(f"No S0 file found for uid={uid}")
        m = re.search(r'Solution_(\d+)_(\d+)_0_', os.path.basename(files[0]))
        n, m_val = int(m.group(1)), int(m.group(2))

    s0_path = os.path.join(solution_dir, f"Solution_{n}_{m_val}_0_{uid}.npy")
    s1_path = os.path.join(solution_dir, f"Solution_{n}_{m_val}_1_{uid}.npy")
    map_path = os.path.join(solution_dir, f"Mapping_{n}_{m_val}_{uid}.npy")

    s0 = np.load(s0_path)
    s1 = np.load(s1_path)
    mapping = np.load(map_path)

    print(f"Loaded: n={n}, m={m_val}, uid={uid}")
    print(f"  S0: {s0_path}")
    print(f"  S1: {s1_path}")
    print(f"  Map: {map_path}")

    return s0, s1, mapping, n


def make_color_grid(n, alpha=0.6):
    """Generate a color gradient grid for n×n pieces."""
    colors = np.zeros((n, n, 4))
    for i in range(n):
        for j in range(n):
            r = i / max(n - 1, 1)
            g = j / max(n - 1, 1)
            b = (i + j) / max(2 * (n - 1), 1)
            colors[i, j] = [r, g, b, alpha]
    return colors


def plot_puzzle(ax, puzzle, colors, title, labels=None):
    """Draw a puzzle grid with connection numbers and piece colors."""
    n = puzzle.shape[0]
    piece_size = 1.0

    for i in range(n):
        for j in range(n):
            top, right, bottom, left = puzzle[i, j]
            rx = j * piece_size
            ry = (n - 1 - i) * piece_size

            color = colors[i, j] if labels is None else colors[labels[i, j, 0], labels[i, j, 1]]

            rect = plt.Rectangle((rx, ry), piece_size, piece_size,
                                 facecolor=color, edgecolor='black', linewidth=1.5)
            ax.add_patch(rect)

            fs = max(4, min(8, 40 // n))
            cx, cy = rx + 0.5, ry + 0.5

            # Side values
            ax.text(cx, ry + 0.88, str(top), ha='center', va='center', fontsize=fs)
            ax.text(rx + 0.88, cy, str(right), ha='center', va='center', fontsize=fs)
            ax.text(cx, ry + 0.12, str(bottom), ha='center', va='center', fontsize=fs)
            ax.text(rx + 0.12, cy, str(left), ha='center', va='center', fontsize=fs)

            # Piece origin label
            if labels is not None:
                oy, ox = labels[i, j, 0], labels[i, j, 1]
                ax.text(cx, cy, f"({oy},{ox})", ha='center', va='center',
                        fontsize=max(3, fs - 1), color='white', fontweight='bold')
            else:
                ax.text(cx, cy, f"({i},{j})", ha='center', va='center',
                        fontsize=max(3, fs - 1), color='white', fontweight='bold')

    ax.set_xlim(0, n * piece_size)
    ax.set_ylim(0, n * piece_size)
    ax.set_aspect('equal')
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.set_axis_off()


def verify_matches(puzzle, label):
    """Check adjacency matching and print results."""
    n = puzzle.shape[0]
    mismatches = 0
    total = 0
    for i in range(n):
        for j in range(n):
            if j < n - 1:
                total += 1
                if puzzle[i, j, 1] + puzzle[i, j + 1, 3] != 0:
                    mismatches += 1
            if i < n - 1:
                total += 1
                if puzzle[i, j, 2] + puzzle[i + 1, j, 0] != 0:
                    mismatches += 1
    status = "PASS" if mismatches == 0 else "FAIL"
    print(f"  {label}: {mismatches}/{total} mismatches [{status}]")
    return mismatches


def main():
    parser = argparse.ArgumentParser(description="Visualize MCMC puzzle solution")
    parser.add_argument("--id", type=int, default=None, help="Solution UID")
    parser.add_argument("--s0", type=str, default=None, help="Path to S0 .npy")
    parser.add_argument("--s1", type=str, default=None, help="Path to S1 .npy")
    parser.add_argument("--map", type=str, default=None, help="Path to mapping .npy")
    parser.add_argument("--dir", type=str, default="Solutions", help="Solutions directory")
    args = parser.parse_args()

    if args.s0 and args.s1 and args.map:
        s0 = np.load(args.s0)
        s1 = np.load(args.s1)
        mapping = np.load(args.map)
        n = s0.shape[0]
    else:
        s0, s1, mapping, n = load_mcmc_solution(args.dir, args.id)

    # Convert mapping array to label arrays for S2
    # mapping[y,x] = [y2, x2, rot] means S1 piece at (y,x) goes to S2 pos (y2,x2)
    # For S2 visualization: at S2 position (y2,x2), the piece came from S1 (y,x)
    s2_labels = np.zeros((n, n, 2), dtype=np.int32)
    for y in range(n):
        for x in range(n):
            y2, x2, rot = mapping[y, x]
            s2_labels[y2, x2] = [y, x]

    # Colors based on S1 position
    colors = make_color_grid(n)

    print("\nAdjacency verification:")
    # The saved format uses legacy encoding where matching = values sum to 0
    # Actually let me check: MCMC convert uses signed_to_legacy which produces
    # odd (outie) / even (innie). Matching rule: odd + even of same type = 0?
    # No — in legacy format matching is: if one is 2t-1 and neighbor is 2t, they match.
    # But the saved arrays use the signed representation converted to legacy...
    # Let me just check with a simple rule.

    # Actually the convert module stores values where matching pairs sum:
    # outie = 2t-1, innie = 2t → (2t-1) + (2t) ≠ 0
    # So the legacy format doesn't use sum-to-zero. Let me check what the 
    # actual saved values look like.
    print(f"\n  S0 sample piece (0,0): {s0[0,0]}")
    print(f"  S0 sample piece (0,1): {s0[0,1]}")

    # Check using the rule: adjacent sides match if one is odd and the other is even
    # and they differ by 1 (i.e. {2t-1, 2t} pair), OR both are 0.
    def check_match(a, b):
        if a == 0 and b == 0:
            return True
        if a == 0 or b == 0:
            return False
        # {2t-1, 2t} pair: sorted should be [odd, even] with diff 1
        lo, hi = min(a, b), max(a, b)
        return lo % 2 == 1 and hi % 2 == 0 and hi - lo == 1

    mm_s0, mm_s1 = 0, 0
    total = 0
    for i in range(n):
        for j in range(n):
            if j < n - 1:
                total += 1
                if not check_match(s0[i, j, 1], s0[i, j + 1, 3]):
                    mm_s0 += 1
                if not check_match(s1[i, j, 1], s1[i, j + 1, 3]):
                    mm_s1 += 1
            if i < n - 1:
                total += 1
                if not check_match(s0[i, j, 2], s0[i + 1, j, 0]):
                    mm_s0 += 1
                if not check_match(s1[i, j, 2], s1[i + 1, j, 0]):
                    mm_s1 += 1

    print(f"  S0 (Solution 1): {mm_s0}/{total} mismatches [{'PASS' if mm_s0==0 else 'FAIL'}]")
    print(f"  S1 (Solution 2): {mm_s1}/{total} mismatches [{'PASS' if mm_s1==0 else 'FAIL'}]")

    # --- Plot ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(max(6, n * 1.2), max(4, n * 0.7)))
    fig.suptitle(f"MCMC Double-Solution Puzzle  (n={n})", fontsize=14, fontweight='bold')

    plot_puzzle(ax1, s0, colors, "Solution 1 (S0)")
    plot_puzzle(ax2, s1, colors, "Solution 2 (S1)", labels=s2_labels)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
