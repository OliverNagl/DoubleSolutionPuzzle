from pysat.solvers import CryptoMinisat
from pysat.solvers import Glucose3
from itertools import product
from collections import Counter
from pysat.formula import IDPool
from generator_V3 import *
from utility_v2 import *
from pysat.card import CardEnc
import time
import psutil
import random
import os

def print_solution(model, puzzle_vars, n, m, jigs=None):
    """
    Print the solution matrix with piece IDs.
    """
    reverse_puzzle_vars = {value: key for key, value in puzzle_vars.items()}
    if jigs is not None:
        revers_jig_vars = {value: key for key, value in jigs.items()}
    solution_matrix = [[None for _ in range(n)] for _ in range(n)]

    for var in model:
        if var > 0:  # Only consider positive literals
            if var in reverse_puzzle_vars:
                i, j, side, m = reverse_puzzle_vars[var]
                if solution_matrix[i][j] is None:
                    if jigs is not None:
                        solution_matrix[i][j] = [None] * 6
                    else:
                        solution_matrix[i][j] = [None] * 4
                solution_matrix[i][j][side] = m

            if jigs is not None:
                if var in revers_jig_vars:
                    y_jig, x_jig , i, j, o = revers_jig_vars[var]
                    solution_matrix[i][j][4] = f"y:{y_jig}" 
                    solution_matrix[i][j][5] = f"x:{x_jig}"

    print("Solution Matrix:")
    solution_matrix = Add_connection_direction(solution_matrix,n)
    for row in solution_matrix:
        print(row)
    return solution_matrix

