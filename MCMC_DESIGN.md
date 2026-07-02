# MCMC Double-Solution Puzzle Generator — Design Document

## 1. Core Insight: Why MCMC on Edge Colors with a Fixed Mapping

### The Convergence Problem
A naïve MCMC over (edge-colors + mapping) will collapse to trivial solutions:
all edges the same color → all interior pieces identical → any mapping works
→ energy = 0 but puzzle is trivially solvable. This is the deepest basin in the
landscape and the MCMC will find it.

### The Fix: Decouple Mapping from Color Search
**Fix the mapping first, then search only for edge colorings that make S2 valid.**

Why this works:
- **S1 is valid by construction.** When we assign colors directly to the *edges*
  of the grid (not to piece sides), adjacency matching in S1 is automatic —
  each edge produces a paired outie/innie on its two cells.
- **S2 validity is the only objective.** The mapping rearranges S1's pieces; we
  need S2's adjacent pieces to also match. This is a well-defined constraint
  satisfaction problem over edge colors.
- **Trivial collapse is blocked.** A fixed non-identity mapping means "all pieces
  identical" is NOT automatically valid in S2 for boundary pieces (a corner piece
  at one corner must match different neighbors than at another corner). The
  diversity emerges naturally from satisfying the mapping constraints.

### What About Piece Moves?
As a secondary mechanism (low-probability move), we allow **mapping mutations**:
swap two pieces' S2 target positions (same category: corner↔corner, edge↔edge,
interior↔interior). This helps escape mappings that are locally unsatisfiable
without giving up on the overall dissimilarity.

---

## 2. Problem Formulation

### 2.1 Grid and Edges

An $n \times n$ puzzle has:
- **Boundary edges**: sides of cells touching the grid border → always type 0 (flat)
- **Internal edges**: shared between two adjacent cells
  - Horizontal: $n \times (n-1)$ edges (between $(i,j)$ and $(i,j+1)$)
  - Vertical: $(n-1) \times n$ edges (between $(i,j)$ and $(i+1,j)$)
  - Total internal: $2n(n-1)$

| $n$ | Internal edges |
|-----|---------------|
| 10  | 180           |
| 20  | 760           |
| 30  | 1,740         |
| 50  | 4,900         |

### 2.2 Edge Orientation (Innie/Outie)

Each internal edge has:
- **Base type** $t \in \{1, \ldots, K\}$ — the shape profile of the connection
- **Direction** $d \in \{0, 1\}$ — which cell gets the "outie" (tab) and which gets the "innie" (blank)

This determines the **signed side values** on the two cells:

```
Horizontal edge between (i,j) and (i,j+1), base type t, direction d:
  d=0: cell (i,j) right = +t (outie),  cell (i,j+1) left = -t (innie)
  d=1: cell (i,j) right = -t (innie),  cell (i,j+1) left = +t (outie)

Vertical edge between (i,j) and (i+1,j), base type t, direction d:
  d=0: cell (i,j) bottom = +t (outie), cell (i+1,j) top = -t (innie)
  d=1: cell (i,j) bottom = -t (innie), cell (i+1,j) top = +t (outie)

Boundary sides: value = 0 (flat)
```

**Matching rule**: Two adjacent sides match iff their signed values sum to zero:
$$\text{match}(c_1, c_2) \iff c_1 + c_2 = 0$$

This works for all cases:
- Interior: $+t + (-t) = 0$ ✓
- Boundary: $0 + 0 = 0$ ✓
- Mismatch: $+t_1 + (-t_2) \neq 0$ when $t_1 \neq t_2$ ✓
- Wrong polarity: $+t + (+t) = 2t \neq 0$ ✓

**Conversion to current codebase format** (for output/visualization):
- $+t \to 2t - 1$ (odd number, outie)
- $-t \to 2t$ (even number, innie)
- $0 \to 0$ (flat)

