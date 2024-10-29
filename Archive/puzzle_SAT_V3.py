from pysat.solvers import Glucose3
from itertools import product

def var(i, j, side, n, m):
    """
    Function to generate unique variable ids for each puzzle piece's connection.
    i, j: position of the puzzle piece in the grid
    side: 0 = top, 1 = right, 2 = bottom, 3 = left
    n: size of the grid (n x n)
    m: number of distinct connection types
    """
    return i * n * 4 * m + j * 4 * m + side * m + 1

def exactly_one(lits, solver):
    """Ensure exactly one literal is True among the given literals (for a connection type)."""
    solver.add_clause(lits)  # At least one true
    for pair in product(lits, repeat=2):
        if pair[0] != pair[1]:
            solver.add_clause([-pair[0], -pair[1]])  # No two true

def enforce_match(solver, piece1, piece2):
    """Enforce that two pieces have matching connection types."""
    for t in range(len(piece1)):  # len(piece1) = number of connection types (m)
        solver.add_clause([-piece1[t], piece2[t]])
        solver.add_clause([piece1[t], -piece2[t]])

def normalize_piece(piece):
    """Return the lexicographically smallest rotation of a piece."""
    rotations = [piece[i:] + piece[:i] for i in range(4)]  # Generate all rotations
    return min(rotations)  # Return the smallest rotation

def extract_normalized_pieces(model, puzzle_vars, n, m):
    """
    Extract and normalize the set of pieces from the SAT model.
    """
    solution_matrix = [[None for _ in range(n)] for _ in range(n)]
    
    for var in model:
        if var > 0:
            for (i, j, side) in puzzle_vars:
                if var in puzzle_vars[(i, j, side)]:
                    connection_type = puzzle_vars[(i, j, side)].index(var)
                    if solution_matrix[i][j] is None:
                        solution_matrix[i][j] = [None] * 4
                    solution_matrix[i][j][side] = connection_type

    # Normalize each piece and store in a set
    normalized_pieces = {tuple(normalize_piece(solution_matrix[i][j])) for i in range(n) for j in range(n)}
    
    return normalized_pieces

def enforce_same_pieces(solver, puzzle_vars, normalized_pieces, n, m):
    """
    Add constraints to the solver to enforce that the second solution must use the same set of pieces.
    """
    for i in range(n):
        for j in range(n):
            # For each piece in the grid, enforce that it must be one of the normalized pieces
            valid_piece_clauses = []
            for piece in normalized_pieces:
                # For each normalized piece, generate all rotations and enforce one of them
                for r in range(4):  # 4 rotations
                    rotated_piece = piece[r:] + piece[:r]
                    valid_rotation_clause = []
                    for side in range(4):
                        valid_rotation_clause.append(puzzle_vars[(i, j, side)][rotated_piece[side]])
                    valid_piece_clauses.append(valid_rotation_clause)
            
            # Enforce that at least one valid rotation of the piece must be chosen
            solver.add_clause([lit for clause in valid_piece_clauses for lit in clause])


def setup_puzzle_constraints(solver, n, m, initial_edges):
    """
    Function to setup the SAT solver constraints for the n x n puzzle.
    Each piece will have four connections (top, right, bottom, left), and adjacent pieces must fit together.
    initial_edges: dictionary {(i, j): [top, right, bottom, left]} specifying initial clues for specific pieces.
    """
    # Create variables for all pieces
    puzzle_vars = {}
    for i in range(n):
        for j in range(n):
            for side in range(4):  # 0=top, 1=right, 2=bottom, 3=left
                puzzle_vars[(i, j, side)] = [var(i, j, side, n, m) + t for t in range(m)]
    
    # Debug: Print generated variable IDs
    #print("Puzzle Variables:")
   # for key, value in puzzle_vars.items():
     #   print(f"{key}: {value}")


    # Enforce connection matching between adjacent pieces
    for i in range(n):
        for j in range(n):
            # Ensure each side has exactly one connection type
            for side in range(4):
                exactly_one(puzzle_vars[(i, j, side)], solver)
            
            # Enforce matching between adjacent pieces
            if i > 0:  # Top piece matches bottom of the piece above
                enforce_match(solver, puzzle_vars[(i, j, 0)], puzzle_vars[(i-1, j, 2)])
            if j > 0:  # Left piece matches right of the piece to the left
                enforce_match(solver, puzzle_vars[(i, j, 3)], puzzle_vars[(i, j-1, 1)])
    
    # Apply initial edge constraints
    for (i, j), edges in initial_edges.items():
        for side, edge_type in enumerate(edges):
            if edge_type is not None:
                 # If edge_type is given (not None), fix that connection type for the side
                if edge_type < m:  # Ensure the edge type is within bounds
                    solver.add_clause([puzzle_vars[(i, j, side)][edge_type]])
                else:
                    print(f"Invalid edge_type {edge_type} for piece {(i, j)} on side {side}.")
    return puzzle_vars

