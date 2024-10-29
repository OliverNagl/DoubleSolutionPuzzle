import numpy as np
from PIL import Image

# Load the input image (identity UV map)
image_path = "UV_ID.png"
image = Image.open(image_path)
width, height = image.size
image_data = np.array(image)

# Define the identity puzzle specification (2x3 grid for simplicity)
identity_puzzle = np.array([
    [[0, -7, -5, 0], [0, 1, 5, 7], [0, 5, -3, -1], [0, -5, -3, -5], [0, 7, 5, 5], [0, 0, 5, -7]],
    [[5, 1, 3, 0], [-5, -7, 1, -1], [3, -3, 3, 7], [3, 5, 7, 3], [-5, 3, -1, -5], [-5, 0, -5, -3]],
    [[-3, -5, -1, 0], [-1, 1, 1, 5], [-3, -7, 7, -1], [-7, 7, -3, 7], [1, 5, 7, -7], [5, 0, -7, -5]],
    [[1, 1, 1, 0], [-1, 1, -1, -1], [-7, 3, -7, -1], [3, -3, 1, -3], [-7, 1, 3, 3], [7, 0, -1, -1]],
    [[-1, 5, -7, 0], [1, -1, -5, -5], [7, 5, 5, 1], [-1, 1, 1, -5], [-3, 3, 1, -1], [1, 0, -5, -3]],
    [[7, 5, 0, 0], [5, -3, 0, -5], [-5, -5, 0, 3], [-1, -5, 0, 5], [-1, -5, 0, 5], [5, 0, 0, 5]]
])

# Define the second puzzle's rearranged specification
# This can be a rearrangement of the identity puzzle's pieces
second_puzzle = np.array([
    [[0, 5, 5, 0], [0, 5, -1, -5], [0, 5, -1, -5], [0, 3, -5, -5], [0, -5, 5, -3], [0, 0, 7, 5]],
    [[-5, -3, 1, 0], [1, -1, -3, 3], [1, -5, -1, 1], [5, 1, 7, 5], [-5, -5, 1, -1], [-7, 0, -1, 5]],
    [[-1, -1, 7, 0], [3, 3, -7, 1], [1, -3, 3, -3], [-7, -1, -7, 3], [-1, -1, -1, 1], [1, 0, 1, 1]],
    [[-7, -5, 5, 0], [7, -7, 1, 5], [-3, 7, -7, 7], [7, -1, -3, -7], [1, 5, -1, 1], [-1, 0, -3, -5]],
    [[-5, -3, -5, 0], [-1, -5, -5, 3], [7, 3, 3, 5], [3, 7, 3, -3], [1, -1, -5, -7], [3, 0, 5, 1]],
    [[5, -7, 0, 0], [5, 5, 0, 7], [-3, -5, 0, -5], [-3, -1, 0, 5], [5, 7, 0, 1], [-5, 0, 0, -7]]
])

# Number of rows and columns of puzzle pieces
rows, cols = identity_puzzle.shape[0], identity_puzzle.shape[1]

# Define the size of each puzzle piece
piece_width = width // cols
piece_height = height // rows

def get_uv_coordinates(piece_x, piece_y, piece_width, piece_height):
    """Get the UV coordinates (pixel positions) of a puzzle piece given its location in the grid."""
    x_start = piece_x * piece_width
    y_start = piece_y * piece_height
    x_end = x_start + piece_width
    y_end = y_start + piece_height
    return (x_start, y_start, x_end, y_end)

def generate_transformed_uv_map(identity_puzzle, second_puzzle, image_data):
    # Create an empty array for the UV map of the second solution
    transformed_uv_map = np.zeros_like(image_data)
    
    # Iterate over each piece in the identity puzzle
    for y in range(rows):
        for x in range(cols):
            # Get the UV coordinates for the current piece in the identity puzzle
            uv_coords_identity = get_uv_coordinates(x, y, piece_width, piece_height)
            x_start_id, y_start_id, x_end_id, y_end_id = uv_coords_identity

            # Iterate over the second puzzle to find where this piece is located
            found = False
            for y_new in range(rows):
                for x_new in range(cols):
                    # Compare the connections to find the matching piece
                    if np.array_equal(identity_puzzle[y, x], second_puzzle[y_new, x_new]):
                        # We found the new position (x_new, y_new) of the current piece
                        found = True
                        break
                if found:
                    break
            
            # Get the UV coordinates for the new position in the second puzzle
            uv_coords_new = get_uv_coordinates(x_new, y_new, piece_width, piece_height)
            x_start_new, y_start_new, x_end_new, y_end_new = uv_coords_new
            
            # Copy the pixel data from the identity UV map to the transformed UV map
            transformed_uv_map[y_start_new:y_end_new, x_start_new:x_end_new, :] = \
                image_data[y_start_id:y_end_id, x_start_id:x_end_id, :]
    
    return transformed_uv_map

# Generate the UV map based on the transformation
transformed_uv_map = generate_transformed_uv_map(identity_puzzle, second_puzzle, image_data)

# Save the transformed UV mapped image
new_image = Image.fromarray(transformed_uv_map)
new_image.save("uv_mapped_puzzle_transformed.png")
