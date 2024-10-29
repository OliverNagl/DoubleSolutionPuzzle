from pysat.solvers import Glucose3
from itertools import product
from collections import Counter
from pysat.formula import IDPool

from Solvers_without_direction.utility_v1 import *

def setup_puzzle_constraints(solver, n, m, initial_edges, initial_pieces):
    """
    Function to setup the SAT solver constraints for the n x n puzzle.
    Each piece will have four connections (top, right, bottom, left), and adjacent pieces must fit together.
    initial_edges: dictionary {(i, j): [top, right, bottom, left]} specifying initial clues for specific pieces.
    """
    puzzle_vars = {}
    piece_ids = {}
    piece_id_counter = 0  # Initialize piece ID counter

    for i in range(n):
        for j in range(n):
            for side in range(4):  # 0=top, 1=right, 2=bottom, 3=left
                puzzle_vars[(i, j, side)] = []
                for rotation in range(4):  # 4 rotations
                    puzzle_vars[(i, j, side)].append([var(i, j, side, n, m, piece_id_counter, rotation) + t for t in range(m)])
                    piece_ids[(i, j, rotation)] = piece_id_counter
                    piece_id_counter += 1
    
    if initial_edges is not None:
        # Apply initial edge constraints
        for (i, j), edges in initial_edges.items():
            for side, edge_type in enumerate(edges):
                if edge_type is not None:
                    # If edge_type is given (not None), fix that connection type for the side
                    if edge_type < m:  # Ensure the edge type is within bounds
                        for rotation in range(4):
                            solver.add_clause([puzzle_vars[(i, j, side)][rotation][edge_type]])
                    else:
                        print(f"Invalid edge_type {edge_type} for piece {(i, j)} on side {side}.")

    if initial_pieces is not None:
        # Apply that only pieces with the ID in initial_pieces can be used but in all places and rotations
        for (i, j, rotation), piece_id in piece_ids.items():
            if piece_id not in initial_pieces:
                for side in range(4):
                    for t in range(m):
                        solver.add_clause([-puzzle_vars[(i, j, side)][rotation][t]])



            

    # Enforce the '0' connection type can only be used on edges or corners
    for i in range(n):
        for j in range(n):
            # Corners
            if (i == 0 and j == 0):  # Top-left corner
                for rotation in range(4):
                    solver.add_clause([puzzle_vars[(i, j, 0)][rotation][0]])  # Top side = 0
                    solver.add_clause([puzzle_vars[(i, j, 3)][rotation][0]])  # Left side = 0
                    solver.add_clause([-puzzle_vars[(i, j, 1)][rotation][0]])
                    solver.add_clause([-puzzle_vars[(i, j, 2)][rotation][0]])
                
            elif (i == 0 and j == n-1):  # Top-right corner
                for rotation in range(4):
                    solver.add_clause([puzzle_vars[(i, j, 0)][rotation][0]])  # Top side = 0
                    solver.add_clause([puzzle_vars[(i, j, 1)][rotation][0]])  # Right side = 0
                    solver.add_clause([-puzzle_vars[(i, j, 3)][rotation][0]])
                    solver.add_clause([-puzzle_vars[(i, j, 2)][rotation][0]])
            elif (i == n-1 and j == 0):  # Bottom-left corner
                for rotation in range(4):
                    solver.add_clause([puzzle_vars[(i, j, 2)][rotation][0]])  # Bottom side = 0
                    solver.add_clause([puzzle_vars[(i, j, 3)][rotation][0]])  # Left side = 0
                    solver.add_clause([-puzzle_vars[(i, j, 1)][rotation][0]])
                    solver.add_clause([-puzzle_vars[(i, j, 0)][rotation][0]])
            elif (i == n-1 and j == n-1):  # Bottom-right corner
                for rotation in range(4):
                    solver.add_clause([puzzle_vars[(i, j, 2)][rotation][0]])  # Bottom side = 0
                    solver.add_clause([puzzle_vars[(i, j, 1)][rotation][0]])  # Right side = 0
                    solver.add_clause([-puzzle_vars[(i, j, 3)][rotation][0]])
                    solver.add_clause([-puzzle_vars[(i, j, 0)][rotation][0]])

            # Edges (excluding corners)
            elif i == 0:  # Top row, excluding corners
                for rotation in range(4):
                    solver.add_clause([puzzle_vars[(i, j, 0)][rotation][0]])  # Top side = 0
                    solver.add_clause([-puzzle_vars[(i, j, 1)][rotation][0]])
                    solver.add_clause([-puzzle_vars[(i, j, 2)][rotation][0]])
                    solver.add_clause([-puzzle_vars[(i, j, 3)][rotation][0]])
            
            elif i == n-1:  # Bottom row, excluding corners
                for rotation in range(4):
                    solver.add_clause([puzzle_vars[(i, j, 2)][rotation][0]])  # Bottom side = 0
                    solver.add_clause([-puzzle_vars[(i, j, 1)][rotation][0]])
                    solver.add_clause([-puzzle_vars[(i, j, 0)][rotation][0]])
                    solver.add_clause([-puzzle_vars[(i, j, 3)][rotation][0]])
                
            elif j == 0:  # Left column, excluding corners
                for rotation in range(4):
                    solver.add_clause([puzzle_vars[(i, j, 3)][rotation][0]])  # Left side = 0
                    solver.add_clause([-puzzle_vars[(i, j, 1)][rotation][0]])
                    solver.add_clause([-puzzle_vars[(i, j, 2)][rotation][0]])
                    solver.add_clause([-puzzle_vars[(i, j, 0)][rotation][0]])
            elif j == n-1:  # Right column, excluding corners
                for rotation in range(4):
                    solver.add_clause([puzzle_vars[(i, j, 1)][rotation][0]])  # Right side = 0
                    solver.add_clause([-puzzle_vars[(i, j, 0)][rotation][0]])
                    solver.add_clause([-puzzle_vars[(i, j, 2)][rotation][0]])
                    solver.add_clause([-puzzle_vars[(i, j, 3)][rotation][0]])

            # Interior pieces should not have connection type 0
            else:
                for side in range(4):
                    for rotation in range(4):
                        solver.add_clause([-puzzle_vars[(i, j, side)][rotation][0]])  # No side = 0 for interior pieces
    
    # Enforce connection matching between adjacent pieces
    for i in range(n):
        for j in range(n):
            # Ensure each side has exactly one connection type
            for side in range(4):
                for rotation in range(4):
                    exactly_one(puzzle_vars[(i, j, side)][rotation], solver)
            
            # Enforce matching between adjacent pieces
            if i > 0:  # Top piece matches bottom of the piece above
                for rotation in range(4):
                    enforce_match(solver, puzzle_vars[(i, j, 0)][rotation], puzzle_vars[(i-1, j, 2)][rotation])
            if j > 0:  # Left piece matches right of the piece to the left
                for rotation in range(4):
                    enforce_match(solver, puzzle_vars[(i, j, 3)][rotation], puzzle_vars[(i, j-1, 1)][rotation])

    return puzzle_vars, piece_ids