def constraints(n, m, jigs, solver, card=None):
    edge_vars = {}
    id_pool = IDPool()

    for i in range(n):
        for j in range(n):
            for side in range(4):
                for conn in range(m):
                    edge_vars[(i, j, side, conn)] = id_pool.id(f'var_{i}_{j}_{side}={conn}')

    if jigs is not None:
        # Apply constrain on usable jigs, all jigs are able to be placed at any position in the grid in any ortientation
        #this can be done by adding a clause that forces the new variable to be true if all connections of a piece are true.
        jig_vars = {}
        for (x, y, o), jig in jigs.items():
            if jig is not [0,0,0,0]:
                for i in range(n):
                    for j in range(n):
                        jig_id = id_pool.id(f'jig_{x}_{y}->{i}_{j}_{o}')
                        jig_vars[(x, y, i, j, o)] = jig_id
                        conn_vars = []
                        for side, connection in enumerate(jig):
                            conn_vars.append(edge_vars[(i, j, side, connection)])
                        enforce_piece_id_and_connection_type(solver, conn_vars, jig_id)

        #enforce cardinality constrain on the jigs to ensure that similar jigs are only used exactly n times
        # where n is the cardinality of the jig.
        if card is not None:
            for (x,y), cardinality in card.items():
                jig_clause = []
                for o in range(4):
                    if jigs[(x, y, o)] != [0,0,0,0]:
                        for i in range(n):
                            for j in range(n):
                                jig_clause.append(jig_vars[(x, y, i, j, o)])
                exactly_n2(jig_clause, solver, cardinality, id_pool)

        # Enforce exactly one jig orientation per cell and one jig per cell total
        for i in range(n):
            for j in range(n):
                jig_clause = []
                for x in range(n):
                    for y in range(n):
                        for o in range(4):
                            jig_clause.append(jig_vars[(x, y, i, j, o)])
                exactly_one(jig_clause, solver,id_pool)

    # Add constraints for each cell
         # Enforce the '0' connection type can only be used on edges or corners
    for i in range(n):
        for j in range(n):
            # Corners
            if (i == 0 and j == 0):  # Top-left corner
                solver.add_clause([edge_vars[(i, j, 0, 0)]])  # Top side = 0
                solver.add_clause([edge_vars[(i, j, 3, 0)]])  # Left side = 0
                solver.add_clause([-edge_vars[(i, j, 1, 0)]])
                solver.add_clause([-edge_vars[(i, j, 2, 0)]])
                
            elif (i == 0 and j == n-1):  # Top-right corner
                    solver.add_clause([edge_vars[(i, j, 0, 0)]])  # Top side = 0
                    solver.add_clause([edge_vars[(i, j, 1, 0)]])  # Left side = 0
                    solver.add_clause([-edge_vars[(i, j, 2, 0)]])
                    solver.add_clause([-edge_vars[(i, j, 3, 0)]])
            elif (i == n-1 and j == 0):  # Bottom-left corner
                
                solver.add_clause([edge_vars[(i, j, 2, 0)]])  # Top side = 0
                solver.add_clause([edge_vars[(i, j, 3, 0)]])  # Left side = 0
                solver.add_clause([-edge_vars[(i, j, 1, 0)]])
                solver.add_clause([-edge_vars[(i, j, 0, 0)]])
            elif (i == n-1 and j == n-1):  # Bottom-right corner
                solver.add_clause([edge_vars[(i, j, 2, 0)]])  # Top side = 0
                solver.add_clause([edge_vars[(i, j, 1, 0)]])  # Left side = 0
                solver.add_clause([-edge_vars[(i, j, 3, 0)]])
                solver.add_clause([-edge_vars[(i, j, 0, 0)]])

            # Edges (excluding corners)
            elif i == 0:  # Top row, excluding corners
             
                solver.add_clause([edge_vars[(i, j, 0, 0)]])  # Top side = 0
                solver.add_clause([-edge_vars[(i, j, 1, 0)]])  # Left side = 0
                solver.add_clause([-edge_vars[(i, j, 2, 0)]])
                solver.add_clause([-edge_vars[(i, j,3, 0)]])
            
            elif i == n-1:  # Bottom row, excluding corners
             
                solver.add_clause([edge_vars[(i, j, 2, 0)]])  # Top side = 0
                solver.add_clause([-edge_vars[(i, j, 1, 0)]])  # Left side = 0
                solver.add_clause([-edge_vars[(i, j, 0, 0)]])
                solver.add_clause([-edge_vars[(i, j, 3, 0)]])
                
            elif j == 0:  # Left column, excluding corners
                solver.add_clause([edge_vars[(i, j, 3, 0)]])  # Top side = 0
                solver.add_clause([-edge_vars[(i, j,1, 0)]])  # Left side = 0
                solver.add_clause([-edge_vars[(i, j, 2, 0)]])
                solver.add_clause([-edge_vars[(i, j, 0, 0)]])
            elif j == n-1:  # Right column, excluding corners
                solver.add_clause([edge_vars[(i, j, 1, 0)]])  # Top side = 0
                solver.add_clause([-edge_vars[(i, j,0, 0)]])  # Left side = 0
                solver.add_clause([-edge_vars[(i, j, 2, 0)]])
                solver.add_clause([-edge_vars[(i, j, 3, 0)]])

            # Interior pieces should not have connection type 0
            else:
                for side in range(4):
                    solver.add_clause([-edge_vars[(i, j, side, 0)]])
    

    # Enforce connection matching between adjacent pieces
    for i in range(n):
        for j in range(n):
            for side in range(4):
                #enforce only one connection type per side
                exactly_one([edge_vars[(i, j, side, conn)] for conn in range(m)], solver,id_pool)

            # Enforce matching between adjacent pieces
            if i > 0:  # Top piece matches bottom of the piece above
                conns2 = [edge_vars[(i-1, j, 2, conn)] for conn in range(m)]
                conns1 = [edge_vars[(i, j, 0, conn)] for conn in range(m)]
                    
                enforce_match(solver, conns1, conns2)
            if j > 0:  # Left piece matches right of the piece to the left
                conns2 = [edge_vars[(i, j, 3, conn)] for conn in range(m)]
                conns1 = [edge_vars[(i, j-1, 1, conn)] for conn in range(m)]
                enforce_match(solver, conns1, conns2)

    if jigs is not None:
        return edge_vars, jig_vars, id_pool
    else:
         edge_vars, id_pool

