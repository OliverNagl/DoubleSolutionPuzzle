import numpy as np
import random

def generate_piece(m):
    """Generate a single puzzle piece with 4 connection types (top, right, bottom, left)."""
    return [random.randint(0, m-1) for _ in range(4)]

def valid_connection(side1, side2):
    """Check if two sides of adjacent pieces can connect (they must be equal)."""
    return side1 == side2

def create_jigsaw(n, m):
    """Create a n x n jigsaw puzzle grid with random pieces using m connection types."""
    # Initialize an empty n x n grid
    puzzle = np.empty((n, n), dtype=object)

    for i in range(n):
        for j in range(n):
            piece = generate_piece(m)
            
            # Ensure top piece matches the bottom of the piece above
            if i > 0:
                piece[0] = puzzle[i-1, j][2]
            
            # Ensure left piece matches the right of the piece to the left
            if j > 0:
                piece[3] = puzzle[i, j-1][1]
            
            puzzle[i, j] = piece

    return puzzle

def is_valid_solution(puzzle, n):
    """Check if the entire puzzle is valid, i.e., all adjacent connections match."""
    for i in range(n):
        for j in range(n):
            piece = puzzle[i, j]
            
            # Check top connection
            if i > 0 and not valid_connection(puzzle[i-1, j][2], piece[0]):
                return False
            
            # Check left connection
            if j > 0 and not valid_connection(puzzle[i, j-1][1], piece[3]):
                return False
    
    return True

def create_second_solution(puzzle, n):
    """Create a second valid solution by modifying the first one slightly."""
    # Example: Swap two pieces and rotate them
    puzzle_copy = np.copy(puzzle)
    
    # Swap first and last piece
    puzzle_copy[0, 0], puzzle_copy[n-1, n-1] = puzzle_copy[n-1, n-1], puzzle_copy[0, 0]
    
    # Rotate both pieces by 180 degrees
    def rotate_piece(piece):
        return [piece[2], piece[3], piece[0], piece[1]]  # Swap top/bottom and left/right

    puzzle_copy[0, 0] = rotate_piece(puzzle_copy[0, 0])
    puzzle_copy[n-1, n-1] = rotate_piece(puzzle_copy[n-1, n-1])

    return puzzle_copy

def main(n, m):
    """Main function to generate a jigsaw puzzle with two distinct solutions."""
    # Step 1: Generate the initial solution
    puzzle = create_jigsaw(n, m)

    print("Original Puzzle:")
    for row in puzzle:
        print(row)

    # Step 2: Create a second solution by modifying the first one
    second_solution = create_second_solution(puzzle, n)

    print("\nSecond Puzzle Solution:")
    for row in second_solution:
        print(row)

    # Step 3: Verify both solutions are valid
    assert is_valid_solution(puzzle, n), "First puzzle solution is not valid!"
    assert is_valid_solution(second_solution, n), "Second puzzle solution is not valid!"
    
    print("\nBoth solutions are valid!")

# Example usage
n = 3  # Size of the puzzle
m = 4  # Number of distinct connection types
main(n, m)