def print_solution(model, puzzle_vars, n, m):
    """
    Print the solution found by the SAT solver as a matrix.
    Each entry in the matrix will be an array of connection types for the corresponding puzzle piece.
    """
    # Initialize the solution matrix
    solution_matrix = [[None for _ in range(n)] for _ in range(n)]
    
   
    # Extract the values for each piece and side
    for var in model:
        if var > 0:  # Only consider positive literals
            # Find the corresponding piece and side
            for (i, j, side) in puzzle_vars:
                if var in puzzle_vars[(i, j, side)]:
                    connection_type = puzzle_vars[(i, j, side)].index(var)
                    if solution_matrix[i][j] is None:
                        solution_matrix[i][j] = [None] * 4  # Initialize the array for sides
                    solution_matrix[i][j][side] = connection_type  # Assign the connection type

    # Print the solution matrix
    print("Solution Matrix:")
    for row in solution_matrix:
        print(row)  # Print each row of the matrix
    

def solve_puzzle_with_two_solutions(n, m, initial_edges):
    """
    Solve the puzzle using SAT solver and ensure two distinct solutions.
    n: Size of the grid (n x n)
    m: Number of connection types
    initial_edges: dictionary containing the predefined edge types for certain pieces
    """
    solver = Glucose3()

    # Step 1: Set up the constraints for the puzzle
    puzzle_vars = setup_puzzle_constraints(solver, n, m, initial_edges)

    # Step 2: Solve for the first solution
    if solver.solve():
        first_solution = solver.get_model()
        print("First solution found!")
        print_solution(first_solution, puzzle_vars, n, m)

        # Extract normalized pieces from the first solution
        normalized_pieces = extract_normalized_pieces(first_solution, puzzle_vars, n, m)

        # Step 3: Block the first solution and solve for a second distinct solution
        solver.add_clause([-lit for lit in first_solution if lit > 0])  # Block first solution

        # Enforce that the second solution must use the same pieces (in any rotation)
        enforce_same_pieces(solver, puzzle_vars, normalized_pieces, n, m)


        if solver.solve():
            second_solution = solver.get_model()
            print("Second solution found!")
            print_solution(second_solution, puzzle_vars, n, m)
            # Step 4: Block second solution and check for any additional solutions
            solver.add_clause([-lit for lit in second_solution if lit > 0])  # Block second solution
            
            if not solver.solve():
                print("No further solutions exist, exactly two solutions found.")
            else:
                third_sol = solver.get_model()
                print("More than two solutions exist!")
                print_solution(third_sol, puzzle_vars, n, m)
        else:
            print("No second solution found!")
    else:
        print("No solution found!")

# Main execution
if __name__ == "__main__":
    n = 3  # Example grid size
    m = 3  # Example number of connection types
    initial_edges = {
    (0, 0): [None, 1, 2, None],  # Top-left piece: right connection = 1, bottom connection = 2
    (1, 1): [2, None, None, 1],  # Center piece: top connection = 2, left connection = 0
    (2, 2): [None, None, None, 1], # Bottom-right piece: left connection = 1
    (0, 1): [None, 1, None, 1]
}
    solve_puzzle_with_two_solutions(n, m, initial_edges)