"""
Visualize an MCMC-generated double-solution puzzle.

Produces (all saved into Images/<puzzle_folder>/):
  1. Matplotlib grid view (numbers + color-coded pieces) — grid.png
  2. SVG jigsaw outlines for S0 and S1 (Draw_sollution.py)
  3. SVG mapped jigsaw with background image (Draw_sol_test_mapped.py)
     — S0 original + S1 mapped arrangement, with or without outline

Usage:  Edit SOLUTION_NAME below, then run:
    python visualize_sol.py
"""

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image as PILImage
import os
import sys

# =====================================================================
#  SETTINGS — edit these
# =====================================================================

# Paste the solution name (without extension) — e.g. from the solver output
SOLUTION_NAME = "Solution_20_29_0_1771579531"

# Folder containing the .npy files
SOLUTIONS_DIR = "Solutions"

# Background image for jigsaw SVG drawings.
# Set to None to auto-generate a color gradient.
BACKGROUND_IMAGE = None  # e.g. "Puzzle_Solutions_after_diffusion/UV map.png"

# Draw SVG jigsaw pieces (requires svgwrite + svgpathtools)
DRAW_SVG = True

# Draw outlines on the mapped SVG pieces
DRAW_OUTLINE = True

# Show matplotlib window (set False to only save files)
SHOW_PLOT = False

# =====================================================================
#  Derived paths — no need to edit
# =====================================================================

def _parse_solution_name(name):
    """Parse 'Solution_{n}_{m}_{sol}_{uid}' → (n, m, sol_idx, uid)."""
    parts = name.replace(".npy", "").split("_")
    n = int(parts[1])
    m = int(parts[2])
    sol_idx = int(parts[3])
    uid = parts[4]
    return n, m, sol_idx, uid


n, m, sol_idx, uid = _parse_solution_name(SOLUTION_NAME)

S0_PATH = os.path.join(SOLUTIONS_DIR, f"Solution_{n}_{m}_0_{uid}.npy")
S1_PATH = os.path.join(SOLUTIONS_DIR, f"Solution_{n}_{m}_1_{uid}.npy")
MAP_PATH = os.path.join(SOLUTIONS_DIR, f"Mapping_{n}_{m}_{uid}.npy")

# Output folder: Images/<puzzle_folder>/
PUZZLE_FOLDER = f"Solution_{n}_{m}_{uid}"
OUTPUT_DIR = os.path.join("Images", PUZZLE_FOLDER)


# =====================================================================
#  Helpers
# =====================================================================

def legacy_to_draw_format(puzzle):
    """Convert MCMC legacy format (odd=outie, even=innie, all positive)
    to the Draw_sollution.py format (positive=outie, negative=innie).

    MCMC legacy:  0=flat, odd (2t-1)=outie, even (2t)=innie
    Draw format:  0=flat, +(2t-1)=outie, -(2t-1)=innie
    """
    out = puzzle.copy().astype(int)
    rows, cols, _ = out.shape
    for i in range(rows):
        for j in range(cols):
            for s in range(4):
                v = out[i, j, s]
                if v != 0 and v % 2 == 0:
                    out[i, j, s] = -(v - 1)
    return out


def ndarray_mapping_to_dict(mapping_arr, n):
    """Convert (n, n, 3) mapping array to legacy dict format.

    Returns dict: (y, x, 0) → (y2, x2, rotation)
    """
    d = {}
    for y in range(n):
        for x in range(n):
            y2, x2, rot = mapping_arr[y, x]
            d[(y, x, 0)] = (int(y2), int(x2), int(rot))
    return d


def identity_mapping(n):
    """Identity mapping dict: every piece stays in place, no rotation."""
    d = {}
    for y in range(n):
        for x in range(n):
            d[(y, x, 0)] = (y, x, 0)
    return d


