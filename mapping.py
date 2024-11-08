import random
from generator_V4 import *
def generate_positions(n, m):
    # Generate positions for corners, edges, and interiors
    corners = [(0, 0), (0, m-1), (n-1, 0), (n-1, m-1)]
    edges = [(0, x) for x in range(1, m-1)] + \
            [(n-1, x) for x in range(1, m-1)] + \
            [(y, 0) for y in range(1, n-1)] + \
            [(y, m-1) for y in range(1, n-1)]
    interior = [(y, x) for y in range(1, n-1) for x in range(1, m-1)]
    return corners, edges, interior

def calculate_rotation(source, target, n,m):
    # Determines the number of rotations (0, 1, 2, or 3) required to match the target orientation
    # Mapping of corners based on their positions (in clockwise order starting from top-left)
    corners = [(0, 0), (0, m-1), (n-1, m-1), (n-1, 0)]
    if source in corners and target in corners:
        src_index = corners.index(source)
        tgt_index = corners.index(target)
        # Determine the clockwise rotation needed
        return (tgt_index - src_index) % 4
    else:
        # For edges, define a similar mapping by side positions (top, right, bottom, left)
        if source[0] == 0:  # Top edge
            if target[0] == 0: return 0  # Top-to-top
            elif target[1] == m-1: return 1  # Top-to-right
            elif target[0] == n-1: return 2  # Top-to-bottom
            elif target[1] == 0: return 3  # Top-to-left
        elif source[1] == m-1:  # Right edge
            if target[1] == m-1: return 0  # Right-to-right
            elif target[0] == n-1: return 1  # Right-to-bottom
            elif target[1] == 0: return 2  # Right-to-left
            elif target[0] == 0: return 3  # Right-to-top
        elif source[0] == n-1:  # Bottom edge
            if target[0] == n-1: return 0  # Bottom-to-bottom
            elif target[1] == 0: return 1  # Bottom-to-left
            elif target[0] == 0: return 2  # Bottom-to-top
            elif target[1] == m-1: return 3  # Bottom-to-right
        elif source[1] == 0:  # Left edge
            if target[1] == 0: return 0  # Left-to-left
            elif target[0] == 0: return 1  # Left-to-top
            elif target[1] == m-1: return 2  # Left-to-right
            elif target[0] == n-1: return 3  # Left-to-bottom
    return None  # Interior pieces don't require special rotations

def mapping(n, m, initial_edges):
    # Generate a mapping of the initial puzzle configuration to a new configuration
    # returns a dictionary of the final mapped puzzle configuration as well
    # as a dictionary of that mapps (y,x,o) to (i,j,o1)


    # Generate available positions
    corners, edges, interior = generate_positions(n, m)
    
    final_edges = {}
    mapping_ = {}
    # Map corners
    corner_positions = [(n-1, m-1), (n-1,0), (0, m-1), (0,0)]
    corner_pieces = [pos for pos in initial_edges if pos[:2] in corners]
    for i in range(len(corner_pieces)):
        piece = initial_edges[corner_pieces[i]]
        target_position = corner_positions[i]
        rotations_needed = calculate_rotation(corner_pieces[i][:2], target_position, n,m)
        final_position = (target_position[0], target_position[1], rotations_needed)
        final_edges[final_position] = rotate(piece, rotations_needed)
        mapping_[corner_pieces[i]] = final_position  # Track the mapping
    # Map edges
    edge_positions = random.sample(edges, len(edges))
    edge_pieces = [pos for pos in initial_edges if pos[:2] in edges]
    for i in range(min(len(edge_pieces), len(edge_positions))):
        piece = initial_edges[edge_pieces[i]]
        target_position = edge_positions[i]
        rotations_needed = calculate_rotation(edge_pieces[i][:2], target_position,n,m)
        final_position = (target_position[0], target_position[1], rotations_needed)
        final_edges[final_position] = rotate(piece, rotations_needed)
        mapping_[edge_pieces[i]] = final_position  # Track the mapping
    
    # Map interior pieces
    interior_positions = random.sample(interior, len(interior))
    interior_pieces = [pos for pos in initial_edges if pos[:2] not in corners and pos[:2] not in edges]
    for i in range(min(len(interior_pieces), len(interior_positions))):
        piece = initial_edges[interior_pieces[i]]
        target_position = interior_positions[i]
        rotation = random.choice([0, 1, 2, 3])  # Interiors can be rotated randomly
        final_position = (target_position[0], target_position[1], rotation)
        final_edges[final_position] = rotate(piece, rotation)
        mapping_[interior_pieces[i]] = final_position  # Track the mapping
    
    return mapping_, final_edges

def rotate(jig, rotation=1):
    """
    Rotate a  piece "rotation" times 90 degrees.
    """
    for rotations in range(rotation):
        jig = [jig[3]] + jig[:3]

    return jig

# Testing function for the mapping
def test_mapping():
    n = 9
    m = 9
    # Generate a simple placeholder initial puzzle configuration with pieces represented by unique integers for testing
    puzzle = generate_jigsaw_puzzle(n, m, initialized_connections=16*n)
    initial_edges = {}
    for y in range(n):
        for x in range(n):
            initial_edges[(y, x, 0)] = [int(puzzle[y][x][0]), int(puzzle[y][x][1]), int(puzzle[y][x][2]), int(puzzle[y][x][3])]
    # Print the final mapped puzzle configuration in matrix form
    mat = [[None for _ in range(m)] for _ in range(n)]
    for (y, x, o), piece in initial_edges.items():
        mat[y][x] = piece
    for row in mat:
        print(row)
    # Map the puzzle
    mapped_puzzle, mapping_ = mapping(n, m, initial_edges)
    print("-----------------------------------------------------")
    print(mapped_puzzle)
    print("-----------------------------------------------------")
    # Print the final mapped puzzle configuration in matrix form
    mat1 = [[None for _ in range(m)] for _ in range(n)]
    for (y, x, o), piece in mapping_.items():
        mat1[y][x] = piece
    for row in mat1:
        print(row)

    return True

if __name__ == "__main__":
    test_mapping()