def enforce_piece_id_and_connection_type(solver, conn_vars, jig_id):
    """Enforce that the piece variable is only true if all the connection variables are true."""
    for var in conn_vars:
        solver.add_clause([-jig_id, var])
      #solver.add_clause([jig_id] + [-var for var in conn_vars])

def solve(n,m, jigs, card=None, diff = 0,Same_pieces_k=0,same_neighbours_k=0,disable_rotations=0):
    solutions = []
    model = []
    """Solve the puzzle, dissable first solution and solve for a second solution"""
    for i in range(2):
        solver = CryptoMinisat()
        edge_vars, jig_vars, pool = constraints(n, m, jigs, solver, card=card)

        if i == 1 and model[0] is not None:
            dissable_solution(n, solver, model[0], edge_vars, jig_vars, jigs, pool, bound=diff, Same_pieces_k=Same_pieces_k, same_neighbours_k=same_neighbours_k, disable_rotations=disable_rotations)

        solver.solve()
        model.append(solver.get_model())
        

        if model[i] is not None:
            print("Solution found!")
            solution_matrix = print_solution(model[i], edge_vars, n, m, jigs=jig_vars)
            solutions.append(solution_matrix)

    print(f"Found {len(solutions)} solutions")
    return solutions


def find_neighbours_vars(y,x,i,j,o, n,jig_vars):
    """Find the neighbours of a piece at position (x, y) on an n x n grid."""
    neighbours = []
    if x > 0 and j > 0:
        for o in range(4):
            neighbours.append(jig_vars[(y, x-1, i, j-1, o)])
        
    if x < n - 1 and j < n - 1:
        for o in range(4):
            neighbours.append(jig_vars[(y, x+1, i, j+1, o)])
        
    if y > 0 and i > 0:
        for o in range(4):
            neighbours.append(jig_vars[(y-1, x, i-1, j, o)])
        
    if y < n - 1 and i < n - 1:
        for o in range(4):
            neighbours.append(jig_vars[(y+1,x, i+1, j, o)])
    
    return neighbours

def dissable_solution(n, solver, model, edge_vars, jig_vars, jigs, pool, bound=0, Same_pieces_k= 0, same_neighbours_k=0,disable_rotations=1):
    """Dissable the current solution by adding a clause that forces the current jigs to be false if their
    entartung is 0."""
    dissable_clause = []
    rotation_clause = []
    rotation_1_clause = []
    rotation_2_clause = []
    rotation_3_clause = []
    rotation_0_clause = []
    neighbour_clause = []
    for (x,y,i,j,o), var in jig_vars.items():
        if entartung(jigs[(x,y,o)]) == 0:
            if var in model and var > 0:
                dissable_clause.append(-var)   
        
        if var in model and var > 0:
            neighbours = find_neighbours_vars(y,x,i,j,o,n,jig_vars)
        
            # Now, add the rotated versions of the jig
            for rotation in range(0, 4):  # Rotate by 90, 180, 270 degrees
                rotated_y, rotated_x, drehung  = rotate_coordinates(y, x, o, n, rotation)
                
                if rotation == 0:
                    rotated_var = jig_vars[(x,y,rotated_y,rotated_x , drehung)]
                    rotation_0_clause.append(-rotated_var)
                elif rotation == 1:
                    rotated_var = jig_vars[(x,y,rotated_y,rotated_x , drehung)]
                    rotation_1_clause.append(-rotated_var)
                elif rotation == 2:
                    rotated_var = jig_vars[(x,y,rotated_y,rotated_x , drehung)]
                    rotation_2_clause.append(-rotated_var)
                elif rotation == 3:
                    rotated_var = jig_vars[(x,y,rotated_y,rotated_x , drehung)]
                    rotation_3_clause.append(-rotated_var)


    #create a global rotation variable that is false if all the rotation clauses in rotation_x_ckause are true
   
   
    """k1 = k2 = k3 = disable_rotations
    #solver.add_clause(rotation_1_clause)
    enc = CardEnc.atleast(lits=rotation_1_clause, bound=k1,encoding=1, vpool=pool)
    solver.append_formula(enc.clauses)

    #solver.add_clause(rotation_2_clause)
    enc = CardEnc.atleast(lits=rotation_2_clause, bound=k2,encoding=1, vpool=pool)
    solver.append_formula(enc.clauses)

    #solver.add_clause(rotation_3_clause)
    enc = CardEnc.atleast(lits=rotation_3_clause, bound=k3,encoding=1, vpool=pool)
    solver.append_formula(enc.clauses)
"""
    k4 = len(rotation_0_clause) - Same_pieces_k
    #solver.add_clause(rotation_0_clause)
    enc = CardEnc.atleast(lits=rotation_0_clause, bound=k4,encoding=1, vpool=pool)
    solver.append_formula(enc.clauses)

    neighbour = CardEnc.atmost(lits=neighbour_clause, bound=same_neighbours_k,encoding=1, vpool=pool)
    solver.append_formula(neighbour.clauses)


