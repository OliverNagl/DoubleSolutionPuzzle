import svgwrite
import math
import numpy as np
from PIL import Image
import base64
from io import BytesIO
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

    def create_piece(self, row, col, background_image_data, mapping=None,outline=True):
        # Get the mapped coordinates and rotation from the mapping
        if mapping:
            target_row, target_col, rotation = mapping.get((row, col, 0))
        else:
            target_row, target_col, rotation = row, col, 0
            #print(f"Mapping ({row}, {col}) to ({target_row}, {target_col}) with rotation {rotation*90} degrees")  # Debugging statement

        connections = self.matrix[row][col]
        piece = JigsawPiece(connections, size=self.piece_size, tab_size=self.tab_size)
        
    
        # Generate the SVG path for the jigsaw piece
        path_d = piece.create_path()
        

        # Define a clipPath for the piece
        clip_path_id = f"clip_{row}_{col}"
        clip_path = self.drawing.defs.add(self.drawing.clipPath(id=clip_path_id))
        piece_path = self.drawing.path(d=path_d)
        
        # add the path to the clipPath
        clip_path.add(piece_path)
        
        # Create a background image with the clipped path
        x_offset_initial = col * self.piece_size
        y_offset_initial = row * self.piece_size
        clipped_image = self.drawing.image(
            href=background_image_data,
            insert=(-x_offset_initial, -y_offset_initial),
            size=(self.n * self.piece_size, self.n * self.piece_size),
            clip_path=f"url(#{clip_path_id})"
        )

        # Apply mapping to move the clipped image to its target location
        x_offset_target = target_col * self.piece_size
        y_offset_target = target_row * self.piece_size
        #print(f"offset_target ({y_offset_target}, {x_offset_target}) with rotation {rotation*90} degrees")  # Debugging statement

        # Move and rotate the clipped image
        clipped_image["transform"] = f"translate({x_offset_target}, {y_offset_target}) rotate({rotation*90}, {self.piece_size/2}, {self.piece_size/2})"
        """clipped_image.translate(x_offset_target, y_offset_target)
        clipped_image.rotate(rotation*90, center=(x_offset_target + self.piece_size/2, y_offset_target + self.piece_size/2))"""
        
        # Add the path and the clipped image to the drawing
        self.drawing.add(clipped_image)
        
        # Add the path outline for the piece (optional)
        if outline:
            piece_outline = self.drawing.path(d=path_d, fill="none", stroke="black", stroke_width=0.1)
            piece_outline["transform"] = f"translate({x_offset_target}, {y_offset_target}) rotate({rotation*90}, {self.piece_size/2}, {self.piece_size/2})"
               #piece_outline.rotate(rotation*90, center=(x_offset_target + self.piece_size/2, y_offset_target + self.piece_size/2))
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
sample_number = 14
size = 15
conn_types = 23
puzzle_matrix = np.load(f"Solutions/Solution_{size}_{conn_types}_0_{sample_number}.npy")
puzzle_matrix = puzzle_matrix[:,:,:4].astype(int)

puzzle = JigsawPuzzle(puzzle_matrix)

# Define mapping dictionary, e.g., (0, 0, 0) -> (1, 2, 90) maps (0,0) to (1,2) with a 90° rotation
mapping = np.load(f"Solutions/Mapping_{size}_{conn_types}_{sample_number}.npy", allow_pickle=True).item()  # Define actual mappings as needed
#print(mapping)
puzzle.draw(f"jigsaw_puzzle_mapped_{sample_number}.svg", background="Puzzle_Solutions_after_diffusion/UV Map.png", mapping=mapping,outline=False)
