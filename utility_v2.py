from pysat.solvers import Glucose3
from itertools import product
from collections import Counter
from pysat.formula import IDPool
import numpy as np
from pysat.card import CardEnc
def extract_piece_ids(model, puzzle_vars, piece_ids, n, m):
    """
    Extract the piece IDs from the SAT model.
    """
    piece_ids_solution = [[None for _ in range(n)] for _ in range(n)]
    
    for var in model:
        if var > 0:  # Only consider positive literals
            for (i, j, side) in puzzle_vars:
                for rotation in range(4):
                    if var in puzzle_vars[(i, j, side)][rotation]:
                        piece_id = piece_ids[(i, j, rotation)]
                        piece_ids_solution[i][j] = piece_id

    return piece_ids_solution

def extract_initial_edges(solution, puzzle_vars, n, m):
    """
    Extract the initial edges from the solution to use as constraints for the next solver.
    """
    initial_edges = {}
    for i in range(n):
        for j in range(n):
            edges = [None] * 4
            for side in range(4):
                for rotation in range(4):
                    for edge_type in range(m):
                        if solution[puzzle_vars[(i, j, side)][rotation][edge_type] - 1] > 0:
                            edges[side] = edge_type
                            break
            initial_edges[(i, j)] = edges
    return initial_edges

def extract_ids(model, puzzle_vars, n, m):
    """
    Extract the piece IDs from the SAT model.
    """
    piece_ids_solution = np.zeros((n, n), dtype=int)
    
    for var in model:
        if var > 0:  # Only consider positive literals
            for (i, j, side) in puzzle_vars:
                for rotation in range(4):
                    if var in puzzle_vars[(i, j, side)][rotation]:
                        piece_id = (var - 1) // (n * 4 * m)
                        piece_ids_solution[i][j] = piece_id

    return piece_ids_solution
def enforce_same_piece_counts_with_ids(solver, puzzle_vars, first_solution_pieces, piece_ids_solution, n, m):
    """
    Enforce that the next solution must use the same pieces with the same frequencies (allowing for rotations and different placements).
    """
    from collections import Counter

    # Count the frequency of each piece in the first solution
    piece_counts = Counter(tuple(piece) for piece in first_solution_pieces)
    
    # For each piece in the first solution, enforce it must appear the same number of times
    for piece, count in piece_counts.items():
        piece_vars = []
        for i in range(n):
            for j in range(n):
                for rotation in range(4):
                    for side in range(4):
                        # Check if the piece matches the values of the current piece
                        if puzzle_vars[(i, j, side)][rotation] == piece[side]:
                            piece_vars.append(puzzle_vars[(i, j, side)][rotation])
        if piece_vars:
            enforce_exactly_k(solver, piece_vars, count)

def enforce_same_piece_counts(solver, puzzle_vars, first_solution_pieces, n, m):
    """
    Enforce that the second solution must use the same pieces with the same frequencies (allowing for rotations).
    """
    # Count the frequency of each piece in the first solution
    piece_counts = Counter(tuple(piece) for piece in first_solution_pieces)
    
    # For each piece in the first solution, enforce it must appear the same number of times
    for piece, count in piece_counts.items():
        piece_vars = []
        for i in range(n):
            for j in range(n):
                for rotation in range(4):
                    piece_vars.append(puzzle_vars[(i, j, 0)][rotation])
        enforce_exactly_k(solver, piece_vars, count)

def enforce_exactly_k(solver, clauses, k):
    """
    Ensure that exactly 'k' of the clauses are true.
    """
    from pysat.card import CardEnc
    lits = [lit for clause in clauses for lit in clause]  # Flatten the list of lists
    
    # At most k
    enc_atmost = CardEnc.atmost(lits=lits, bound=k)
    for clause in enc_atmost.clauses:
        solver.add_clause(clause)
    
    # At least k
    enc_atleast = CardEnc.atleast(lits=lits, bound=k)
    for clause in enc_atleast.clauses:
        solver.add_clause(clause)
        
def piece_to_id(piece, m, max_var_pool):
    """
    Convert the normalized piece representation into a unique ID using a base conversion.
    And make sure that the IDs are also not present in the var pool.
    """
    piece_id = 0
    for i, connection in enumerate(piece):
        piece_id += connection * (m ** i)

    piece_id += max_var_pool + 1
    return piece_id

def id_to_piece(piece_id, m, max_var_pool):
    """
    Convert the unique ID back into the original piece representation.
    """
    piece = []
    piece_id -= 1
    piece_id -= max_var_pool
    for i in range(4):
        piece.append(piece_id % m)
        piece_id //= m
    return normalize_piece(piece)
        
def create_unique_ids(solution_matrix, n, m, max_var_pool):
    """
    Create unique ID for each realization of a jig puzzle piece.
    By using the ID, we can uniquely identify each piece's connection type and rotation.
    """
    piece_id_list = [None] * (n * n)
    piece_list = [item for sublist in solution_matrix for item in sublist]
    for i, piece in enumerate(piece_list):
        piece_id = piece_to_id(piece, m,max_var_pool)
        piece_id_list[i] = piece_id
    return piece_id_list
    
def normalize_piece(piece):
    """
    Normalize the piece representation by rotating it to start with the smallest connection type.
    """
    min_piece = piece
    for i in range(1, 4):
        rotated_piece = piece[i:] + piece[:i]
        if rotated_piece < min_piece:
            min_piece = rotated_piece
    return min_piece

def var(i, j, side, n, m, piece_id, rotation):
    """
    Function to generate unique variable ids for each puzzle piece's connection.
    i, j: position of the puzzle piece in the grid
    side: 0 = top, 1 = right, 2 = bottom, 3 = left
    n: size of the grid (n x n)
    m: number of distinct connection types
    piece_id: unique ID for the piece
    rotation: rotation of the piece (0, 1, 2, 3)
    """
    return int(piece_id * n * 4 * m + rotation * n * 4 * m + i * n * 4 * m + j * 4 * m + side * m + 1)



