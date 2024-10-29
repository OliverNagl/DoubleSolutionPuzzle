from pysat.solvers import CryptoMinisat
from pysat.solvers import Glucose3
from itertools import product
from collections import Counter
from pysat.formula import IDPool
from generator_V2 import *
from Solvers_without_direction.utility_v1 import *

def setup_puzzle_constraints(solver, n, m, initial_edges, initial_piece_ID=None):
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

    
    """Using the initial piece ID`s as extra variable to enforce the same piece connections in the
    next solution. This is done by adding a clause that forces the new variable to be true if 
    all connections of a piece are true."""
    if initial_piece_ID is not None:
        max_var_pool = max([max(puzzle_vars[(i, j, side)][rotation]) for (i, j, side) in puzzle_vars for rotation in range(4)])
        # Loop over all possible positions in the grid
        for piece_ID in initial_piece_ID:
            or_clauses = []  # This will hold all the connection_match clauses for OR logic
            
            for i in range(n):
                for j in range(n):
                    # For each position, check the connection pattern matches `id_to_piece[Piece_ID]`
                    for rotation in range(4):  # If there are rotations to consider
                        # Create a clause for each side to match the piece's connections
                        connection_match = []
                        piece = id_to_piece(piece_ID, m, max_var_pool)
                        for side in range(4):
                            connection = piece[side]  # Get the expected connection for this side
                            connection_var = puzzle_vars[(i, j, side)][rotation][connection]
                            connection_match.append(connection_var)

                        # Create a new variable representing this conjunction (AND of connection_match)
                        conjunction_var = piece_ID + n*m + i*n + j*n + rotation + 1
                        # Add a clause that makes conjunction_var true if and only if all connection_match are true
                        # We achieve this by adding a CNF encoding for the conjunction
                        for literal in connection_match:
                            pass
                            solver.add_clause([-conjunction_var, literal])
                             # If conjunction_var is true, all connection_match must be true
                        solver.add_clause([conjunction_var] + [-literal for literal in connection_match])
                        # Add this new conjunction variable to or_clauses for XOR logic
                        or_clauses.append(conjunction_var)  

            # Now, make piece_ID true if **any** position matches the connections (OR logic)
            # Create a clause linking piece_ID to all possible matches in the grid
            exactly_one(or_clauses, solver)

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
                            solution_matrix[i][j] = [None] * 4  # Initialize the array for sides + piece ID
                        solution_matrix[i][j][side] = puzzle_vars[(i, j, side)][rotation].index(var)

    print("Solution Matrix:")
    for row in solution_matrix:
        print(row)
    return solution_matrix

def solve_puzzle_with_all_solutions(n, m, initial_edges, initial_pieces=None):
    """
    Solve the puzzle using a SAT solver and find all possible solutions.
    n: Size of the grid (n x n)
    m: Number of connection types
    initial_edges: Dictionary containing the predefined edge types for certain pieces.
    """
    solutions = []
    solver = CryptoMinisat()

    # Set up the constraints with initial edge constraints
    puzzle_vars, piece_ids = setup_puzzle_constraints(solver, n, m, initial_edges,initial_piece_ID= None)

    # Solve for the first solution
    if solver.solve():
        first_solution = solver.get_model()
        solutions.append(first_solution)
        print("First solution found!")
        solution_matrix = print_solution(first_solution, puzzle_vars, piece_ids, n, m)
        max_var_pool = max([max(puzzle_vars[(i, j, side)][rotation]) for (i, j, side) in puzzle_vars for rotation in range(4)])
        # Extract initial edges from the first solution
        sol_ids = create_unique_ids(solution_matrix, n, m, max_var_pool)
        
        """
        Debugging:
        print(sol_ids)
        sol_matrix = [id_to_piece(sol_id, m, max_var_pool) for sol_id in sol_ids]
        print(sol_matrix)
        """
        
        # Create a new solver instance for finding all solutions
        solver2 = CryptoMinisat()
        # Set up the constraints for the new solver using the initial edges from the first solution
        puzzle_vars2, piece_ids2 = setup_puzzle_constraints(solver2, n, m, initial_edges=None,initial_piece_ID=sol_ids)
        
        i=0
        while solver2.solve():
            i += 1
            solution = solver2.get_model()
            solutions.append(solution)
            print("Solution found!")
            print_solution(solution, puzzle_vars2, piece_ids2, n, m)
            if i == 3:
                break

    if not solutions:
        print("No solutions found!")
    else:
        print(f"Total solutions found: {len(solutions)}")


if __name__ == "__main__":
    n = 5 # Example grid size
    q = 2*n*2.71**(-1/2)
    m = int((2 + q)/2)
    m=5
    print(f"puzzle should have 2 < m < {q} connection types")
    print(f"Using m = {m}")

    #generate_random_valid_jigsaw(n, m, 1) with seed = 1 and convert to dictionary of intial edges:
    puzzle = generate_random_valid_jigsaw(n, m, None)
    initial_edges = {}

    for y in range(n):
        for x in range(n):
            initial_edges[(y, x)] = [int(puzzle[y][x][0]), int(puzzle[y][x][1]), int(puzzle[y][x][2]), int(puzzle[y][x][3])]
   
    #print(puzzle)
    #print(initial_edges)

    initial_edges1 = {
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

    solve_puzzle_with_all_solutions(n, m, initial_edges1)