def check_match(a, b):
    """Check if two adjacent sides match in legacy format."""
    if a == 0 and b == 0:
        return True
    if a == 0 or b == 0:
        return False
    lo, hi = min(a, b), max(a, b)
    return lo % 2 == 1 and hi % 2 == 0 and hi - lo == 1


def verify_and_print(puzzle, label):
    """Check adjacency matching and print results."""
    rows, cols = puzzle.shape[0], puzzle.shape[1]
    mismatches, total = 0, 0
    for i in range(rows):
        for j in range(cols):
            if j < cols - 1:
                total += 1
                if not check_match(puzzle[i, j, 1], puzzle[i, j + 1, 3]):
                    mismatches += 1
            if i < rows - 1:
                total += 1
                if not check_match(puzzle[i, j, 2], puzzle[i + 1, j, 0]):
                    mismatches += 1
    status = "PASS" if mismatches == 0 else "FAIL"
    print(f"  {label}: {mismatches}/{total} mismatches [{status}]")
    return mismatches


def generate_gradient_background(n, piece_size=43, save_path=None):
    """Generate a color-gradient background image for the puzzle.

    Each cell gets a unique color so you can visually track piece movement.
    """
    img_size = n * piece_size
    img = PILImage.new("RGB", (img_size, img_size))
    pixels = img.load()
    for py in range(img_size):
        for px in range(img_size):
            r = int(255 * py / img_size)
            g = int(255 * px / img_size)
            b = int(255 * (py + px) / (2 * img_size))
            pixels[px, py] = (r, g, b)
    if save_path:
        img.save(save_path)
    return save_path or img


# =====================================================================
#  Create output directory
# =====================================================================

os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"Output folder: {OUTPUT_DIR}/")


# =====================================================================
#  1. Load data
# =====================================================================

print(f"\nLoading solution: {SOLUTION_NAME}")
print(f"  n={n}, m={m}, uid={uid}")

s0 = np.load(S0_PATH)
s1 = np.load(S1_PATH)
mapping_arr = np.load(MAP_PATH)

print(f"\nAdjacency verification:")
verify_and_print(s0, "S0 (Solution 1)")
verify_and_print(s1, "S1 (Solution 2)")

mapping_dict = ndarray_mapping_to_dict(mapping_arr, n)


# =====================================================================
#  2. Matplotlib grid view
# =====================================================================

def make_color_grid(n, alpha=0.6):
    colors = np.zeros((n, n, 4))
    for i in range(n):
        for j in range(n):
            r = i / max(n - 1, 1)
            g = j / max(n - 1, 1)
            b = (i + j) / max(2 * (n - 1), 1)
            colors[i, j] = [r, g, b, alpha]
    return colors


