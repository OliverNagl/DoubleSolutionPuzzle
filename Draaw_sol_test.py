import svgwrite
import numpy as np
import math

class JigsawPiece:
    def __init__(self, connections, size=26, tab_size=20):
        self.connections = connections
        self.size = size
        self.tab_size = tab_size
        self.drawing = svgwrite.Drawing(size=(size, size))

    # [Your methods like generate_curve and generate_knob go here, unchanged]

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
    def __init__(self, matrix, piece_size=43, tab_size=15, background="background.jpg"):
        self.matrix = matrix
        self.piece_size = piece_size
        self.tab_size = tab_size
        self.n = len(matrix)
        self.drawing = svgwrite.Drawing(size=(self.n * piece_size, self.n * piece_size))
        self.background = background

    def create_piece(self, row, col):
        connections = self.matrix[row][col]
        piece = JigsawPiece(connections, size=self.piece_size, tab_size=self.tab_size)
        path_d = piece.create_path()

        # Define position in the puzzle grid
        x_offset = col * self.piece_size
        y_offset = row * self.piece_size

        # Create a clip path for the piece and adjust its position
        clip_id = f"clip_{row}_{col}"
        clip_path = self.drawing.defs.add(self.drawing.clipPath(id=clip_id))
        clip_path.add(self.drawing.path(d=path_d))

        # Add the background image to the drawing
        image = self.drawing.image(
            href=self.background,
            insert=(0, 0),
            size=(self.n * self.piece_size, self.n * self.piece_size),
            clip_path=f"url(#{clip_id})"
        )

        # Apply position translation to the image
        image.translate(x_offset, y_offset)
        self.drawing.add(image)

        # Draw piece outline for visibility (optional)
        outline = self.drawing.path(d=path_d, fill="none", stroke="black", stroke_width=0.5)
        outline.translate(x_offset, y_offset)
        self.drawing.add(outline)

    def draw(self, filename="jigsaw_puzzle.svg"):
        for row in range(self.n):
            for col in range(self.n):
                self.create_piece(row, col)
        self.drawing.saveas(filename)
        print(f"Saved jigsaw puzzle as {filename}")

# Usage example (load and modify puzzle data as needed)
sample_number = 10
size = 6
conn_types = 7
puzzle_data = np.load(f"Solutions/Solution_{size}_{conn_types}_0_{sample_number}.npy")[:,:,:4].astype(int)

# Create puzzle with a global background
puzzle = JigsawPuzzle(puzzle_data, background="background.jpg")
puzzle.draw("jigsaw_puzzle.svg")
