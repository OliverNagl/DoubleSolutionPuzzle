import numpy as np
from mapping import *
def propagate_solution(n,m,inital_edges):
    #Start at a puzzle with initializing a array of n x n x 4 with None
    puzzle = np.full((n, n, 4), None)
    #Set the outer edges to 0
    for i in range(n):
        puzzle[0, i, 0] = 0    # Top row
        puzzle[n-1, i, 2] = 0   # Bottom row
        puzzle[i, 0, 3] = 0     # Left column
        puzzle[i, n-1, 1] = 0   # Right column

    # Get a map of the initial puzzle configuration to a new configuration
    mapping_, puzzle1 = mapping(n, m, inital_edges)

    #Start randomly assigning connections to the puzzle and propagate to the second puzzle
    while None in puzzle:
        head = (0,0,0)
        