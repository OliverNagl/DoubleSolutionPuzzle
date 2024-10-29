from pysat.solvers import Solver
from pysat.formula import CNF

# Define problem size
n = 3  # Grid size (n x n)
m = 4  # Number of connection types (assume 4 types for example)
num_pieces = n * n  # Total number of pieces

# Each piece has 4 sides (T, R, B, L), and can have m different connection types
# Piece connections: dict with piece number as keys, values are lists of connection types [Top, Right, Bottom, Left]
piece_connections = {
    0: [0, 1, 2, 0],  # Top-left piece: right connection = 1, bottom connection = 2
    1: [0, 2, 4, 1],  # Center piece: top connection = 2, left connection = 0
    2: [0, 0, 1, 2],
    3: [2, 4, 1, 0],  # Bottom-right piece: left connection = 1
    4: [4, 4, 4, 4],
    5: [1, 0, 2, 4],
    6: [1, 2, 0, 0],
    7: [4, 1, 0, 2],
    8: [2, 0, 0, 1]
    # Add other pieces similarly...
}

# Initialize a SAT solver
solver = Solver()

# CNF formula storage
cnf = CNF()

# Variables for piece placement and orientation
def piece_var(i, j, p):
    """Returns the variable for piece p at position (i, j)"""
    return i * n * num_pieces + j * num_pieces + p + 1

def orientation_var(i, j, p, k):
    """Returns the variable for piece p at position (i, j) with orientation k"""
    return n * n * num_pieces + i * n * num_pieces * 4 + j * num_pieces * 4 + p * 4 + k + 1

# Add piece placement constraints (one piece per position, no duplicates)
for i in range(n):
    for j in range(n):
        piece_vars = [piece_var(i, j, p) for p in range(num_pieces)]
        cnf.append(piece_vars)  # At least one piece in position (i,j)

        # No two pieces can occupy the same position
        for p1 in range(num_pieces):
            for p2 in range(p1 + 1, num_pieces):
                cnf.append([-piece_var(i, j, p1), -piece_var(i, j, p2)])

# Add orientation constraints (each piece in one orientation only)
for i in range(n):
    for j in range(n):
        for p in range(num_pieces):
            orientation_vars = [orientation_var(i, j, p, k) for k in range(4)]
            cnf.append(orientation_vars)  # At least one orientation for piece (i,j)

            # Ensure no two orientations are assigned simultaneously
            for k1 in range(4):
                for k2 in range(k1 + 1, 4):
                    cnf.append([-orientation_var(i, j, p, k1), -orientation_var(i, j, p, k2)])

# Connection matching constraints between adjacent pieces
for i in range(n):
    for j in range(n):
        for p1 in range(num_pieces):
            for k1 in range(4):
                # Matching right side of (i,j) with left side of (i,j+1)
                if j < n - 1:
                    for p2 in range(num_pieces):
                        for k2 in range(4):
                            right_side_1 = piece_connections[p1][(1 + k1) % 4]
                            left_side_2 = piece_connections[p2][(3 + k2) % 4]
                            if right_side_1 != left_side_2:
                                cnf.append([-piece_var(i, j, p1), -orientation_var(i, j, p1, k1),
                                            -piece_var(i, j + 1, p2), -orientation_var(i, j + 1, p2, k2)])

                # Matching bottom side of (i,j) with top side of (i+1,j)
                if i < n - 1:
                    for p2 in range(num_pieces):
                        for k2 in range(4):
                            bottom_side_1 = piece_connections[p1][(2 + k1) % 4]
                            top_side_2 = piece_connections[p2][(0 + k2) % 4]
                            if bottom_side_1 != top_side_2:
                                cnf.append([-piece_var(i, j, p1), -orientation_var(i, j, p1, k1),
                                            -piece_var(i + 1, j, p2), -orientation_var(i + 1, j, p2, k2)])

# Pre-specify initial jigs (force certain pieces into specific positions)
def pre_specify_initial_jigs(initial_positions):
    """Pre-specify initial pieces and orientations for given positions.
    
    Example of initial_positions: 
    {(0, 0): (0, 0), (1, 1): (3, 2)} where (i,j): (piece, orientation)
    """
    for (i, j), (p, o) in initial_positions.items():
        cnf.append([piece_var(i, j, p)])  # Force piece p at position (i,j)
        cnf.append([orientation_var(i, j, p, o)])  # Force piece p to have orientation o at position (i,j)]

# Find all solutions by blocking previous solutions
def find_all_solutions():
    solutions = []
    i = 1
    while solver.solve():
        i += 1
        print("Found a solution!")
        solution = solver.get_model()
        solutions.append(solution)

        # Add a blocking clause to prevent finding the same solution again
        blocking_clause = [-lit for lit in solution if lit > 0]
        solver.add_clause(blocking_clause)
        if i > 10:
            break
    return solutions

# Specify initial positions (example)
initial_positions = {
    (0, 0): (0, 0),  # Piece 0 at (0,0) with 0° orientation  # Piece 2 at (2,2) with 90° orientation
    #(1, 0): (1,0),


}
pre_specify_initial_jigs(initial_positions)

# Add all CNF constraints to the solver
solver.append_formula(cnf)

# Solve and find all possible solutions
all_solutions = find_all_solutions()

# Interpret solutions
for sol in all_solutions:
    grid = [[None for _ in range(n)] for _ in range(n)]
    for lit in sol:
        if lit > 0:
            var = lit - 1
            if var < n * n * num_pieces:
                i = var // (n * num_pieces)
                j = (var % (n * num_pieces)) // num_pieces
                p = var % num_pieces
                grid[i][j] = p
    print("Solution Grid:")
    for row in grid:
        print(row)

# Cleanup solver
solver.delete()
