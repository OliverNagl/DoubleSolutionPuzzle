import svgwrite
import os
import math
import numpy as np
class JigsawPiece:
    def __init__(self, connections, size=200, folder="Conn_types"):
        """
        Initialize a jigsaw piece using specified connection types.

        :param connections: List of four integers representing connection types for each side.
                            Positive values indicate "out" tabs, negative values indicate "in" cuts, 0 indicates a flat edge.
        :param size: The size of the jigsaw piece.
        :param folder: The folder containing the SVG connection types.
        """
        assert len(connections) == 4, "Connections should have exactly four sides"
        self.connections = connections
        self.size = size
        self.folder = folder
        self.drawing = svgwrite.Drawing(size=(size, size))

        # Normalize tab size as a fraction of the piece size
        self.tab_size = size // 4  # Standardize tab size for all pieces

    def add_connection(self, conn_type, x, y, rotation=0):
        """
        Adds a connection of specified type at the given location, rotated correctly.

        :param conn_type: The type of the connection (positive = "out", negative = "in").
        :param x, y: The position for this connection on the jigsaw piece.
        :param rotation: The rotation angle in degrees.
        """
        filename = os.path.join(self.folder, f"type_{abs(conn_type)}.svg")

        # Check if the file exists
        if not os.path.isfile(filename):
            print(f"Error: {filename} not found.")
            return

        # Insert SVG image reference at specified location with rotation
        image = self.drawing.image(href=filename, insert=(x, y), size=(self.size, self.size))

        # Rotate if necessary
        if rotation:
            image.rotate(rotation, center=(x + self.size / 2, y + self.size / 2))

        self.drawing.add(image)

    def assemble_piece(self):
        """
        Assembles the jigsaw piece by placing the appropriate connections on each side.
        """
        size = self.size
        half_size = size / 1.7

        # Define placements for each side (top, right, bottom, left)
        # These are the positions where the whole SVG connection will be placed, ensuring it fits properly on the piece.
        placements = [
            (0, -half_size),  # Top side
            (half_size, 0),  # Right side
            (0, half_size),  # Bottom side
            (-half_size, 0),  # Left side
        ]

        # Rotation logic for each side:
        rotations = [-90, 0, 90, 180]

        # Place each connection (top, right, bottom, left)
        for i, conn_type in enumerate(self.connections):
            x, y = placements[i]
            rotation = rotations[i]

            if conn_type != 0:
                self.add_connection(conn_type, x, y, rotation)

    def draw(self):
        """
        Returns the drawing object containing the assembled jigsaw piece without any positioning.
        This is meant to be used when adding the piece to the puzzle.
        """
        self.assemble_piece()
        return self.drawing

class Puzzle:
    def __init__(self, grid, size=200, folder="Conn_types"):
        """
        Initialize the puzzle with a grid of connection types.
        
        :param grid: A numpy array of shape (n, n, 4) representing the puzzle.
        :param size: The size of each puzzle piece.
        :param folder: The folder containing the connection SVG files.
        """
        self.grid = grid
        self.n = grid.shape[0]
        self.size = size
        self.folder = folder
        self.drawing = svgwrite.Drawing(size=(self.n * self.size, self.n * self.size))

    def place_piece(self, row, col, connections):
        """
        Places a single jigsaw piece at the correct location on the grid.

        :param row, col: The row and column indices for the piece in the puzzle grid.
        :param connections: The list of four connections for this piece.
        """
        # Create the jigsaw piece with the specified connections
        piece = JigsawPiece(connections, size=self.size, folder=self.folder)
        
        # Get the drawing object for the piece
        piece_drawing = piece.draw()

        # Create a group to hold this piece
        piece_group = self.drawing.g()

        # Calculate the position for this piece in the full puzzle grid
        x_pos = col * self.size
        y_pos = row * self.size

        # Apply the position offset by translating the entire piece group
        piece_group.translate(x_pos, y_pos)

        # Add the translated piece to the final puzzle drawing
        self.drawing.add(piece_drawing)

    def assemble_puzzle(self):
        """
        Assembles the entire puzzle from the grid.
        """
        for row in range(self.n):
            for col in range(self.n):
                connections = self.grid[row, col]
                self.place_piece(row, col, connections)

    def draw(self, filename="full_puzzle.svg"):
        """
        Draws the entire puzzle and saves it as an SVG file.
        """
        self.assemble_puzzle()
        self.drawing.saveas(filename)
        print(f"Saved assembled puzzle as {filename}")



# Example usage
n = 3  # Puzzle size 3x3
# Sample puzzle connections: (top, right, bottom, left) for each piece
grid = np.array([[[0, 1, -2, 3], [1, 0, -3, 2], [-2, 3, 0, 1]],
                 [[3, 2, -1, 0], [0, 1, -2, 3], [1, 0, 3, -2]],
                 [[2, -1, 3, 0], [-3, 2, 1, 0], [0, 1, -2, 3]]])

# Create puzzle from grid
puzzle = Puzzle(grid, size=200, folder="Conn_types")
puzzle.draw("full_puzzle.svg")