def plot_puzzle(ax, puzzle, colors, title, mapping=None):
    """Draw a puzzle grid with connection numbers and piece colors."""
    rows, cols = puzzle.shape[0], puzzle.shape[1]
    piece_size = 1.0
    inv_map = None
    if mapping is not None:
        inv_map = {v[:2]: k for k, v in mapping.items()}

    for i in range(rows):
        for j in range(cols):
            rx = j * piece_size
            ry = (rows - 1 - i) * piece_size

            if inv_map is not None and (i, j) in inv_map:
                oy, ox = inv_map[(i, j)][:2]
                color = colors[oy, ox]
            else:
                color = colors[i, j]
                oy, ox = i, j

            rect = plt.Rectangle((rx, ry), piece_size, piece_size,
                                 facecolor=color, edgecolor='black', linewidth=1.5)
            ax.add_patch(rect)

            fs = max(4, min(8, 40 // max(rows, cols)))
            cx, cy = rx + 0.5, ry + 0.5
            top, right, bottom, left = puzzle[i, j]

            ax.text(cx, ry + 0.88, str(top), ha='center', va='center', fontsize=fs)
            ax.text(rx + 0.88, cy, str(right), ha='center', va='center', fontsize=fs)
            ax.text(cx, ry + 0.12, str(bottom), ha='center', va='center', fontsize=fs)
            ax.text(rx + 0.12, cy, str(left), ha='center', va='center', fontsize=fs)

            ax.text(cx, cy, f"({oy},{ox})", ha='center', va='center',
                    fontsize=max(3, fs - 1), color='white', fontweight='bold')

    ax.set_xlim(0, cols * piece_size)
    ax.set_ylim(0, rows * piece_size)
    ax.set_aspect('equal')
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.set_axis_off()


colors = make_color_grid(n)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(max(6, n * 1.2), max(4, n * 0.7)))
fig.suptitle(f"MCMC Puzzle  n={n}, m={m}  (uid={uid})", fontsize=13, fontweight='bold')

plot_puzzle(ax1, s0, colors, "Solution 1 (S0)")
plot_puzzle(ax2, s1, colors, "Solution 2 (S1)", mapping=mapping_dict)

plt.tight_layout()
grid_path = os.path.join(OUTPUT_DIR, "grid.png")
plt.savefig(grid_path, dpi=150, bbox_inches='tight')
print(f"\n  Saved grid view to {grid_path}")
if SHOW_PLOT:
    plt.show()
else:
    plt.close()


# =====================================================================
#  3. SVG jigsaw outlines (using Draw_sollution.py)
# =====================================================================

if DRAW_SVG:
    try:
        from Draw_sollution import JigsawPuzzle

        s0_draw = legacy_to_draw_format(s0)
        s1_draw = legacy_to_draw_format(s1)

        svg_s0 = os.path.join(OUTPUT_DIR, "S0_outline.svg")
        JigsawPuzzle(s0_draw.tolist()).draw(svg_s0)

        svg_s1 = os.path.join(OUTPUT_DIR, "S1_outline.svg")
        JigsawPuzzle(s1_draw.tolist()).draw(svg_s1)

    except ImportError as e:
        print(f"\n  Skipping SVG outline drawing (missing dependency: {e})")
    except Exception as e:
        print(f"\n  SVG outline drawing failed: {e}")


# =====================================================================
#  4. SVG mapped jigsaw (using Draw_sol_test_mapped.py)
# =====================================================================

if DRAW_SVG:
    try:
        from Draw_sol_test_mapped import JigsawPuzzle as MappedJigsawPuzzle

        s0_draw = legacy_to_draw_format(s0)

        # Resolve background image
        bg_path = BACKGROUND_IMAGE
        if bg_path is None or not os.path.exists(bg_path):
            # Auto-generate a gradient background
            bg_path = os.path.join(OUTPUT_DIR, "_gradient_bg.png")
            generate_gradient_background(n, piece_size=43, save_path=bg_path)
            print(f"  Generated gradient background: {bg_path}")

        # --- S0: original arrangement (identity mapping) ---
        svg_s0_mapped = os.path.join(OUTPUT_DIR, "S0_mapped.svg")
        puzzle_s0 = MappedJigsawPuzzle(s0_draw.tolist())
        puzzle_s0.draw(
            svg_s0_mapped,
            background=bg_path,
            mapping=identity_mapping(n),
            outline=DRAW_OUTLINE,
        )

        # --- S1: mapped arrangement (pieces moved by the mapping) ---
        svg_s1_mapped = os.path.join(OUTPUT_DIR, "S1_mapped.svg")
        puzzle_s1 = MappedJigsawPuzzle(s0_draw.tolist())
        puzzle_s1.draw(
            svg_s1_mapped,
            background=bg_path,
            mapping=mapping_dict,
            outline=DRAW_OUTLINE,
        )

    except ImportError as e:
        print(f"\n  Skipping mapped SVG drawing (missing dependency: {e})")
    except Exception as e:
        print(f"\n  Mapped SVG drawing failed: {e}")

print(f"\nAll outputs saved to: {OUTPUT_DIR}/")
print("Done!")
