import svgwrite
import math
import numpy as np
from PIL import Image
import base64
from io import BytesIO
class JigsawPiece:
    def __init__(self, connections, size=26, tab_size=20):
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




    def create_path(self, x_offset, y_offset):
        size = self.size
        path_d = []
        
        x, y = x_offset, y_offset
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
    def __init__(self, matrix, piece_size=26, tab_size=15):
        self.matrix = matrix
        self.piece_size = piece_size
        self.tab_size = tab_size
        self.n = len(matrix)
        self.drawing = svgwrite.Drawing(size=(self.n * piece_size, self.n * piece_size))

    def create_piece(self, row, col, background_image_data, mapping=None,outline=True):
        # Get the mapped coordinates and rotation from the mapping
        if mapping:
            target_row, target_col, rotation = mapping.get((row, col, 0))
        else:
            target_row, target_col, rotation = row, col, 0
            print(f"Mapping ({row}, {col}) to ({target_row}, {target_col}) with rotation {rotation*90} degrees")  # Debugging statement

        connections = self.matrix[row][col]
        piece = JigsawPiece(connections, size=self.piece_size, tab_size=self.tab_size)
        
    
        x_offset_initial = col * self.piece_size
        y_offset_initial = row * self.piece_size
        path_d = piece.create_path(x_offset_initial,y_offset_initial)
        # Define a clipPath for the piece
        clip_path_id = f"clip_{row}_{col}"
        clip_path = self.drawing.defs.add(self.drawing.clipPath(id=clip_path_id))
        piece_path = self.drawing.path(d=path_d)
        clip_path.add(piece_path)
        
        # Create a background image with the clipped path
        clipped_image = self.drawing.image(
            href=background_image_data,
            insert=(-x_offset_initial, -y_offset_initial),
            size=(self.n * self.piece_size, self.n * self.piece_size),
            clip_path=f"url(#{clip_path_id})"
        )

        # Apply mapping to move the clipped image to its target location
        x_offset_target = target_col * self.piece_size
        y_offset_target = target_row * self.piece_size
        print(f"offset_target ({y_offset_target}, {x_offset_target}) with rotation {rotation*90} degrees")  # Debugging statement

        
        # Move and rotate the clipped image
        clipped_image.translate(x_offset_target, y_offset_target)
        if rotation != 0:
            cx, cy = x_offset_target, y_offset_target
            #,clipped_image.rotate(rotation*90)

        # Add the path and the clipped image to the drawing
        self.drawing.add(clipped_image)
        
        # Add the path outline for the piece (optional)
        if outline:
            piece_outline = self.drawing.path(d=path_d, fill="none", stroke="black", stroke_width=0.5)
            piece_outline.translate(x_offset_target, y_offset_target)
            if rotation != 0:
                pass
                #piece_outline.rotate(rotation*90, center=(cx, cy))
            self.drawing.add(piece_outline)
    

    def draw(self, filename="jigsaw_puzzle.svg", background=None, mapping=None, outline= True):
        # Resize the background to fit the puzzle size and convert it to Base64
        background_image = Image.open(background)
        resized_background = background_image.resize((self.n * self.piece_size, self.n * self.piece_size))
        image_data = BytesIO()
        resized_background.save(image_data, format="PNG")
        background_image_data = f"data:image/png;base64,{base64.b64encode(image_data.getvalue()).decode()}"
        
        # Draw each piece using the mapping dictionary
        for row in range(self.n):
            for col in range(self.n):
                self.create_piece(row, col, background_image_data, mapping=mapping or {},outline=outline)

        self.drawing.saveas(filename)
        print(f"Saved jigsaw puzzle as {filename}")


# Example usage
sample_number = 20
size = 10
conn_types = 17
puzzle_matrix = np.load(f"Solutions/Solution_{size}_{conn_types}_0_{sample_number}.npy")
puzzle_matrix = puzzle_matrix[:,:,:4].astype(int)

puzzle = JigsawPuzzle(puzzle_matrix)

# Define mapping dictionary, e.g., (0, 0, 0) -> (1, 2, 90) maps (0,0) to (1,2) with a 90° rotation
mapping = np.load(f"Solutions/Mapping_{size}_{conn_types}_{sample_number}.npy", allow_pickle=True).item()  # Define actual mappings as needed
print(mapping)
puzzle.draw(f"jigsaw_puzzle_mapped_{sample_number}.svg", background="Puzzle_Solutions_after_diffusion/UV map.png", mapping=mapping,outline=False)
