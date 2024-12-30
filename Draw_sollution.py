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
                transformed_path_str = " ".join(tab_path)
            else:
                tab_path = [
                    f"L {cx} {cy + s * one * orientation}",
                    f"C {cx} {cy + s * two * orientation}, {cx + s * -three * inny_outy} {cy + s * seven * orientation}, {cx + s * -three* inny_outy} {cy + s * seven * orientation}",
                    f"C {cx + s * -four* inny_outy} {cy + s * four * orientation}, {cx + s * -four* inny_outy} {cy + s * two * orientation}, {cx + s * -four* inny_outy} {cy + s * two * orientation}",
                    f"C {cx + s * -four* inny_outy} {cy + s * five * orientation}, {cx + s * -three* inny_outy} {cy + s * eight * orientation}, {cx + s * -three* inny_outy} {cy + s * eight * orientation}",
                    f"C {cx} {cy + s * two * orientation}, {cx} {cy + s * six * orientation}, {cx} {cy + s * six * orientation}",
                    f"L {cx} {cy + s * orientation}",
                ]

                # Convert the tab_path to a path string
                tab_path_str = " ".join(tab_path)

                # Parse the path into a Path object
                path = parse_path(tab_path_str, current_pos=cx + cy * 1j)

                mid_y = (cy + cy + s * orientation) / 2
                # Step 2: Translate the path to move its midpoint to the origin
                translated_path_1 = path.translated(0 - mid_y *1j)

                # Step 3: Apply the scaling to flip the path over the x-axis (now at the midpoint)
                scaled_path = translated_path_1.scaled(1, -1)

                # Step 4: Translate the path back to its original position
                translated_path_2 = scaled_path.translated(0 + mid_y *1j)

                # Convert the final transformed path to a string
                transformed_path_str = translated_path_2.d()
                #remove everything until the first L of the string
                #transformed_path_str = transformed_path_str[transformed_path_str.find('L'):]
                
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
                transformed_path_str = " ".join(tab_path)
            else:
                tab_path = [
                    f"L {cx + s * one * orientation} {cy}",
                    f"C {cx + s * two * orientation} {cy}, {cx + s * seven * orientation} {cy - s * three*inny_outy}, {cx + s * seven * orientation} {cy - s * three*inny_outy}",
                    f"C {cx + s * four * orientation} {cy - s * four*inny_outy}, {cx + s * two * orientation} {cy - s * four*inny_outy}, {cx + s * two * orientation} {cy - s * four*inny_outy}",
                    f"C {cx + s * five * orientation} {cy - s * four*inny_outy}, {cx + s * eight * orientation} {cy - s * three*inny_outy}, {cx + s * eight * orientation} {cy - s * three*inny_outy}",
                    f"C {cx + s * two * orientation} {cy}, {cx + s * six * orientation} {cy}, {cx + s * six * orientation} {cy}",
                    f"L {cx + s * orientation} {cy}"
                ]

                # Convert the tab_path to a path string
                tab_path_str = " ".join(tab_path)
    
                # Parse the path into a Path object
                path = parse_path(tab_path_str, current_pos=cx + cy * 1j)

                mid_x = (cx + cx + s * orientation) / 2
                # Step 2: Translate the path to move its midpoint to the origin
                translated_path_1 = path.translated(-mid_x + 0j)

                # Step 3: Apply the scaling to flip the path over the x-axis (now at the midpoint)
                scaled_path = translated_path_1.scaled(-1, 1)

                # Step 4: Translate the path back to its original position
                translated_path_2 = scaled_path.translated(mid_x + 0j)

                # Convert the final transformed path to a string
                transformed_path_str = translated_path_2.d()
                #remove everything until the first L of the string
                #transformed_path_str = transformed_path_str[transformed_path_str.find('L'):]

        return transformed_path_str

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
sample_number = 20
size = 10
conn_types = 17
puzzle = np.load(f"Solutions/Solution_{size}_{conn_types}_0_{sample_number}.npy")

# Drop the last two entries of the (n,n,6) matrix making it (n,n,4) and convert all entries to integers$$
puzzle = puzzle[:,:,:4].astype(int)
#print(puzzle)
puzzle = JigsawPuzzle(puzzle)
puzzle.draw("jigsaw_puzzle.svg")