import os

def get_counter():
    """Reads the counter from a file or initializes it if the file doesn't exist."""
    counter_file = 'counter.txt'
    if os.path.exists(counter_file):
        with open(counter_file, 'r') as f:
            t = int(f.read())
    else:
        t = 1  # Initialize t if this is the first run
        with open(counter_file, 'w') as f:
            f.write(str(t))
    return t

def increment_counter(t):
    """Increments the counter and saves it to a file."""
    counter_file = 'counter.txt'
    with open(counter_file, 'w') as f:
        f.write(str(t + 1))

def rotate_coordinates(y, x, o, n, rotation):
    """Rotate the coordinates (x, y) on an n x n grid by 90, 180, or 270 degrees. And return the new orientation which wraps around 4."""
    if rotation == 1:  # 90 degrees
        return x, n - 1 - y, (o + rotation) % 4
    elif rotation == 2:  # 180 degrees
        return n - 1 - y,n - 1 - x, (o + rotation) % 4
    elif rotation == 3:  # 270 degrees
        return n-1-x, y, (o + rotation) % 4
    else:
        return y, x, o  # 0 degrees (no rotation)

def symmetric(jig):
    """Check if a jig is symmetric."""
    return jig == rotate(rotate(jig))

def entartung(jig):
    """Return the entartung of a symmetric jig. Which is the number of rotations that are equivalent.
    for example entartung([4,4,4,4]) = 4, entartung([3,4,3,4]) = 2 and entartung([0,1,2,3]) = 0 """
    if jig == rotate(jig):
        return 4
    elif jig == rotate(rotate(jig)):
        return 2
    else:
        return 0


def are_similar(jig1, jig2):
    """Check if two jigs are similar considering rotation."""
    for _ in range(4):
        if jig1 == jig2:
            return True
        jig1 = rotate(jig1)
    return False

def get_cardinality(n, jigs):
    """Return the cardinality of the jigsaw puzzle. e.g. the count of similar jigs, that are only
    different in rotation and position."""
    cardinality = {}
    visited = set()
    
    for (i, j), jig in jigs.items():
        if (i, j) not in visited:
            cardinality[(i, j)] = 1
            for (k, l), other_jig in jigs.items():
                if (i, j) != (k, l) and are_similar(jig, other_jig):
                    cardinality[(i, j)] += 1
                    visited.add((k, l))
    
    return cardinality

def get_orientations(n, jigs):
    """
    input dict of pieces on a grid (i,j) and output dictionary of possible orientations for each piece
    (i,j,o) where o is the orientation. Delete jig if it is the sam as another jig """
    orientations = {}
    jig_list = []

    for (i, j), jig in jigs.items():
        for o in range(4):
            if jig not in jig_list:
                orientations[(i, j, o)] = jig
            else:
                orientations[(i, j, o)] = [0,0,0,0]

            jig_list.append(jig)
            jig = rotate(jig)
    return orientations

def rotate(jig):
    """
    Rotate a piece 90 degrees clockwise
    """
    return [jig[3]] + jig[:3]

def scramble_pieces(n, m, jigs):
    """
    Scramble the pieces in the grid.
    """
    scrambled_jigs = {}
    for i in range(1, n+1):
        for j in range(1, n+1):
            scrambled_jigs[(i-1, j-1)] = jigs[(n-i, n-j)]
    return scrambled_jigs

