from generator_V4 import *
from pysat.solvers import CryptoMinisat
from pysat.solvers import Glucose3
from itertools import product
from collections import Counter
from pysat.formula import IDPool
from utility_v2 import *
from pysat.card import CardEnc
import time
import psutil
import random
import os
from mapping import *

def enforce_piece_id_and_connection_type(solver, conn_vars, jig_id):
    """Enforce that the piece variable is only true if all the connection variables are true."""
    for var in conn_vars:
        solver.add_clause([-jig_id, var])
      #solver.add_clause([jig_id] + [-var for var in conn_vars])

def print_solution(model, puzzle_vars, n, m, jig_vars=None, mapped_jig_vars=None, verbose=True):
    """
    Print the solution matrices with piece IDs.
    """
   # Pre-initialize solution matrices with None
    solution_matrix0 = [[[None] * 4 for _ in range(n)] for _ in range(n)]
    solution_matrix1 = [[[None] * 4 for _ in range(n)] for _ in range(n)]

    for (y,x,o), jig_var in jig_vars.items():
        if jig_var in model:
            for side in range(4):
                for conntype in range(m):
                    if puzzle_vars[(y,x,side,conntype,0)] in model:
                        solution_matrix0[y][x][side] = conntype
                        break
    
    for (y,x,o), jig_var in mapped_jig_vars.items():
        if jig_var in model:
            for side in range(4):
                for conntype in range(m):
                    if puzzle_vars[(y,x,side,conntype,1)] in model:
                        solution_matrix1[y][x][side] = conntype
                        break
            

    
    print("Solution Matrix:")
    solution_matrix0 = Add_connection_direction(solution_matrix0,n)
    solution_matrix1 = Add_connection_direction(solution_matrix1,n)
    if verbose == True:
        print("Sol0")
        for row in solution_matrix0:
            print(row)
        print("Sol1")
        for row in solution_matrix1:
            print(row)
        
    return [solution_matrix0, solution_matrix1]

def constraints(n, m, puzzle, solver,balance,row_constraint):
    edge_vars = {}
    id_pool = IDPool()

    for i in range(n):
        for j in range(n):
            for side in range(4):
                for conn in range(m):
                    for sol in range(2):
                        edge_vars[(i, j, side, conn, sol)] = id_pool.id(f'var{sol}_{i}_{j}_{side}={conn}')
    # Apply constrain on usable jigs, all jigs are able to be placed at any position in the grid in any ortientation
    #this can be done by adding a clause that forces the new variable to be true if all connections of a piece are true.
    jig_vars = {}
    mapped_jig_vars = {}
    mapping_, mapped_puzzle = mapping(n,n, puzzle)

    for (y, x, o), jig in puzzle.items():
        jig_id = id_pool.id(f'jig0_{y}_{x}_{o}')
        jig_vars[(y, x, o)] = jig_id
        conn_vars = []
        for side, connection in enumerate(jig):
            if connection == None:
                continue
            conn_vars.append(edge_vars[(y, x, side, connection,0)])
            
        enforce_piece_id_and_connection_type(solver, conn_vars, jig_id)

        #enforce that the piece is only used once/is used
        solver.add_clause([jig_vars[(y, x, o)]])

    for (y, x, o), jig in mapped_puzzle.items():
        jig_id = id_pool.id(f'jig1_{y}_{x}_{o}')
        mapped_jig_vars[(y, x, o)] = jig_id
        conn_vars = []
        for side, connection in enumerate(jig):
            if connection == None:
                continue
            conn_vars.append(edge_vars[(y, x, side, connection,1)])
            
        enforce_piece_id_and_connection_type(solver, conn_vars, jig_id)

        #enforce that the piece is only used once/ is used
        solver.add_clause([mapped_jig_vars[(y, x, o)]])

    #enforce that interior pieces never have conn type 0
    for i in range(1, n-1):
        for j in range(1, n-1):
            for side in range(4):
                    solver.add_clause([-edge_vars[(i, j, side, 0,1)]])
                    solver.add_clause([-edge_vars[(i, j, side, 0,0)]])
    
    #enforce that edge pieces have no connection type 0 to the inside
    for i in range(n):
        for j in range(n):
            if i == 0:
                solver.add_clause([-edge_vars[(i, j, 2, 0,1)]])
                solver.add_clause([-edge_vars[(i, j, 2, 0,0)]])
                if not j == n-1:
                    solver.add_clause([-edge_vars[(i, j, 1, 0,1)]])
                    solver.add_clause([-edge_vars[(i, j, 1, 0,0)]])
                if not j == 0:
                    solver.add_clause([-edge_vars[(i, j, 3, 0,1)]])
                    solver.add_clause([-edge_vars[(i, j, 3, 0,0)]])
            elif i == n-1:
                solver.add_clause([-edge_vars[(i, j, 0, 0,1)]])
                solver.add_clause([-edge_vars[(i, j, 0, 0,0)]])
                if not j == n-1:
                    solver.add_clause([-edge_vars[(i, j, 1, 0,1)]])
                    solver.add_clause([-edge_vars[(i, j, 1, 0,0)]])
                if not j == 0:
                    solver.add_clause([-edge_vars[(i, j, 3, 0,1)]])
                    solver.add_clause([-edge_vars[(i, j, 3, 0,0)]])
            if j == 0:
                solver.add_clause([-edge_vars[(i, j, 1, 0,1)]])
                solver.add_clause([-edge_vars[(i, j, 1, 0,0)]])
                if not i == n-1:
                    solver.add_clause([-edge_vars[(i, j, 2, 0,1)]])
                    solver.add_clause([-edge_vars[(i, j, 2, 0,0)]])
                if not i == 0:
                    solver.add_clause([-edge_vars[(i, j, 0, 0,1)]])
                    solver.add_clause([-edge_vars[(i, j, 0, 0,0)]])
            if j == n-1:
                solver.add_clause([-edge_vars[(i, j, 3, 0,1)]])
                solver.add_clause([-edge_vars[(i, j, 3, 0,0)]])
                if not i == n-1:
                    solver.add_clause([-edge_vars[(i, j, 2, 0,1)]])
                    solver.add_clause([-edge_vars[(i, j, 2, 0,0)]])
                if not i == 0:
                    solver.add_clause([-edge_vars[(i, j, 0, 0,1)]])
                    solver.add_clause([-edge_vars[(i, j, 0, 0,0)]])

    #enforce that each piece has at least one connection (no None)
    for i in range(n):
        for j in range(n):
            for sol in range(2):
                for side in range(4):
                    exactly_one([edge_vars[(i, j, side, conn, sol)] for conn in range(m)], solver,id_pool)

    #enforce that if a connection is true in the mapped puzzle, it is also true in the original puzzle, considering the rotation and displacement
    for (y, x, o), (i,j,o1) in mapping_.items():
        for side1 in range(4):
            for conn in range(m):
                rot = (side1+o1)%4
                solver.add_clause([edge_vars[(i, j, rot, conn, 1)], -edge_vars[(y, x, side1, conn, 0)]])
                solver.add_clause([-edge_vars[(i, j, rot, conn, 1)], edge_vars[(y, x, side1, conn, 0)]])

    #enforce that a given connection type is only used a certain amount of times

    for conn in range(m):
        lits0 = []
        lits1 = []
        for i in range(n):
            for j in range(n):
                for side in range(4):
                    lits0.append(edge_vars[(i, j, side, conn, 0)])

        card  = CardEnc.atmost(lits=lits0, bound=balance, encoding=1, vpool=id_pool)
        solver.append_formula(card)
                        


    # Enforce connection matching between adjacent pieces
    for i in range(n):
        for j in range(n):
            for sol in range(2):
                # Enforce matching between adjacent pieces
                if i > 0:  # Top piece matches bottom of the piece above
                        conns2 = [edge_vars[(i-1, j, 2, conn, sol)] for conn in range(m)]
                        conns1 = [edge_vars[(i, j, 0, conn, sol)] for conn in range(m)]
                        enforce_match(solver, conns1, conns2)
                if j > 0:  # Left piece matches right of the piece to the left
                        conns2 = [edge_vars[(i, j, 3, conn, sol)] for conn in range(m)]
                        conns1 = [edge_vars[(i, j-1, 1, conn, sol)] for conn in range(m)]
                        enforce_match(solver, conns1, conns2)



    if puzzle is not None:
        return edge_vars, jig_vars, mapped_jig_vars, id_pool, mapping_
    else:
        return edge_vars, id_pool