The total number of side-value types is $m = 2K + 1$ (matching the existing code's convention).

### 2.3 Pieces

A piece at cell $(i,j)$ is the 4-tuple of its signed side values:
$$\text{piece}(i,j) = [\text{top}, \text{right}, \text{bottom}, \text{left}]$$

These are determined entirely by the 2–4 edges incident to cell $(i,j)$ plus any
boundary sides (which are 0).

### 2.4 Mapping

A mapping $\pi$ assigns each S1 cell to an S2 cell with a rotation:
$$\pi: (y, x) \mapsto (y', x', r) \quad \text{where } r \in \{0,1,2,3\}$$

Constraints on $\pi$:
- **Bijective**: every S2 position is used exactly once
- **Category-preserving**: corners → corners, edges → edges, interior → interior
- **Rotation-correct**: the rotation $r$ aligns the flat sides with the target position's boundary

The piece in S2 at position $(y', x')$ with rotation $r$ is:
$$\text{s2\_piece}(y', x') = \text{rotate}(\text{piece}(y, x),\, r) \quad \text{where } (y', x', r) = \pi(y, x)$$

Rotation by $r$ clockwise shifts the sides:
$$\text{rotate}([t,r,b,l],\, 1) = [l, t, r, b]$$

### 2.5 The Optimization Problem

**Given**: $n$, $K$, and a fixed mapping $\pi$

**Find**: An assignment of $(t, d)$ to each of the $2n(n-1)$ internal edges

**Such that**: 
1. All adjacent pairs in S2 match: $\text{s2}[i][j][\text{side}] + \text{s2}[\text{neighbor}][\text{opp\_side}] = 0$
2. At least $K_{min}$ distinct base types are used
3. No base type dominates excessively

---

## 3. Energy Function

$$E = w_1 \cdot M_2 + w_2 \cdot E_{\text{diversity}} + w_3 \cdot E_{\text{balance}}$$

### 3.1 Mismatch Count $M_2$

The number of S2 internal adjacencies where touching sides don't match:

$$M_2 = \sum_{\substack{(i,j),(i',j') \\ \text{adjacent in S2}}} \mathbb{1}\left[\text{s2}[i][j][s] + \text{s2}[i'][j'][s'] \neq 0\right]$$

Range: $0 \leq M_2 \leq 2n(n-1)$. **Target: $M_2 = 0$.**

Note: S1 mismatches are always 0 by construction (edge-based representation).

### 3.2 Diversity Penalty $E_{\text{diversity}}$

Prevent collapse to too few edge types:

$$E_{\text{diversity}} = \max(0,\; K_{min} - K_{\text{used}})^2$$

Where $K_{\text{used}}$ = number of distinct base types with at least one edge,
and $K_{min}$ is typically $K$ (use all types) or $\lfloor 0.8K \rfloor$.

### 3.3 Balance Penalty $E_{\text{balance}}$

Prevent any single type from dominating:

$$E_{\text{balance}} = \sum_{t=1}^{K} \max\left(0,\; f_t - f_{\max}\right)$$

Where $f_t$ = number of edges using base type $t$, and
$f_{\max} = \lceil 1.5 \cdot \frac{2n(n-1)}{K} \rceil$ (50% above uniform).

### 3.4 Weight Recommendations

| Weight | Value | Rationale |
|--------|-------|-----------|
| $w_1$ | 10.0 | Dominant: S2 validity is the primary goal |
| $w_2$ | 1.0 | Secondary: keep diversity pressure |
| $w_3$ | 0.5 | Tertiary: gentle balance enforcement |

Once $M_2 = 0$, the solution is valid regardless of diversity/balance terms.
Those terms only guide the search away from trivial basins.

---

## 4. State Representation & Data Structures

### 4.1 Core State

```python
class MCMCState:
    # Edge colors: base type ∈ {1..K}, direction ∈ {0,1}
    h_type: np.ndarray  # shape (n, n-1), dtype=int8,  values in [1, K]
    h_dir:  np.ndarray  # shape (n, n-1), dtype=int8,  values in {0, 1}
    v_type: np.ndarray  # shape (n-1, n), dtype=int8,  values in [1, K]
    v_dir:  np.ndarray  # shape (n-1, n), dtype=int8,  values in {0, 1}
    
    # Cached derived data (always kept in sync)
    s1_pieces: np.ndarray  # shape (n, n, 4), signed side values
    s2_pieces: np.ndarray  # shape (n, n, 4), signed side values
    
    # Per-edge-type frequency counters (for fast diversity/balance)
    type_freq: np.ndarray  # shape (K+1,), freq[t] = count of edges with base type t
    
    # Cached energy components
    mismatch_count: int
    diversity_penalty: float
    balance_penalty: float
```

### 4.2 Mapping Tables (Precomputed Once)

```python
class MappingInfo:
    # Forward: S1 position → S2 position + rotation
    fwd: dict  # (y, x) → (y2, x2, rotation)
    
    # Inverse: S2 position → S1 position + rotation  
    inv: dict  # (y2, x2) → (y1, x1, rotation)
```

### 4.3 Piece Computation from Edges

```python
def get_side_value(base_type, direction, cell_is_first):
    """
    cell_is_first: True if this cell is the "first" in the edge definition
      (left for horizontal, top for vertical)
    """
    if base_type == 0:
        return 0
    if cell_is_first:
        return +base_type if direction == 0 else -base_type
    else:
        return -base_type if direction == 0 else +base_type

def compute_piece(i, j, h_type, h_dir, v_type, v_dir, n):
    """Compute signed side values [top, right, bottom, left] for cell (i,j)"""
    # Top
    if i == 0:
        top = 0
    else:
        top = get_side_value(v_type[i-1, j], v_dir[i-1, j], cell_is_first=False)
    
    # Right
    if j == n - 1:
        right = 0
    else:
        right = get_side_value(h_type[i, j], h_dir[i, j], cell_is_first=True)
    
    # Bottom
    if i == n - 1:
        bottom = 0
    else:
        bottom = get_side_value(v_type[i, j], v_dir[i, j], cell_is_first=True)
    
    # Left
    if j == 0:
        left = 0
    else:
        left = get_side_value(h_type[i, j-1], h_dir[i, j-1], cell_is_first=False)
    
    return [top, right, bottom, left]
```

### 4.4 Rotation

```python
def rotate_piece(piece, r):
    """Rotate piece r times 90° clockwise: [t,r,b,l] → [l,t,r,b]"""
    p = list(piece)
    for _ in range(r % 4):
        p = [p[3], p[0], p[1], p[2]]
    return p
```

---

## 5. Move Operators

### 5.1 Primary Move: Single-Edge Recolor (95% of moves)

**Proposal**: Pick a random internal edge. Assign a new random $(t', d')$ where
$t' \in \{1, \ldots, K\}$, $d' \in \{0, 1\}$.

**Affected cells in S1**: Exactly 2 (the two cells sharing the edge).

**Affected cells in S2**: Exactly 2 (the mapped positions of those 2 cells).

**Delta computation**:

```
RECOLOR_EDGE(edge):
    (cell_A, cell_B) ← the two S1 cells sharing this edge
    s2_pos_A ← mapping.fwd[cell_A]  →  (yA', xA', rA)
    s2_pos_B ← mapping.fwd[cell_B]  →  (yB', xB', rB)
    
    # Collect all S2 adjacency pairs touching positions A' or B'
    affected_pairs ← unique S2 adjacency pairs involving (yA', xA') or (yB', xB')
    
    old_mismatches ← count mismatches in affected_pairs using current s2_pieces
    
    # Tentatively update
    change edge type/dir
    recompute s1_pieces for cell_A and cell_B
    recompute s2_pieces for (yA', xA') and (yB', xB')
    
    new_mismatches ← count mismatches in affected_pairs using updated s2_pieces
    
    delta_M2 ← new_mismatches - old_mismatches
    delta_diversity ← recompute diversity change (type_freq update)
    delta_balance ← recompute balance change
    
    delta_E ← w1 * delta_M2 + w2 * delta_diversity + w3 * delta_balance
    
    RETURN delta_E, undo_info
```

**Complexity**: $O(1)$ per move (at most 8 adjacency checks).

**Adjacency enumeration for delta**:
```
For S2 position P = (y', x'):
  neighbors = {(y'-1,x'), (y',x'+1), (y'+1,x'), (y',x'-1)} ∩ grid
  For each neighbor Q:
    this is an affected adjacency pair (P, Q) with specific sides:
      P above Q → check P.bottom + Q.top
      P left of Q → check P.right + Q.left
      etc.
```

**Important**: If $s2\_pos_A$ and $s2\_pos_B$ are adjacent in S2, their shared
adjacency should only be counted once. Collect all affected $(P,Q)$ pairs into a
**set** to deduplicate.

### 5.2 Secondary Move: Mapping Swap (5% of moves)

**Proposal**: Pick two cells of the **same category** (both corners, both edges,
or both interior). Swap their S2 target positions.

```
SWAP_MAPPING(cell_A, cell_B):
    (yA', xA', rA) ← mapping.fwd[cell_A]
    (yB', xB', rB) ← mapping.fwd[cell_B]
    
    # Swap targets (recalculate rotations for new positions)
    new_rA ← calculate_rotation(cell_A, (yB', xB'))
    new_rB ← calculate_rotation(cell_B, (yA', xA'))
    
    mapping.fwd[cell_A] ← (yB', xB', new_rA)
    mapping.fwd[cell_B] ← (yA', xA', new_rB)
    
    # All S2 adjacencies around (yA', xA') and (yB', xB') are affected
    # Compute delta_E the same way as recolor
```

This move changes **which** pieces sit at two S2 positions but doesn't change
any edge colors. It's more disruptive but helps escape bad mappings.

**Complexity**: $O(1)$ per move.

### 5.3 Optional Move: Chain Recolor (for escaping local minima)

**Proposal**: Pick a path of $L$ consecutive edges in S1 (horizontal or vertical
strip). Recolor all $L$ edges simultaneously.

This is a Swendsen-Wang / Wolff-style cluster move. It helps break up long-range
correlations where no single-edge change can reduce energy.

**When to use**: Only when the algorithm is stuck (acceptance rate < 1% for many
steps). Not needed initially.

**Complexity**: $O(L)$ per move.

---

## 6. Acceptance Criterion & Temperature Schedule

### 6.1 Metropolis-Hastings Acceptance

$$P(\text{accept}) = \min\left(1,\; \exp\left(-\frac{\Delta E}{T}\right)\right)$$

- $\Delta E < 0$: always accept (energy decreases)
- $\Delta E = 0$: always accept (enables random walk on plateaus)
- $\Delta E > 0$: accept with probability $\exp(-\Delta E / T)$

### 6.2 Adaptive Temperature Schedule

Instead of a fixed geometric cooling schedule (which requires tuning $T_0$ and
$\alpha$), use an **adaptive** scheme that targets a desired acceptance rate:

```
ADAPTIVE_TEMPERATURE:
    Track acceptance rate over last W = 1000 moves
    Target acceptance rate: τ = 0.25
    
    every W steps:
        actual_rate = accepted / W
        if actual_rate > τ + 0.05:
            T ← T * 0.95     # Cool down (accepting too much)
        elif actual_rate < τ - 0.05:
            T ← T * 1.05     # Heat up (stuck)
        
        // Also clamp temperature within reasonable range:
        T ← clamp(T, T_min=0.01, T_max=100.0)
```

### 6.3 Initial Temperature

Start with $T_0$ high enough that ~60-80% of random moves are accepted:

```
CALIBRATE_T0:
    Apply 1000 random moves, collect |delta_E| values
    T0 ← median(|delta_E|) / ln(3)    # ~75% acceptance for median-cost moves
```

### 6.4 Convergence Detection

```
CONVERGED if:
    mismatch_count == 0
    AND diversity_penalty == 0  (optional, can be relaxed)

STUCK if:
    best_energy has not improved for PATIENCE = 50,000 steps
    → trigger restart (see Section 8)
```

---

## 7. Initialization Strategy

### 7.1 Mapping Generation

Use a modified version of the existing `mapping.py`:

```
GENERATE_MAPPING(n):
    corners ← [(0,0), (0,n-1), (n-1,0), (n-1,n-1)]
    edges ← border cells excluding corners
    interior ← all non-border cells
    
    # Shuffle within each category
    corner_targets ← random permutation of corners
    edge_targets ← random permutation of edges
    interior_targets ← random permutation of interior
    
    # Assign with correct rotation
    for each (source, target) pair:
        rotation ← calculate_rotation(source, target, n)
        mapping[source] = (target, rotation)
```

**Quality check**: Verify that the mapping doesn't contain fixed points
(piece staying at same position with rotation 0). If too many fixed points,
regenerate. We want **at least** 80% of pieces to change position or rotation.

### 7.2 Edge Color Initialization

**Option A — Uniform Random** (recommended for first attempt):
```
for each internal edge:
    base_type ← random.randint(1, K)
    direction ← random.randint(0, 1)
```

**Option B — Guided by S2 constraints** (faster convergence, more complex):
```
for each S2 internal adjacency (P, Q):
    # Find which S1 edges contribute to P and Q's touching sides
    # Set those edges to values that would satisfy this S2 adjacency
    # May create conflicts — resolve greedily
```

**Recommendation**: Start with Option A. It's simpler, and the MCMC should handle
convergence. If convergence is too slow, implement Option B.

### 7.3 Frequency Table Initialization

After setting edge colors:
```
type_freq = zeros(K+1)
for each internal edge with base_type t:
    type_freq[t] += 1
```

---

## 8. Restart & Multi-Level Strategy

### Level 0: Core MCMC Run

Run up to `MAX_STEPS` (default: $10 \times n^4$) MCMC steps with adaptive temperature.

### Level 1: Reheat (After Stagnation)

If stuck (no improvement for `PATIENCE` steps):
1. Set $T \leftarrow 5 \times T_{\text{current}}$ (large temperature spike)
2. Continue for `PATIENCE / 2` steps
3. Resume adaptive cooling

Reheats: up to 5 per run.

### Level 2: Partial Randomization

After 5 failed reheats:
1. Keep the best-so-far edge coloring
2. Randomly recolor 30% of edges (chosen uniformly)
3. Reset temperature to $T_0$
4. Restart Level 0

Partial restarts: up to 10 per mapping.

### Level 3: New Mapping

After 10 failed partial restarts:
1. Generate a completely new random mapping
2. Reset edge colors (uniform random)
3. Restart from Level 0

Mapping attempts: up to `MAX_MAPPING_ATTEMPTS` (default: 20).

### Summary Flow

```
for mapping_attempt in range(MAX_MAPPING_ATTEMPTS):
    mapping ← generate_random_mapping(n)
    
    for restart in range(MAX_RESTARTS):
        if restart > 0:
            partially_randomize_edges(fraction=0.3)
        
        state ← initialize_or_keep_edges(K)
        T ← calibrate_T0(state)
        best_E ← state.energy
        stagnation ← 0
        reheats ← 0
        
        for step in range(MAX_STEPS):
            delta_E, undo ← propose_move(state)
            
            if accept(delta_E, T):
                apply_move(state)
                if state.energy < best_E:
                    best_E = state.energy
                    stagnation = 0
                    if best_E == 0:
                        RETURN state  # SUCCESS!
            else:
                revert_move(state, undo)
            
            stagnation += 1
            update_temperature(T)
            
            if stagnation > PATIENCE:
                if reheats < 5:
                    T *= 5
                    reheats += 1
                    stagnation = 0
                else:
                    break  # Go to next restart
    
    print(f"Mapping {mapping_attempt} failed, trying new mapping")

RETURN None  # Failed
```

---

## 9. Complete Implementation Structure

### 9.1 File Layout

```
mcmc_solver/
    __init__.py
    state.py            # MCMCState class, edge/piece data structures
    mapping.py           # Mapping generation (reuse + improve existing)
    energy.py            # Energy function components
    moves.py             # Move proposal, delta computation, apply/revert
    solver.py            # Main MCMC loop, temperature, restarts
    verify.py            # SAT-based uniqueness verification
    convert.py           # Convert MCMC output to existing format
    main.py              # Entry point, CLI arguments
```

### 9.2 Class: `MCMCState`  (state.py)

```python
import numpy as np

class MCMCState:
    def __init__(self, n, K, mapping_fwd, mapping_inv):
        self.n = n
        self.K = K
        
        # Mapping (fixed)
        self.map_fwd = mapping_fwd   # dict: (y,x) → (y2,x2,rot)
        self.map_inv = mapping_inv   # dict: (y2,x2) → (y,x,rot)
        
        # Edge state: random initialization
        self.h_type = np.random.randint(1, K+1, size=(n, n-1), dtype=np.int8)
        self.h_dir  = np.random.randint(0, 2, size=(n, n-1), dtype=np.int8)
        self.v_type = np.random.randint(1, K+1, size=(n-1, n), dtype=np.int8)
        self.v_dir  = np.random.randint(0, 2, size=(n-1, n), dtype=np.int8)
        
        # Type frequency tracker
        self.type_freq = np.zeros(K+1, dtype=np.int32)
        self._init_freq()
        
        # Cached pieces
        self.s1_pieces = np.zeros((n, n, 4), dtype=np.int16)
        self.s2_pieces = np.zeros((n, n, 4), dtype=np.int16)
        self.recompute_all_pieces()
        
        # Cached energy
        self.mismatch_count = self.full_mismatch_count()
        self.diversity_pen = self.compute_diversity_penalty()
        self.balance_pen = self.compute_balance_penalty()
    
    def _init_freq(self):
        """Count frequency of each base type across all edges"""
        self.type_freq[:] = 0
        for t in self.h_type.flat:
            self.type_freq[t] += 1
        for t in self.v_type.flat:
            self.type_freq[t] += 1
    
    def get_piece_s1(self, i, j):
        """Compute [top, right, bottom, left] signed side values for S1 cell (i,j)"""
        n = self.n
        # Top
        top = 0 if i == 0 else self._side_val(self.v_type[i-1,j], self.v_dir[i-1,j], False)
        # Right
        right = 0 if j == n-1 else self._side_val(self.h_type[i,j], self.h_dir[i,j], True)
        # Bottom
        bottom = 0 if i == n-1 else self._side_val(self.v_type[i,j], self.v_dir[i,j], True)
        # Left
        left = 0 if j == 0 else self._side_val(self.h_type[i,j-1], self.h_dir[i,j-1], False)
        return [top, right, bottom, left]
    
    @staticmethod
    def _side_val(base_type, direction, is_first_cell):
        """
        Compute signed side value.
        is_first_cell: True = top/left cell of the edge pair, False = bottom/right
        Convention: direction=0 → first cell gets +t (outie), second gets -t (innie)
        """
        if is_first_cell:
            return int(base_type) if direction == 0 else -int(base_type)
        else:
            return -int(base_type) if direction == 0 else int(base_type)
    
    def recompute_all_pieces(self):
        """Full recompute of S1 and S2 piece arrays"""
        n = self.n
        for i in range(n):
            for j in range(n):
                self.s1_pieces[i, j] = self.get_piece_s1(i, j)
        
        for i in range(n):
            for j in range(n):
                sy, sx, rot = self.map_inv[(i, j)]
                self.s2_pieces[i, j] = self._rotate(self.s1_pieces[sy, sx], rot)
    
    @staticmethod
    def _rotate(piece, r):
        """Rotate piece r times 90° clockwise"""
        p = list(piece)
        for _ in range(r % 4):
            p = [p[3], p[0], p[1], p[2]]
        return p
    
    def full_mismatch_count(self):
        """Count all S2 adjacency mismatches"""
        n, s2 = self.n, self.s2_pieces
        count = 0
        for i in range(n):
            for j in range(n):
                # Right neighbor
                if j < n - 1:
                    if s2[i, j, 1] + s2[i, j+1, 3] != 0:
                        count += 1
                # Bottom neighbor
                if i < n - 1:
                    if s2[i, j, 2] + s2[i+1, j, 0] != 0:
                        count += 1
        return count
    
    def compute_diversity_penalty(self):
        """Penalty for using too few distinct types"""
        K_used = np.count_nonzero(self.type_freq[1:])  # types 1..K
        K_min = max(1, int(0.8 * self.K))
        return max(0, K_min - K_used) ** 2
    
    def compute_balance_penalty(self):
        """Penalty for type imbalance"""
        total_edges = 2 * self.n * (self.n - 1)
        f_max = int(np.ceil(1.5 * total_edges / self.K))
        excess = np.maximum(0, self.type_freq[1:] - f_max)
        return int(np.sum(excess))
    
    @property
    def energy(self):
        return 10.0 * self.mismatch_count + 1.0 * self.diversity_pen + 0.5 * self.balance_pen
```

### 9.3 Class: `MoveEngine`  (moves.py)

```python
import random
import numpy as np

# Side index constants
TOP, RIGHT, BOTTOM, LEFT = 0, 1, 2, 3

# Neighbor directions: (dy, dx, my_side, their_side)
NEIGHBORS = [(-1, 0, TOP, BOTTOM), (0, 1, RIGHT, LEFT),
             (1, 0, BOTTOM, TOP), (0, -1, LEFT, RIGHT)]


class MoveEngine:
    def __init__(self, state):
        self.state = state
        self.n = state.n
    
    def propose_recolor(self):
        """
        Propose changing one random edge's type and direction.
        Returns (delta_E, undo_data) or None if move is trivial.
        """
        s = self.state
        n = s.n
        
        # Pick random edge
        total_h = n * (n - 1)
        total_v = (n - 1) * n
        edge_idx = random.randrange(total_h + total_v)
        
        if edge_idx < total_h:
            # Horizontal edge
            ei, ej = divmod(edge_idx, n - 1)
            is_horiz = True
            old_t, old_d = int(s.h_type[ei, ej]), int(s.h_dir[ei, ej])
            cell_A, cell_B = (ei, ej), (ei, ej + 1)
        else:
            # Vertical edge
            vidx = edge_idx - total_h
            ei, ej = divmod(vidx, n)
            is_horiz = False
            old_t, old_d = int(s.v_type[ei, ej]), int(s.v_dir[ei, ej])
            cell_A, cell_B = (ei, ej), (ei + 1, ej)
        
        # New random type/dir
        new_t = random.randint(1, s.K)
        new_d = random.randint(0, 1)
        if (new_t, new_d) == (old_t, old_d):
            return None  # Skip identity moves
        
        # --- Compute delta ---
        
        # S2 positions of affected cells
        s2A = s.map_fwd[cell_A]  # (y', x', rot)
        s2B = s.map_fwd[cell_B]
        
        # Collect affected S2 adjacency pairs (as a set to avoid duplicates)
        affected = self._get_affected_adjacencies(s2A[:2], s2B[:2])
        
        # Count old mismatches for affected pairs
        old_mm = self._count_mismatches_at(affected)
        
        # Save old piece data for undo
        old_s1A = list(s.s1_pieces[cell_A])
        old_s1B = list(s.s1_pieces[cell_B])
        old_s2A = list(s.s2_pieces[s2A[0], s2A[1]])
        old_s2B = list(s.s2_pieces[s2B[0], s2B[1]])
        
        # Tentatively apply the edge change
        if is_horiz:
            s.h_type[ei, ej] = new_t
            s.h_dir[ei, ej] = new_d
        else:
            s.v_type[ei, ej] = new_t
            s.v_dir[ei, ej] = new_d
        
        # Recompute affected S1 pieces
        s.s1_pieces[cell_A] = s.get_piece_s1(*cell_A)
        s.s1_pieces[cell_B] = s.get_piece_s1(*cell_B)
        
        # Recompute affected S2 pieces
        s.s2_pieces[s2A[0], s2A[1]] = s._rotate(s.s1_pieces[cell_A], s2A[2])
        s.s2_pieces[s2B[0], s2B[1]] = s._rotate(s.s1_pieces[cell_B], s2B[2])
        
        # Count new mismatches
        new_mm = self._count_mismatches_at(affected)
        delta_mm = new_mm - old_mm
        
        # Diversity/balance delta
        old_div = s.diversity_pen
        old_bal = s.balance_pen
        s.type_freq[old_t] -= 1
        s.type_freq[new_t] += 1
        new_div = s.compute_diversity_penalty()
        new_bal = s.compute_balance_penalty()
        s.type_freq[old_t] += 1  # Revert freq for now
        s.type_freq[new_t] -= 1
        
        delta_E = (10.0 * delta_mm 
                   + 1.0 * (new_div - old_div) 
                   + 0.5 * (new_bal - old_bal))
        
        undo_data = {
            'is_horiz': is_horiz, 'ei': ei, 'ej': ej,
            'old_t': old_t, 'old_d': old_d, 'new_t': new_t, 'new_d': new_d,
            'cell_A': cell_A, 'cell_B': cell_B,
            's2A': s2A, 's2B': s2B,
            'old_s1A': old_s1A, 'old_s1B': old_s1B,
            'old_s2A': old_s2A, 'old_s2B': old_s2B,
            'delta_mm': delta_mm,
            'new_div': new_div, 'new_bal': new_bal,
            'old_div': old_div, 'old_bal': old_bal,
        }
        
        return delta_E, undo_data
    
    def accept_recolor(self, undo_data):
        """Commit the move: update cached energy values"""
        s = self.state
        s.mismatch_count += undo_data['delta_mm']
        s.type_freq[undo_data['old_t']] -= 1
        s.type_freq[undo_data['new_t']] += 1
        s.diversity_pen = undo_data['new_div']
        s.balance_pen = undo_data['new_bal']
    
    def reject_recolor(self, undo_data):
        """Revert the move"""
        s = self.state
        d = undo_data
        if d['is_horiz']:
            s.h_type[d['ei'], d['ej']] = d['old_t']
            s.h_dir[d['ei'], d['ej']] = d['old_d']
        else:
            s.v_type[d['ei'], d['ej']] = d['old_t']
            s.v_dir[d['ei'], d['ej']] = d['old_d']
        
        s.s1_pieces[d['cell_A']] = d['old_s1A']
        s.s1_pieces[d['cell_B']] = d['old_s1B']
        s.s2_pieces[d['s2A'][0], d['s2A'][1]] = d['old_s2A']
        s.s2_pieces[d['s2B'][0], d['s2B'][1]] = d['old_s2B']
    
    def _get_affected_adjacencies(self, pos_a, pos_b):
        """
        Get all S2 adjacency pairs affected by changes at pos_a and pos_b.
        Returns list of ((y1,x1,side1), (y2,x2,side2)) tuples.
        Deduplicated: each adjacency appears once.
        """
        n = self.n
        seen = set()
        result = []
        
        for pos in [pos_a, pos_b]:
            y, x = pos
            for dy, dx, my_side, their_side in NEIGHBORS:
                ny, nx = y + dy, x + dx
                if 0 <= ny < n and 0 <= nx < n:
                    # Canonical form: smaller position first
                    edge_key = (min((y,x), (ny,nx)), max((y,x), (ny,nx)))
                    if edge_key not in seen:
                        seen.add(edge_key)
                        result.append((y, x, my_side, ny, nx, their_side))
        return result
    
    def _count_mismatches_at(self, affected):
        """Count mismatches for a list of specific adjacency pairs"""
        s2 = self.state.s2_pieces
        count = 0
        for (y1, x1, s1, y2, x2, s2_side) in affected:
            if s2[y1, x1, s1] + s2[y2, x2, s2_side] != 0:
                count += 1
        return count
```

### 9.4 Main Solver Loop  (solver.py)

```python
import math
import random
import time
import numpy as np

class MCMCSolver:
    def __init__(self, n, K, 
                 max_mapping_attempts=20,
                 max_restarts_per_mapping=10,
                 max_steps=None,
                 patience=50_000,
                 move_weights=(0.95, 0.05),  # (recolor, mapping_swap)
                 verbose=True):
        self.n = n
        self.K = K
        self.max_mapping_attempts = max_mapping_attempts
        self.max_restarts = max_restarts_per_mapping
        self.max_steps = max_steps or 10 * n**4
        self.patience = patience
        self.p_recolor, self.p_swap = move_weights
        self.verbose = verbose
    
    def solve(self):
        """Main entry point. Returns (state, mapping) or None."""
        for m_attempt in range(self.max_mapping_attempts):
            if self.verbose:
                print(f"\n=== Mapping attempt {m_attempt+1}/{self.max_mapping_attempts} ===")
            
            mapping_fwd, mapping_inv = generate_mcmc_mapping(self.n)
            
            # Check mapping quality (dissimilarity)
            fixed_points = sum(1 for (y,x), (y2,x2,r) in mapping_fwd.items()
                             if (y,x) == (y2,x2) and r == 0)
            if self.verbose:
                print(f"  Mapping has {fixed_points}/{self.n**2} fixed points")
            
            for restart in range(self.max_restarts):
                result = self._run_mcmc(mapping_fwd, mapping_inv, restart)
                if result is not None:
                    return result
            
            if self.verbose:
                print(f"  Mapping {m_attempt+1} exhausted after {self.max_restarts} restarts")
        
        return None  # Failed
    
    def _run_mcmc(self, mapping_fwd, mapping_inv, restart_idx):
        """Single MCMC run. Returns state if successful, None otherwise."""
        state = MCMCState(self.n, self.K, mapping_fwd, mapping_inv)
        
        if restart_idx > 0:
            # Partial randomization: keep 70% of edges, randomize 30%
            self._partial_randomize(state, fraction=0.3)
        
        engine = MoveEngine(state)
        
        # Calibrate initial temperature
        T = self._calibrate_T0(engine)
        
        best_energy = state.energy
        best_mm = state.mismatch_count
        stagnation = 0
        reheats = 0
        accepted = 0
        total = 0
        
        t_start = time.time()
        
        for step in range(self.max_steps):
            # Choose move type
            if random.random() < self.p_recolor:
                result = engine.propose_recolor()
            else:
                result = engine.propose_mapping_swap()
            
            if result is None:
                continue  # Skip identity moves
            
            delta_E, undo = result
            total += 1
            
            # Metropolis acceptance
            if delta_E <= 0 or random.random() < math.exp(-delta_E / max(T, 1e-10)):
                engine.accept_recolor(undo)
                accepted += 1
                
                if state.energy < best_energy:
                    best_energy = state.energy
                    best_mm = state.mismatch_count
                    stagnation = 0
                
                # Check for solution
                if state.mismatch_count == 0:
                    elapsed = time.time() - t_start
                    if self.verbose:
                        E = state.energy
                        print(f"  ✓ SOLVED in {step+1} steps, {elapsed:.1f}s "
                              f"(E={E:.1f}, types_used={np.count_nonzero(state.type_freq[1:])})")
                    
                    # Optional: check diversity is acceptable
                    if state.diversity_pen == 0:
                        return state
                    # else: solution is valid but low diversity, continue to improve
            else:
                engine.reject_recolor(undo)
            
            stagnation += 1
            
            # Adaptive temperature every 1000 steps
            if total > 0 and total % 1000 == 0:
                rate = accepted / 1000
                if rate > 0.30:
                    T *= 0.95
                elif rate < 0.20:
                    T *= 1.05
                T = max(0.01, min(T, 100.0))
                accepted = 0
            
            # Stagnation detection
            if stagnation > self.patience:
                if reheats < 5:
                    T *= 5.0
                    reheats += 1
                    stagnation = 0
                    if self.verbose:
                        print(f"  Reheat #{reheats}, T={T:.3f}, best_mm={best_mm}")
                else:
                    if self.verbose:
                        elapsed = time.time() - t_start
                        print(f"  Restart {restart_idx}: stuck at mm={best_mm} "
                              f"after {step+1} steps, {elapsed:.1f}s")
                    return None
            
            # Progress log every 100K steps
            if self.verbose and step > 0 and step % 100_000 == 0:
                elapsed = time.time() - t_start
                print(f"  Step {step//1000}K: mm={state.mismatch_count}, "
                      f"best={best_mm}, T={T:.3f}, {elapsed:.1f}s")
        
        if self.verbose:
            elapsed = time.time() - t_start
            print(f"  Restart {restart_idx}: max steps reached, "
                  f"best_mm={best_mm}, {elapsed:.1f}s")
        return None
    
    def _calibrate_T0(self, engine, n_samples=1000):
        """Estimate good initial temperature by sampling move costs"""
        deltas = []
        for _ in range(n_samples):
            result = engine.propose_recolor()
            if result is not None:
                delta_E, undo = result
                deltas.append(abs(delta_E))
                engine.reject_recolor(undo)
        
        if not deltas:
            return 1.0
        
        median_delta = sorted(deltas)[len(deltas) // 2]
        T0 = median_delta / math.log(3)  # ~75% acceptance for median
        return max(T0, 0.1)
    
    def _partial_randomize(self, state, fraction=0.3):
        """Randomize a fraction of all edges"""
        n = state.n
        # Horizontal edges
        for i in range(n):
            for j in range(n - 1):
                if random.random() < fraction:
                    state.h_type[i, j] = random.randint(1, state.K)
                    state.h_dir[i, j] = random.randint(0, 1)
        # Vertical edges
        for i in range(n - 1):
            for j in range(n):
                if random.random() < fraction:
                    state.v_type[i, j] = random.randint(1, state.K)
                    state.v_dir[i, j] = random.randint(0, 1)
        # Recompute everything
        state._init_freq()
        state.recompute_all_pieces()
        state.mismatch_count = state.full_mismatch_count()
        state.diversity_pen = state.compute_diversity_penalty()
        state.balance_pen = state.compute_balance_penalty()
```

### 9.5 Output Conversion  (convert.py)

```python
def mcmc_to_legacy_format(state):
    """
    Convert MCMC signed representation to the legacy odd/even format
    used by Draw_sollution.py and the existing codebase.
    
    Signed → Legacy:
      +t  →  2t - 1  (odd, outie)
      −t  →  2t      (even, innie)
       0  →  0       (flat)
    """
    n = state.n
    sol0 = [[[None]*4 for _ in range(n)] for _ in range(n)]
    sol1 = [[[None]*4 for _ in range(n)] for _ in range(n)]
    
    for i in range(n):
        for j in range(n):
            for s in range(4):
                v0 = int(state.s1_pieces[i, j, s])
                v1 = int(state.s2_pieces[i, j, s])
                sol0[i][j][s] = _signed_to_legacy(v0)
                sol1[i][j][s] = _signed_to_legacy(v1)
    
    return sol0, sol1

def _signed_to_legacy(v):
    if v == 0:
        return 0
    elif v > 0:
        return 2 * v - 1   # outie → odd
    else:
        return 2 * (-v)    # innie → even

def mcmc_to_mapping_dict(state):
    """Convert mapping to legacy format: (y,x,0) → (y2,x2,rot)"""
    mapping = {}
    for (y, x), (y2, x2, rot) in state.map_fwd.items():
        mapping[(y, x, 0)] = (y2, x2, rot)
    return mapping
```

---

## 10. Hyperparameter Guide

### 10.1 Choosing $K$ (Number of Base Edge Types)

From the Martinsson threshold, uniqueness transitions at $m \sim c \cdot n$ where
$c \approx 2e^{-1/2} \approx 1.21$. Since $m = 2K + 1$:

$$K \approx \frac{cn - 1}{2} \approx 0.6n$$

We want to be slightly BELOW the uniqueness threshold (to allow two solutions):

| $n$  | $K_{\text{recommended}}$ | $m = 2K+1$ |
|------|--------------------------|------------|
| 10   | 5–7                      | 11–15      |
| 15   | 7–10                     | 15–21      |
| 20   | 10–13                    | 21–27      |
| 30   | 15–20                    | 31–41      |
| 50   | 25–35                    | 51–71      |

**Start with $K = \lfloor 0.6n \rfloor$ and adjust**: if MCMC consistently finds
solutions, try lower $K$ (harder). If it consistently fails, try higher $K$.

### 10.2 Step Budget

| $n$  | Internal edges | Recommended `max_steps` | Expected time (Python) |
|------|---------------|------------------------|----------------------|
| 10   | 180           | 1,000,000              | ~10s                 |
| 20   | 760           | 5,000,000              | ~60s                 |
| 30   | 1,740         | 20,000,000             | ~5min                |
| 50   | 4,900         | 100,000,000            | ~30min               |

### 10.3 All Parameters

```python
DEFAULT_PARAMS = {
    # Core
    'n': 10,
    'K': 6,                       # Base edge types (effective m = 2K+1)
    
    # Energy weights
    'w_mismatch': 10.0,           # Weight for S2 mismatch count
    'w_diversity': 1.0,           # Weight for diversity penalty
    'w_balance': 0.5,             # Weight for balance penalty
    
    # Diversity thresholds
    'K_min_fraction': 0.8,        # Min fraction of K types that must be used
    'f_max_factor': 1.5,          # Max frequency = f_max_factor × uniform
    
    # Temperature
    'T_adapt_window': 1000,       # Steps between temperature adjustments
    'target_accept_rate': 0.25,   # Target Metropolis acceptance rate
    'T_min': 0.01,
    'T_max': 100.0,
    
    # Move mix
    'p_recolor': 0.95,            # Probability of edge recolor move
    'p_mapping_swap': 0.05,       # Probability of mapping swap move
    
    # Convergence
    'patience': 50_000,           # Steps without improvement before reheat
    'max_reheats': 5,             # Reheats before restart
    'reheat_factor': 5.0,         # Temperature multiplier on reheat
    
    # Restarts
    'max_restarts': 10,           # Edge restarts per mapping
    'restart_randomize_frac': 0.3,# Fraction of edges to randomize on restart
    
    # Mapping
    'max_mapping_attempts': 20,   # Different mappings to try
    'min_displaced_fraction': 0.8,# Min fraction of pieces that change position
}
```

---

## 11. Verification Strategy

### 11.1 Internal Checks (Fast)

After MCMC finds $M_2 = 0$:

```python
def verify_solution(state):
    """Quick O(n²) verification"""
    n = state.n
    
    # 1. Check S1 is trivially valid (by construction, always true)
    # Just verify boundary
    for i in range(n):
        assert state.s1_pieces[i, 0, LEFT] == 0     # Left boundary
        assert state.s1_pieces[i, n-1, RIGHT] == 0   # Right boundary
        assert state.s1_pieces[0, i, TOP] == 0        # Top boundary
        assert state.s1_pieces[n-1, i, BOTTOM] == 0   # Bottom boundary
    
    # 2. Check S2 adjacency matching
    for i in range(n):
        for j in range(n):
            if j < n-1:
                assert state.s2_pieces[i,j,RIGHT] + state.s2_pieces[i,j+1,LEFT] == 0
            if i < n-1:
                assert state.s2_pieces[i,j,BOTTOM] + state.s2_pieces[i+1,j,TOP] == 0
    
    # 3. Check S2 boundary
    for i in range(n):
        assert state.s2_pieces[i, 0, LEFT] == 0
        assert state.s2_pieces[i, n-1, RIGHT] == 0
        assert state.s2_pieces[0, i, TOP] == 0
        assert state.s2_pieces[n-1, i, BOTTOM] == 0
    
    # 4. Check piece multiset match
    s1_multiset = Counter()
    s2_multiset = Counter()
    for i in range(n):
        for j in range(n):
            s1_canonical = canonical_piece(state.s1_pieces[i,j])
            s2_canonical = canonical_piece(state.s2_pieces[i,j])
            s1_multiset[s1_canonical] += 1
            s2_multiset[s2_canonical] += 1
    assert s1_multiset == s2_multiset
    
    return True

def canonical_piece(piece):
    """Get rotation-canonical form of a piece (smallest rotation)"""
    p = tuple(piece)
    return min(p[i:] + p[:i] for i in range(4))
```

### 11.2 SAT-Based Uniqueness Check (Optional, Expensive)

After finding a valid double-solution, verify no 3rd solution exists:

1. Fix the piece set (all $n^2$ pieces with their connection types)
2. Encode as a SAT problem: "can these pieces be arranged in a valid grid?"
3. Add blocking clauses for Solution 1 and Solution 2
4. If UNSAT → exactly 2 solutions (confirmed)

This can reuse the existing SAT infrastructure from `jig_SAT_V3.py`.

---

## 12. Expected Performance & Scaling

### 12.1 Per-Step Cost

| Operation | Cost |
|-----------|------|
| Pick random edge | $O(1)$ |
| Compute 2 old S1 pieces | $O(1)$ |
| Lookup 2 S2 positions | $O(1)$ |
| Count old mismatches (≤8 pairs) | $O(1)$ |
| Apply edge change | $O(1)$ |
| Compute 2 new S1 pieces | $O(1)$ |
| Apply 2 rotations for S2 | $O(1)$ |
| Count new mismatches (≤8 pairs) | $O(1)$ |
| Diversity/balance delta | $O(1)$ |
| Accept/reject | $O(1)$ |
| **Total per step** | **$O(1)$** |

In pure Python: ~5–10 μs per step → **100K–200K steps/second**.

With Numba JIT on the inner loop: ~0.1–0.5 μs per step → **2M–10M steps/second**.

### 12.2 Convergence Estimate

The number of steps to convergence depends on:
1. How constraining the mapping is
2. How many base types $K$ we use
3. The energy landscape ruggedness

Empirical expectation (to be validated):

| $n$ | Steps to solve | Time (Python) | Time (Numba) |
|-----|---------------|---------------|-------------|
| 10  | ~100K–1M      | 1–10s         | <1s         |
| 20  | ~1M–10M       | 10–100s       | 1–5s        |
| 30  | ~5M–50M       | 1–10min       | 5–30s       |
| 50  | ~20M–200M     | 5–60min       | 1–10min     |

### 12.3 Memory

| Component | Size | $n=50$ |
|-----------|------|--------|
| Edge arrays (h_type, h_dir, v_type, v_dir) | $4 \times n^2$ bytes | ~10 KB |
| S1/S2 pieces | $2 \times n^2 \times 4 \times 2$ bytes | ~40 KB |
| Mapping dicts | $2 \times n^2 \times 3 \times 8$ bytes | ~120 KB |
| Type frequencies | $K \times 4$ bytes | <1 KB |
| **Total** | | **< 1 MB** |

Memory is negligible. This is a major advantage over the SAT approach.

---

## 13. Potential Enhancements (Phase 2+)

### 13.1 Numba/Cython Acceleration

The inner MCMC loop is pure Python with dictionary lookups and small array
operations. Converting the hot path to Numba would give 10–50× speedup:

```python
@numba.njit
def mcmc_step(h_type, h_dir, v_type, v_dir, s1_pieces, s2_pieces, 
              map_fwd_arr, map_inv_arr, type_freq, T, K, n):
    # ... tight inner loop without Python overhead
```

Key change: replace dict-based mapping with 2D arrays:
- `map_fwd_arr[y, x, :]` = `[y2, x2, rot]`
- `map_inv_arr[y2, x2, :]` = `[y, x, rot]`

### 13.2 Parallel Tempering

Run $P$ replicas at different temperatures $T_1 < T_2 < \ldots < T_P$.
Periodically swap configurations between adjacent temperatures.

Benefits:
- Hot replicas explore broadly, cold replicas refine
- Provably faster mixing for multimodal landscapes
- Embarrassingly parallel

### 13.3 Wolff-Style Cluster Moves

When stuck, identify a "frustrated cluster" — a connected subgraph of S2
mismatches — and recolor all contributing S1 edges simultaneously.

### 13.4 Smart Initialization via Constraint Propagation

Before MCMC, do one pass of arc consistency / unit propagation on the S2
constraints to pre-assign some edges that are forced.

---

## 14. Test Plan

### 14.1 Unit Tests

1. **Piece computation**: Verify `get_piece_s1` matches manually computed pieces
2. **Rotation**: Verify `_rotate` for all 4 rotations
3. **Matching**: Verify `c1 + c2 == 0` correctly identifies matched/mismatched pairs
4. **Delta computation**: Verify delta matches full recompute for random moves
5. **Energy consistency**: After each move, verify `state.energy` matches full recompute

### 14.2 Integration Tests

1. **$n=3, K=2$**: Trivially small, should find solutions instantly. Verify both solutions are valid.
2. **$n=5, K=3$**: Still small, good for debugging. Verify piece multiset equality.
3. **$n=6, K=4$**: Compare against existing SAT solver output (if available).

### 14.3 Scaling Tests

Run for $n \in \{10, 15, 20, 25, 30, 40, 50\}$ with recommended $K$ values.
Record:
- Time to first solution
- Number of mapping attempts needed
- Number of restarts needed
- Final mismatch count (if not solved)
- Number of distinct piece types
- Step count at solution

### 14.4 Validation Against SAT

For $n \leq 12$: after MCMC finds a solution, run the SAT uniqueness verifier to
confirm exactly 2 solutions. This validates that the MCMC approach produces
genuinely valid double-solution puzzles.

---

*Design document for MCMC implementation of the Double-Solution Puzzle Generator.
Ready for implementation.*
