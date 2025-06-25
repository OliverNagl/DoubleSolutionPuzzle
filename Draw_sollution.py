import svgwrite
import math
import numpy as np
import random
from svgpathtools import parse_path, Path


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
        s = max(abs(dx),abs(dy))  # Side length of the segment

        conn_type_factor = np.abs(conn_type)  # Connection type for the curve (positive)
        conn_type_factor = conn_type_factor/20

        # Define control points for the Bezier curve
        random.seed(conn_type_factor)

        # Generate control points for the Bezier curve
        one = random.uniform(0.2, 0.3)
        two = random.uniform(0.45, 0.55)
        three = random.uniform(0.13, 0.19)
        four = random.uniform(0.3, 0.4)
        five = random.uniform(0.7, 0.75)
        six = random.uniform(0.66, 0.8)
        seven = random.uniform(0.35, 0.45)
        eight = random.uniform(0.6, 0.7)

        # Adjust direction for vertical or horizontal lines
        if dy != 0:  # Vertical segment
            orientation = 1 if dy > 0 else -1
            
            if orientation > 0:
                inny_outy = 1 if conn_type < 0 else -1
            elif orientation < 0:
                inny_outy = 1 if conn_type > 0 else -1

            if orientation == 1:
                tab_path = [
                    f"L {cx} {cy + s * one * orientation}",
                    f"C {cx} {cy + s * two * orientation}, {cx + s * -three * inny_outy} {cy + s * seven * orientation}, {cx + s * -three* inny_outy} {cy + s * seven * orientation}",
                    f"C {cx + s * -four* inny_outy} {cy + s * four * orientation}, {cx + s * -four* inny_outy} {cy + s * two * orientation}, {cx + s * -four* inny_outy} {cy + s * two * orientation}",
                    f"C {cx + s * -four* inny_outy} {cy + s * five * orientation}, {cx + s * -three* inny_outy} {cy + s * eight * orientation}, {cx + s * -three* inny_outy} {cy + s * eight * orientation}",
                    f"C {cx} {cy + s * two * orientation}, {cx} {cy + s * six * orientation}, {cx} {cy + s * six * orientation}",
                    f"L {cx} {cy + s * orientation}"
                ]

                if inny_outy == 1:
                    midpoind = (cy + (cy + s))/2
                    tab_path_string = " ".join(tab_path)
                    path = parse_path(tab_path_string, current_pos= cx + cy*1j)
                    path = path.translated(0 - midpoind * 1j)
                    path = path.scaled(1, -1)
                    path = path.translated(0 + midpoind * 1j)
                    path = path.reversed()
                    path = path.d()
                    tab_path_string = path[path.find("L"): ]
                else:
                    midpoind = (cy + (cy + s))/2
                    tab_path_string = " ".join(tab_path)
                    path = parse_path(tab_path_string, current_pos= cx + cy*1j)
                    """path = path.translated(0 - midpoind * 1j)
                    path = path.scaled(1, -1)
                    path = path.translated(0 + midpoind * 1j)
                    path = path.reversed()"""
                    path = path.d()
                    tab_path_string = path[path.find("L"): ]

            else:
                o = orientation
                orientation = orientation * -1
                old_cy = cy
                cy = cy - s * orientation

                tab_path = [
                    f"L {cx} {cy + s * one * orientation}",
                    f"C {cx} {cy + s * two * orientation}, {cx + s * -three * inny_outy} {cy + s * seven * orientation}, {cx + s * -three* inny_outy} {cy + s * seven * orientation}",
                    f"C {cx + s * -four* inny_outy} {cy + s * four * orientation}, {cx + s * -four* inny_outy} {cy + s * two * orientation}, {cx + s * -four* inny_outy} {cy + s * two * orientation}",
                    f"C {cx + s * -four* inny_outy} {cy + s * five * orientation}, {cx + s * -three* inny_outy} {cy + s * eight * orientation}, {cx + s * -three* inny_outy} {cy + s * eight * orientation}",
                    f"C {cx} {cy + s * two * orientation}, {cx} {cy + s * six * orientation}, {cx} {cy + s * six * orientation}",
                    f"L {cx} {cy + s * orientation}"
                ]


                if inny_outy == -1:
                    midpoind = (cy + old_cy)/2
                    tab_path_string = " ".join(tab_path)
                    path = parse_path(tab_path_string, current_pos= cx + cy*1j)
                    """path = path.translated(0 - midpoind * 1j)
                    path = path.scaled(1, -1)
                    path = path.translated(0 + midpoind * 1j)"""
                    path = path.reversed()
                    path = path.d()
                    tab_path_string = path[path.find("L"): ]
                else:
                    midpoind = (cy + old_cy)/2
                    tab_path_string = " ".join(tab_path)
                    path = parse_path(tab_path_string, current_pos= cx + cy*1j)
                    path = path.translated(0 - midpoind * 1j)
                    path = path.scaled(1, -1)
                    path = path.translated(0 + midpoind * 1j)
                    #path = path.reversed()
                    path = path.d()
                    tab_path_string = path[path.find("L"): ]

        else:  # Horizontal segment
            orientation = 1 if dx > 0 else -1
            if orientation > 0:
                inny_outy = 1 if conn_type > 0 else -1
            elif orientation < 0:
                inny_outy = 1 if conn_type < 0 else -1
            
            if orientation == 1:
                tab_path = [
                    f"L {cx + s * one * orientation} {cy}",
                    f"C {cx + s * two * orientation} {cy}, {cx + s * seven * orientation} {cy - s * three*inny_outy}, {cx + s * seven * orientation} {cy - s * three*inny_outy}",
                    f"C {cx + s * four * orientation} {cy - s * four*inny_outy}, {cx + s * two * orientation} {cy - s * four*inny_outy}, {cx + s * two * orientation} {cy - s * four*inny_outy}",
                    f"C {cx + s * five * orientation} {cy - s * four*inny_outy}, {cx + s * eight * orientation} {cy - s * three*inny_outy}, {cx + s * eight * orientation} {cy - s * three*inny_outy}",
                    f"C {cx + s * two * orientation} {cy}, {cx + s * six * orientation} {cy}, {cx + s * six * orientation} {cy}",
                    f"L {cx + s * orientation} {cy}"
                ]

                if inny_outy == -1:
                    midpoind = (cx + (cx + s))/2
                    tab_path_string = " ".join(tab_path)
                    path = parse_path(tab_path_string, current_pos= cx + cy*1j)
                    path = path.translated(-midpoind + 0j)
                    path = path.scaled(-1, 1)
                    path = path.translated(+midpoind + 0j)
                    path = path.reversed()
                    path = path.d()
                    tab_path_string = path[path.find("L"): ]
                else:
                    midpoind = (cx + (cx + s))/2
                    tab_path_string = " ".join(tab_path)
                    path = parse_path(tab_path_string, current_pos= cx + cy*1j)
                    """path = path.translated(-midpoind + 0j)
                    path = path.scaled(-1, 1)
                    path = path.translated(+midpoind + 0j)
                    path = path.reversed()"""
                    path = path.d()
                    tab_path_string = path[path.find("L"): ]

            else:
                o = orientation
                orientation = orientation * -1
                old_cx = cx
                cx = cx - s * orientation
                tab_path = [
                    f"L {cx + s * one * orientation} {cy}",
                    f"C {cx + s * two * orientation} {cy}, {cx + s * seven * orientation} {cy - s * three*inny_outy}, {cx + s * seven * orientation} {cy - s * three*inny_outy}",
                    f"C {cx + s * four * orientation} {cy - s * four*inny_outy}, {cx + s * two * orientation} {cy - s * four*inny_outy}, {cx + s * two * orientation} {cy - s * four*inny_outy}",
                    f"C {cx + s * five * orientation} {cy - s * four*inny_outy}, {cx + s * eight * orientation} {cy - s * three*inny_outy}, {cx + s * eight * orientation} {cy - s * three*inny_outy}",
                    f"C {cx + s * two * orientation} {cy}, {cx + s * six * orientation} {cy}, {cx + s * six * orientation} {cy}",
                    f"L {cx + s * orientation} {cy}"               
                ]

                if inny_outy == 1:
                    midpoind = (cx + old_cx)/2
                    tab_path_string = " ".join(tab_path)
                    path = parse_path(tab_path_string, current_pos= cx + cy*1j)
                    """path = path.translated(-midpoind + 0j)
                    path = path.scaled(-1, 1)
                    path = path.translated(+midpoind + 0j)"""
                    path = path.reversed()
                    path = path.d()
                    tab_path_string = path[path.find("L"): ]
                else:
                    midpoind = (cx + old_cx)/2
                    tab_path_string = " ".join(tab_path)
                    path = parse_path(tab_path_string, current_pos= cx + cy*1j)
                    path = path.translated(-midpoind + 0j)
                    path = path.scaled(-1, 1)
                    path = path.translated(+midpoind + 0j)
                    #path = path.reversed()
                    path = path.d()
                    tab_path_string = path[path.find("L"): ]

        return tab_path_string

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
        
        path = self.drawing.path(d=path_d, fill="none", stroke="black", stroke_width=0.1)
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
sample_number = 14
size = 15
conn_types = 23
puzzle = np.load(f"Solutions/Solution_{size}_{conn_types}_0_{sample_number}.npy")

# Drop the last two entries of the (n,n,6) matrix making it (n,n,4) and convert all entries to integers$$
puzzle = puzzle[:,:,:4].astype(int)
#print(puzzle)
puzzle = JigsawPuzzle(puzzle)
puzzle.draw("jigsaw_puzzle.svg")