def solve(n,m,puzzle,verbose=True,balance=10000,row_constraint=100):
    solver = CryptoMinisat()
    edge_vars, jig_vars,mapped_jig_vars, pool, piece_mapping = constraints(n, m, puzzle, solver,balance,row_constraint)

    solver.solve()
    model = solver.get_model()
        
    solutions = []
    if model is not None:
        print("Solution found!")
        print("---------------------------")
        print("Solution found!")
        solutions = print_solution(model, edge_vars, n, m, jig_vars=jig_vars, mapped_jig_vars=mapped_jig_vars, verbose=verbose)
    if verbose:
        print(f"Found {len(solutions)} solutions")
    return solutions, piece_mapping


def jig_main(n=5,initialized_connections=0, m=2, verbose=False, balance=10000,row_constraint=100):
    
    if verbose:
        print(f"Using m = {m}")
    m = 2*m + 1
    
    puzzle = generate_jigsaw_puzzle(n, m=m, initialized_connections=initialized_connections)

    initial_edges = {}

    for y in range(n):
        for x in range(n):
            initial_edges[(y, x, 0)] = [puzzle[y][x][0], puzzle[y][x][1], puzzle[y][x][2], puzzle[y][x][3]]
    
    """initial_edges_true = {
            (0, 0, 0): [0, 1, 2, 0],  # Top-left piece: right connection = 1, bottom connection = 2
            (0, 1, 0): [0, 2, 4, 1],  # Center piece: top connection = 2, left connection = 0
            (0, 2, 0): [0, 0, 1, 2],
            (1, 0, 0): [2, 4, 1, 0],  # Bottom-right piece: left connection = 1
            (1, 1, 0): [4, 3, 4, 4],
            (1, 2, 0): [1, 0, 3, 3],
            (2, 0, 0): [1, 4, 0, 0],
            (2, 1, 0): [4, 1, 0, 4],
            (2, 2, 0): [3, 0, 0, 1]
        }"""

    solve_this_puzzle = initial_edges
   
    solutions, piece_mapping = solve(n, 
                      m, 
                      solve_this_puzzle,
                      verbose=verbose,
                      balance = balance,
                      row_constraint=row_constraint)
    
    if len(solutions) > 1:
        save_solutions(solutions, n, m, piece_mapping)
    return solutions
    

def save_solutions(solutions, n, m, piece_mapping):
    t = get_counter()
    increment_counter(t)
    #save mapping dictionary with numpy
    np.save(f'Solutions/Mapping_{n}_{m}_{t}.npy', piece_mapping)
    for i, solution in enumerate(solutions):
        solution = np.array(solution)
        np.save(f'Solutions/Solution_{n}_{m}_{i}_{t}.npy', solution)

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



