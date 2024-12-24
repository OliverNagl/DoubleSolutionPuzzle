import svgwrite
import math
import numpy as np
class JigsawPiece:
    def __init__(self, connections, size=26, tab_size=20):
        # Initialize a jigsaw piece with connections, size, and tab size
        assert len(connections) == 4, "Connections should have exactly four sides"
        self.connections = connections
        self.size = size
        self.tab_size = tab_size
        self.drawing = svgwrite.Drawing(size=(size, size))

    def generate_knob(self, x, y, dx, dy, conn_type):
        """
        Generates an interlocking tab or cut shape for each connection type.
        :param x, y: Start point of the segment.
        :param dx, dy: Directional increments for the end point.
        :param conn_type: Connection type for the curve (-n for inward, n for outward).
        :return: SVG path segment as a string.
        """
        # Calculate basic parameters
        cx, cy = x, y  # Current starting point
        s = math.sqrt(dx**2 + dy**2)  # Side length of the segment

        conn_type_factor = np.abs(conn_type)  # Connection type for the curve (positive)
        conn_type_factor = conn_type_factor/20

        # Adjust direction for vertical or horizontal lines
        if dy != 0:  # Vertical segment
            orientation = 1 if dy > 0 else -1
            tab_path = [
                f"L {cx} {cy + s * 0.34 * orientation}",
                f"C {cx} {cy + s * 0.5 * orientation}, {cx + s * -0.15} {cy + s * 0.4 * orientation}, {cx + s * -0.15} {cy + s * 0.4 * orientation}",
                f"C {cx + s * -0.3} {cy + s * 0.3 * orientation}, {cx + s * -0.3} {cy + s * 0.5 * orientation}, {cx + s * -0.3} {cy + s * 0.5 * orientation}",
                f"C {cx + s * -0.3} {cy + s * 0.7 * orientation}, {cx + s * -0.15} {cy + s * 0.6 * orientation}, {cx + s * -0.15} {cy + s * 0.6 * orientation}",
                f"C {cx} {cy + s * 0.5 * orientation}, {cx} {cy + s * 0.65 * orientation}, {cx} {cy + s * 0.65 * orientation}",
                f"L {cx} {cy + s * orientation}"
            ]
        else:  # Horizontal segment
            orientation = 1 if dx > 0 else -1
            tab_path = [
                f"L {cx + s * 0.34 * orientation} {cy}",
                f"C {cx + s * 0.5 * orientation} {cy}, {cx + s * 0.4 * orientation} {cy - s * 0.15}, {cx + s * 0.4 * orientation} {cy - s * 0.15}",
                f"C {cx + s * 0.3 * orientation} {cy - s * 0.3}, {cx + s * 0.5 * orientation} {cy - s * 0.3}, {cx + s * 0.5 * orientation} {cy - s * 0.3}",
                f"C {cx + s * 0.7 * orientation} {cy - s * 0.3}, {cx + s * 0.6 * orientation} {cy - s * 0.15}, {cx + s * 0.6 * orientation} {cy - s * 0.15}",
                f"C {cx + s * 0.5 * orientation} {cy}, {cx + s * 0.65 * orientation} {cy}, {cx + s * 0.65 * orientation} {cy}",
                f"L {cx + s * orientation} {cy}"
            ]

        # Reverse path for inward tabs (negative connection types)
        if conn_type < 0:
            tab_path = [segment.replace('C', 'c').replace('L', 'l') for segment in reversed(tab_path)]

        return " ".join(tab_path)

    def create_path(self):
        # Generate SVG path for the jigsaw piece
        size = self.size
        path_d = []
        
        x, y = 0, 0
        path_d.append(f"M {x} {y}")

        directions = [
            (size, 0),   # Right
            (0, size),   # Down
            (-size, 0),  # Left
            (0, -size)   # Up
        ]

        for i, (dx, dy) in enumerate(directions):
            conn_type = self.connections[i]
            if conn_type == 0:
                x, y = x + dx, y + dy
                path_d.append(f"L {x} {y}")
            else:
                path_d.append(self.generate_knob(x, y, dx, dy, conn_type))
                x, y = x + dx, y + dy

        path_d.append("Z")
        return " ".join(path_d)

class JigsawPuzzle:
    def __init__(self, matrix, piece_size=43, tab_size=15):
        self.matrix = matrix
        self.piece_size = piece_size
        self.tab_size = tab_size
        self.n = len(matrix)
        self.drawing = svgwrite.Drawing(size=(self.n * piece_size, self.n * piece_size))

    def create_piece(self, row, col):
        # Create a jigsaw piece at (row, col) using connection types from the matrix
        connections = self.matrix[row][col]
        piece = JigsawPiece(connections, size=self.piece_size, tab_size=self.tab_size)
        path_d = piece.create_path()
        
        x_offset = col * self.piece_size
        y_offset = row * self.piece_size
        
        path = self.drawing.path(d=path_d, fill="none", stroke="black", stroke_width=0.5)
        path.translate(x_offset, y_offset)  # Position piece in grid
        self.drawing.add(path)

    def draw(self, filename="jigsaw_puzzle.svg"):
        # Draw all pieces in the puzzle
        for row in range(self.n):
            for col in range(self.n):
                self.create_piece(row, col)
        self.drawing.saveas(filename)
        print(f"Saved jigsaw puzzle as {filename}")

# Example usage
# Define a matrix of connection types for a 3x3 puzzle
# Each entry is a list of four integers representing connection types [right, down, left, up]
sample_number = 11
size = 8
conn_types = 13
puzzle = np.load(f"Solutions/Solution_{size}_{conn_types}_0_{sample_number}.npy")

# Drop the last two entries of the (n,n,6) matrix making it (n,n,4) and convert all entries to integers$$
puzzle = puzzle[:,:,:4].astype(int)
print(puzzle)
puzzle = JigsawPuzzle(puzzle)
puzzle.draw("jigsaw_puzzle.svg")