def exactly_one(lits, solver, pool):
    """Ensure exactly one literal is True among the given literals (for a connection type)."""
    enc = CardEnc.equals(lits=lits, bound=1, encoding=1, vpool=pool)
    solver.append_formula(enc.clauses)

def exactly_n2(lits, solver, n, pool):
    """Ensure exactly n literals are True among the given literals (for a connection type)."""
    enc = CardEnc.equals(lits=lits, bound=n, encoding=1, vpool=pool)
    solver.append_formula(enc.clauses)

# Block the exact placement of each piece in the current solution
def block_current_solution(solver, solution, puzzle_vars, n, m):
    blocking_clause = []
    for i in range(n):
        for j in range(n):
            for piece_idx in range(m):  # Number of pieces provided
                for rotation in range(4):  # All rotations
                    # Find the piece's current placement (if it was placed)
                    if solution.contains(puzzle_vars[(i, j, piece_idx, rotation)]):
                        # Block this exact placement (piece at this position with this rotation)
                        blocking_clause.append(-puzzle_vars[(i, j, piece_idx, rotation)])
    
    solver.add_clause(blocking_clause)

def at_most_k(solver, literals, k):
    """
    Ensure that at most k literals can be true at the same time.
    """
    if len(literals) <= k:
        return  # No need to enforce if there are fewer literals than k

    # Create auxiliary variables
    aux_vars = []
    for i in range(len(literals) - k):
        aux_var = solver.new_var()
        aux_vars.append(aux_var)

    # Add clauses linking auxiliary variables with literals
    for i in range(len(literals)):
        for j in range(len(aux_vars)):
            if i < j + k + 1:  # Connect the literal to the auxiliary variable
                solver.add_clause([-literals[i], aux_vars[j]])

    # Add clauses to ensure that each auxiliary variable can only be set true if enough literals are false
    for j in range(len(aux_vars)):
        solver.add_clause([aux_vars[j]] + [-literals[i] for i in range(j, j + k + 1)])

    # Finally, ensure that not too many auxiliary variables can be true
    for i in range(len(aux_vars) - 1):
        for j in range(i + 1, len(aux_vars)):
            solver.add_clause([-aux_vars[i], -aux_vars[j]])


def allow_one_swap_or_rotation(solver, solution, puzzle_vars, n, m):
    # We will create a clause that ensures that at least one piece changes either its position or rotation
    swap_rotation_clause = []
    
    for i in range(n):
        for j in range(n):
            for piece_idx in range(m):  # Number of pieces provided
                for rotation in range(4):  # All rotations
                    # If the current placement is used in the solution, block this piece from being the same in next solution
                    if solution.contains(puzzle_vars[(i, j, piece_idx, rotation)]):
                        # Add the negation of the current placement (it must change in next solution)
                        swap_rotation_clause.append(-puzzle_vars[(i, j, piece_idx, rotation)])
    
    # Now we create an "OR" clause: At least one placement or rotation must change
    solver.add_clause(swap_rotation_clause)


def exactly_one_piece(solver, initial_pieces, n, m, num_positions, num_rotations=4):
    clauses = []
    
    # Ensure each position has exactly one piece in one rotation
    for position in range(num_positions):
        clause = []
        for piece_id in initial_pieces:
            for rotation in range(num_rotations):
                i, j = divmod(position, n)  # Calculate the row (i) and column (j) from the position
                for side in range(4):
                    clause.append(var(i, j, side, n, m, piece_id, rotation))
        clauses.append(clause)
        
        # Add mutual exclusion clauses
        for i in range(len(clause)):
            for j in range(i + 1, len(clause)):
                clauses.append([-clause[i], -clause[j]])
    
    # Add clauses to the solver
    for clause in clauses:
        solver.add_clause(clause)

def enforce_match(solver, piece1, piece2):
    """Enforce that two pieces have matching connection types."""
    for t in range(len(piece1)):  # len(piece1) = number of connection types (m)
        if t > 0:
            if t % 2 == 0:
                solver.add_clause([-piece1[t], piece2[t-1]])
                solver.add_clause([piece1[t], -piece2[t-1]])
            else:
                solver.add_clause([-piece1[t], piece2[t+1]])
                solver.add_clause([piece1[t], -piece2[t+1]])
        else:
            solver.add_clause([-piece1[t], piece2[t]])
            solver.add_clause([piece1[t], -piece2[t]])


def extract_pieces(model, puzzle_vars,piece_ids, n, m):
    """
    Extract the set of pieces from the SAT model.
    """
    solution_matrix = [[None for _ in range(n)] for _ in range(n)]
    
    for var in model:
        if var > 0:  # Only consider positive literals
            for (i, j, side) in puzzle_vars:
                for rotation in range(4):
                    if var in puzzle_vars[(i, j, side)][rotation]:
                        if solution_matrix[i][j] is None:
                            solution_matrix[i][j] = [None] * 5  # Initialize the array for sides + piece ID
                        solution_matrix[i][j][side] = puzzle_vars[(i, j, side)][rotation].index(var)
                        solution_matrix[i][j][4] = piece_ids[(i, j, rotation)]  # Assign the piece ID

    # Ensure all pieces are fully populated
    for i in range(n):
        for j in range(n):
            if solution_matrix[i][j] is None:
                raise ValueError(f"Piece at position ({i}, {j}) is not fully populated.")

    pieces = [solution_matrix[i][j] for i in range(n) for j in range(n)]
    
    return pieces