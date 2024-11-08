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

    def generate_curve(self, x, y, dx, dy, conn_type):
        # Generates a curve path for a given connection type
        end_x, end_y = x + dx, y + dy
        mid_x, mid_y = x + dx / 2, y + dy / 2
        angle = math.atan2(dy, dx)
        
        control_points = {
        # Outward curves (positive knob shapes)
        1: (mid_x + self.tab_size * 0.5 * math.sin(angle), mid_y - self.tab_size * 1.2 * math.cos(angle)),
        3: (mid_x + self.tab_size * 0.8 * math.sin(angle), mid_y - self.tab_size * 1.0 * math.cos(angle)),
        5: (mid_x + self.tab_size * math.sin(angle), mid_y - self.tab_size * math.cos(angle)),
        7: (mid_x + 1.1 * self.tab_size * math.sin(angle), mid_y - 1.1 * self.tab_size * math.cos(angle)),
        9: (mid_x + self.tab_size * 0.7 * math.sin(angle), mid_y - self.tab_size * 1.5 * math.cos(angle)),
        11: (mid_x + 0.9 * self.tab_size * math.sin(angle), mid_y - self.tab_size * 0.9 * math.cos(angle)),
        13: (mid_x + 1.2 * self.tab_size * math.sin(angle), mid_y - 1.4 * self.tab_size * math.cos(angle)),
        15: (mid_x + 1.3 * self.tab_size * math.sin(angle), mid_y - 1.0 * self.tab_size * math.cos(angle)),

        # Inward curves (negative knob shapes)
        -1: (mid_x - self.tab_size * 0.5 * math.sin(angle), mid_y + self.tab_size * 1.2 * math.cos(angle)),
        -3: (mid_x - self.tab_size * 0.8 * math.sin(angle), mid_y + self.tab_size * 1.0 * math.cos(angle)),
        -5: (mid_x - self.tab_size * math.sin(angle), mid_y + self.tab_size * math.cos(angle)),
        -7: (mid_x - 1.1 * self.tab_size * math.sin(angle), mid_y + 1.1 * self.tab_size * math.cos(angle)),
        -9: (mid_x - self.tab_size * 0.7 * math.sin(angle), mid_y + self.tab_size * 1.5 * math.cos(angle)),
        -11: (mid_x - 0.9 * self.tab_size * math.sin(angle), mid_y + self.tab_size * 0.9 * math.cos(angle)),
        -13: (mid_x - 1.2 * self.tab_size * math.sin(angle), mid_y + 1.4 * self.tab_size * math.cos(angle)),
        -15: (mid_x - 1.3 * self.tab_size * math.sin(angle), mid_y + 1.0 * self.tab_size * math.cos(angle)),

        # 0: Flat edge, no curve
        0: (mid_x, mid_y)}


        
        ctrl_x, ctrl_y = control_points.get(conn_type, (mid_x, mid_y))
        return f"Q {ctrl_x} {ctrl_y} {end_x} {end_y}"

    def generate_knob(self, x, y, dx, dy, conn_type):
        """
        Generates an interlocking tab or cut shape for each connection type.
        :param x, y: Start point of the segment.
        :param dx, dy: Directional increments for the end point.
        :param conn_type: Connection type for the curve (-7 to 7, excluding 0).
        :return: SVG path segment as a string.
        """
        end_x, end_y = x + dx, y + dy
        mid_x, mid_y = x + dx / 2, y + dy / 2
        angle = math.atan2(dy, dx)

        # Define the circular tab size and control points for smooth interlocking shapes
        radius = self.tab_size / 2
        neck_length = radius
        tab_length = radius

        # Calculate offset for tab or cut
        if conn_type > 0:  # Outward tab
            neck_x = mid_x + neck_length * math.cos(angle + math.pi / 2)
            neck_y = mid_y + neck_length * math.sin(angle + math.pi / 2)
            outer_x = mid_x + tab_length * math.cos(angle + math.pi / 2)
            outer_y = mid_y + tab_length * math.sin(angle + math.pi / 2)
        else:  # Inward cut
            neck_x = mid_x - neck_length * math.cos(angle + math.pi / 2)
            neck_y = mid_y - neck_length * math.sin(angle + math.pi / 2)
            outer_x = mid_x - tab_length * math.cos(angle + math.pi / 2)
            outer_y = mid_y - tab_length * math.sin(angle + math.pi / 2)

        # Create smooth path for interlocking tabs or cuts
        path_segment = (
            f"L {neck_x} {neck_y} "
            f"A {radius} {radius} 0 0 1 {outer_x} {outer_y} "
            f"A {radius} {radius} 0 0 1 {neck_x} {neck_y} "
            f"L {end_x} {end_y}"
        )
        return path_segment

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
    def __init__(self, matrix, piece_size=26, tab_size=9):
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
sample_number = 10
size = 6
conn_types = 7
puzzle = np.load(f"Solutions/Solution_{size}_{conn_types}_0_{sample_number}.npy")

# Drop the last two entries of the (n,n,6) matrix making it (n,n,4) and convert all entries to integers$$
puzzle = puzzle[:,:,:4].astype(int)
print(puzzle)
puzzle = JigsawPuzzle(puzzle)
puzzle.draw("jigsaw_puzzle.svg")
