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
    return i * n * 4 * m + j * 4 * m + side * m

def exactly_one(lits, solver):
    """Ensure exactly one literal is True among the given literals (for a connection type)."""
    solver.add_clause(lits)  # At least one true
    for pair in product(lits, repeat=2):
        if pair[0] != pair[1]:
            solver.add_clause([-pair[0], -pair[1]])  # No two true

def enforce_match(solver, piece1, piece2):
    """Enforce that two pieces have matching connection types."""
    for t in range(m):  # m is the number of connection types
        solver.add_clause([-piece1[t], piece2[t]])
        solver.add_clause([piece1[t], -piece2[t]])

def setup_puzzle_constraints(solver, n, m):
    """
    Function to setup the SAT solver constraints for the n x n puzzle.
    Each piece will have four connections (top, right, bottom, left), and adjacent pieces must fit together.
    """
    # Create variables for all pieces
    puzzle_vars = {}
    for i in range(n):
        for j in range(n):
            for side in range(4):  # 0=top, 1=right, 2=bottom, 3=left
                puzzle_vars[(i, j, side)] = [var(i, j, side, n, m) + t for t in range(m)]
    
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
    
    return puzzle_vars

def solve_puzzle_with_two_solutions(n, m):
    """
    Solve the puzzle using SAT solver and ensure two distinct solutions.
    n: Size of the grid (n x n)
    m: Number of connection types
    """
    solver = Glucose3()

    # Step 1: Set up the constraints for the puzzle
    puzzle_vars = setup_puzzle_constraints(solver, n, m)

    # Step 2: Solve for the first solution
    if solver.solve():
        first_solution = solver.get_model()
        print("First solution found!")

        # Step 3: Block the first solution and solve for a second distinct solution
        solver.add_clause([-lit for lit in first_solution if lit > 0])  # Block first solution
        
        if solver.solve():
            second_solution = solver.get_model()
            print("Second solution found!")

            # Step 4: Block second solution and check for any additional solutions
            solver.add_clause([-lit for lit in second_solution if lit > 0])  # Block second solution
            if not solver.solve():
                print("No further solutions exist, exactly two solutions found.")
            else:
                print("More than two solutions exist!")
        else:
            print("No second solution found!")
    else:
        print("No solution found!")

# Example usage
n = 3  # Size of the puzzle (n x n)
m = 3  # Number of distinct connection types
solve_puzzle_with_two_solutions(n, m)