def print_solution(model, puzzle_vars, piece_ids, n, m):
    """
    Print the solution matrix with piece IDs.
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

    print("Solution Matrix:")
    for row in solution_matrix:
        print(row)

def solve_puzzle_with_all_solutions(n, m, initial_edges, initial_pieces=None):
    """
    Solve the puzzle using a SAT solver and find all possible solutions.
    n: Size of the grid (n x n)
    m: Number of connection types
    initial_edges: Dictionary containing the predefined edge types for certain pieces.
    """
    solutions = []
    solver = Glucose3()

    # Set up the constraints with initial edge constraints
    puzzle_vars, piece_ids = setup_puzzle_constraints(solver, n, m, initial_edges,initial_pieces = None)

    # Solve for the first solution
    if solver.solve():
        first_solution = solver.get_model()
        solutions.append(first_solution)
        print("First solution found!")
        print_solution(first_solution, puzzle_vars, piece_ids, n, m)

        # Extract initial edges from the first solution
        sol_ids = extract_ids(first_solution, puzzle_vars, n, m)

        # Create a new solver instance for finding all solutions
        solver2 = Glucose3()
        # Set up the constraints for the new solver using the initial edges from the first solution
        puzzle_vars2, piece_ids2 = setup_puzzle_constraints(solver2, n, m, initial_edges=None,initial_pieces=sol_ids)
        
        while solver2.solve():
            i += 1
            solution = solver2.get_model()
            solutions.append(solution)
            print("Solution found!")
            print_solution(solution, puzzle_vars2, piece_ids2, n, m)

    if not solutions:
        print("No solutions found!")
    else:
        print(f"Total solutions found: {len(solutions)}")


if __name__ == "__main__":
    n = 3  # Example grid size
    q = 2*n*2.71**(-1/2)
    m = int((2 + q)/2)
    m = 6
    print(f"puzzle should have 2 < m < {q} connection types")
    print(f"Using m = {m}")

    initial_edges = {
        (0, 0): [0, 1, 2, 0],  # Top-left piece: right connection = 1, bottom connection = 2
        (0, 1): [0, 2, 4, 1],  # Center piece: top connection = 2, left connection = 0
        (0, 2): [0, 0, 1, 2],
        (1, 0): [2, 4, 1, 0],  # Bottom-right piece: left connection = 1
        (1, 1): [4, 4, 4, 4],
        (1, 2): [1, 0, 2, 4],
        (2, 0): [1, 2, 0, 0],
        (2, 1): [4, 1, 0, 2],
        (2, 2): [2, 0, 0, 1]
    }

    solve_puzzle_with_all_solutions(n, m, initial_edges)