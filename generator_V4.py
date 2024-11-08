import numpy as np
import random

def generate_jigsaw_puzzle(n, m=5, initialized_connections=0):
    # Initialize the puzzle with all entries as -1 (undecided)
    puzzle = np.full((n, n, 4), None)
    
    # Directions: 0 = top, 1 = right, 2 = bottom, 3 = left
    # Set outer edges to 0
    for i in range(n):
        puzzle[0, i, 0] = 0    # Top row
        puzzle[n-1, i, 2] = 0   # Bottom row
        puzzle[i, 0, 3] = 0     # Left column
        puzzle[i, n-1, 1] = 0   # Right column

    # List to hold potential inner connections (i, j, direction)
    # direction: 0 = top, 1 = right, 2 = bottom, 3 = left
    possible_connections = []
    
    # Collect all possible internal connections for random selection
    for i in range(n):
        for j in range(n):
            if i < n - 1:  # Bottom connection for all but the last row
                possible_connections.append((i, j, 2))
            if j < n - 1:  # Right connection for all but the last column
                possible_connections.append((i, j, 1))

    # Randomly select m connections to initialize
    selected_connections = random.sample(possible_connections, min(initialized_connections, len(possible_connections)))

    for i, j, direction in selected_connections:
        # Generate a random connection value
        connection_value = random.randint(1, m-1)
        
        if direction == 2:  # Bottom connection
            if connection_value % 2 == 0:
                puzzle[i, j, 2] = connection_value  # Set bottom of current piece
                puzzle[i + 1, j, 0] = connection_value-1  # Set top of piece below
            else:
                puzzle[i, j, 2] = connection_value
                puzzle[i + 1, j, 0] = connection_value+1
        elif direction == 1:  # Right connection
            if connection_value % 2 == 0:
                puzzle[i, j, 1] = connection_value
                puzzle[i, j + 1, 3] = connection_value-1
            else:
                puzzle[i, j, 1] = connection_value  # Set right of current piece
                puzzle[i, j + 1, 3] = connection_value +1  # Set left of piece to the right

    return puzzle

def Add_connection_direction(puzzle, n):
    for y in range(0, n):
        for x in range(0, n):
            if not puzzle[y][x]== None:
                for i in range(0,4):
                    if not puzzle[y][x][i]== None:
                        if puzzle[y][x][i] % 2 == 0:
                            if puzzle[y][x][i] == 0:
                                pass
                            else:
                                puzzle[y][x][i] = -(puzzle[y][x][i]-1)
                
                        else:
                            if puzzle[y][x][i] == 0:
                                pass
                            else:
                                puzzle[y][x][i] = puzzle[y][x][i]
    return puzzle



