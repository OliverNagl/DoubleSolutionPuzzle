import svgwrite
import os
import numpy as np

class JigsawPiece:
    def __init__(self, connections, size=200, folder="Conn_types"):
        self.connections = connections
        self.size = size
        self.folder = folder
        self.drawing = svgwrite.Drawing(size=(size, size))
        self.tab_size = size // 4

    def add_connection(self, conn_type, x, y, rotation=0):
        filename = os.path.join(self.folder, f"type_{abs(conn_type)}.svg")
        if not os.path.isfile(filename):
            print(f"Error: {filename} not found.")
            return
        image = self.drawing.image(href=filename, insert=(x, y), size=(self.size, self.size))
        if rotation:
            image.rotate(rotation, center=(x + self.size / 2, y + self.size / 2))
        self.drawing.add(image)

    def assemble_piece(self):
        size = self.size
        half_size = size / 1.7
        placements = [(0, -half_size), (half_size, 0), (0, half_size), (-half_size, 0)]
        rotations = [-90, 0, 90, 180]
        for i, conn_type in enumerate(self.connections):
            x, y = placements[i]
            rotation = rotations[i]
            if conn_type != 0:
                self.add_connection(conn_type, x, y, rotation)

    def draw(self):
        self.assemble_piece()
        return self.drawing

class Puzzle:
    def __init__(self, grid, mapping, background_image, size=200, folder="Conn_types"):
        self.grid = grid
        self.mapping = mapping
        self.n = grid.shape[0]
        self.size = size
        self.folder = folder
        self.background_image = background_image
        self.drawing = svgwrite.Drawing(size=(self.n * self.size, self.n * self.size))

    def create_clipped_piece(self, row, col, connections):
        piece = JigsawPiece(connections, size=self.size, folder=self.folder)
        piece_drawing = piece.draw()
        piece_group = self.drawing.g()

        # Add clipping path for the piece
        clip_id = f"clip_{row}_{col}"
        clip_path = self.drawing.defs.add(self.drawing.clipPath(id=clip_id))
        clip_rect = self.drawing.rect(insert=(col * self.size, row * self.size), size=(self.size, self.size))
        clip_path.add(clip_rect)

        # Position the background inside the clipping path
        background = self.drawing.image(
            href=self.background_image,
            insert=(0, 0),
            size=(self.n * self.size, self.n * self.size)
        )
        background.clip_path = f"url(#{clip_id})"
        
        # Apply the mapping transformation
        if (row, col, 0) in self.mapping:
            mapped_row, mapped_col, rotation = self.mapping[(row, col, 0)]
            x_pos = mapped_col * self.size
            y_pos = mapped_row * self.size
            piece_group.translate(x_pos, y_pos)
            piece_group.rotate(rotation, center=(x_pos + self.size / 2, y_pos + self.size / 2))
        else:
            x_pos = col * self.size
            y_pos = row * self.size
            piece_group.translate(x_pos, y_pos)

        # Add the background and piece drawing to the clipped group
        piece_group.add(background)
        piece_group.add(piece_drawing)
        self.drawing.add(piece_group)

    def assemble_puzzle(self):
        for row in range(self.n):
            for col in range(self.n):
                connections = self.grid[row, col]
                self.create_clipped_piece(row, col, connections)

    def draw(self, filename="full_puzzle.svg"):
        self.assemble_puzzle()
        self.drawing.saveas(filename)
        print(f"Saved assembled puzzle as {filename}")

# Example usage
n = 3
grid = np.array([[[0, 1, -2, 3], [1, 0, -3, 2], [-2, 3, 0, 1]],
                 [[3, 2, -1, 0], [0, 1, -2, 3], [1, 0, 3, -2]],
                 [[2, -1, 3, 0], [-3, 2, 1, 0], [0, 1, -2, 3]]])

# Mapping dictionary (row, col, orientation) -> (new_row, new_col, new_orientation)
mapping = {
    (0, 0, 0): (1, 1, 90),
    (0, 1, 0): (1, 2, 180),
    # Add further mappings as needed
}

# Create puzzle with a global background image
background_image = "Puzzle_Solutions_after_diffusion/UV map.png"
puzzle = Puzzle(grid, mapping, background_image, size=200, folder="Conn_types")
puzzle.draw("mapped_puzzle.svg")
