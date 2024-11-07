def mapping(n, m, initial_edges):
    # Create a second configuration of a jigsawpuzzle given a dictionary of initial edges wiht x, y, and orientation
    # n: int, number of rows
    # m: int, number of columns
    # initial_edges: dict, dictionary of initial edges with x, y, and orientation
    # return: dict, dictionary of final edges with x, y, and orientation

    # Create a dictionary of final edges
    final_edges = {}
    for (y, x, o), piece in initial_edges.items():
        if y==0 and x==0:
            final_edges[(n-1,n-1,o+2)] = piece
        