def main():
    n = 9 # Example grid size
    q = 2*n*2.71**(-1/2)
    m = int((2 + q)/2)
    print(f"Using m = {m}")
    m = 2*m + 1
    print(f"puzzle should have 2 < m < {q} connection types")
    
    puzzle = generate_random_valid_jigsaw(n, m, seed=50)

    initial_edges = {}

    for y in range(n):
        for x in range(n):
            initial_edges[(y, x)] = [int(puzzle[y][x][0]), int(puzzle[y][x][1]), int(puzzle[y][x][2]), int(puzzle[y][x][3])]
    
    solve_this_puzzle = initial_edges

    threshold = 0
    Same_pieces_k = 0
    same_neighbours_k = n**3*4
    disable_rotations = int(n**2-n)

    solutions = solve(n, 
                      m, 
                      get_orientations(n, solve_this_puzzle), 
                      get_cardinality(n, solve_this_puzzle), 
                      diff=threshold, 
                      Same_pieces_k=Same_pieces_k,
                      same_neighbours_k=same_neighbours_k,
                      disable_rotations = disable_rotations)
    
    save_solutions(solutions, n, m)
    

def save_solutions(solutions, n, m):
    t = get_counter()
    increment_counter(t)
    for i, solution in enumerate(solutions):
        solution = np.array(solution)
        np.save(f'Solutions/Solution_{n}_{m}_{i}_{t}.npy', solution)

if __name__ == "__main__":
    # Record start time and initial resource usage
    start_time = time.time()
    process = psutil.Process()
    start_memory = process.memory_info().rss

    # Execute the main function
    main()

    # Record end time and final resource usage
    end_time = time.time()
    end_memory = process.memory_info().rss

    # Calculate elapsed time and memory usage
    elapsed_time = end_time - start_time
    memory_usage = end_memory - start_memory

    # Print performance metrics
    print(f"Elapsed time: {elapsed_time:.2f} seconds")
    print(f"Memory usage: {memory_usage / (1024 * 1024):.2f} MB")



"""
    Debug section:
    initial_edges_false = {
            (0, 0): [0, 1, 2, 0],  # Top-left piece: right connection = 1, bottom connection = 2
            (0, 1): [0, 2, 4, 1],  # Center piece: top connection = 2, left connection = 0
            (0, 2): [0, 0, 1, 2],
            (1, 0): [2, 4, 1, 0],  # Bottom-right piece: left connection = 1
            (1, 1): [4, 3, 4, 4],
            (1, 2): [1, 0, 2, 4],
            (2, 0): [1, 2, 0, 0],
            (2, 1): [4, 1, 0, 2],
            (2, 2): [2, 0, 0, 1]
        }

        initial_edges_true = {
            (0, 0): [0, 1, 2, 0],  # Top-left piece: right connection = 1, bottom connection = 2
            (0, 1): [0, 2, 4, 1],  # Center piece: top connection = 2, left connection = 0
            (0, 2): [0, 0, 1, 2],
            (1, 0): [2, 4, 1, 0],  # Bottom-right piece: left connection = 1
            (1, 1): [4, 3, 4, 4],
            (1, 2): [1, 0, 3, 3],
            (2, 0): [1, 4, 0, 0],
            (2, 1): [4, 1, 0, 4],
            (2, 2): [3, 0, 0, 1]
        }

        initial_edges1 = {
            (0, 0): [0, 1, 2, 0],  # Top-left piece: right connection = 1, bottom connection = 2
            (0, 1): [0, 2, 4, 1],  # Center piece: top connection = 2, left connection = 0
            (0, 2): [0, 0, 1, 2],
            (1, 0): [2, 4, 1, 0],  # Bottom-right piece: left connection = 1
            (1, 1): [2, 0, 0, 1],
            (1, 2): [1, 0, 2, 4],
            (2, 0): [1, 2, 0, 0],
            (2, 1): [4, 1, 0, 2],
            (2, 2): [4, 4, 4, 4]
        }

"""


    