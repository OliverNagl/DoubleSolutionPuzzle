import matplotlib.pyplot as plt
import numpy as np

# Sample input array (simplified for testing)
puzzle = np.load("Solutions/Solution_5_9_0_1.npy")

# Constants
piece_size = 1  # The size of each piece in the drawing

# Create a plot
fig, ax = plt.subplots(figsize=(10, 10))

# Set axis off
ax.set_axis_off()

# Iterate through each row and piece
for i, row in enumerate(puzzle):
    for j, piece in enumerate(row):
        # Parse the piece
        top, right, bottom, left, y_label, x_label = piece
        y = int(y_label.split(":")[1])
        x = int(x_label.split(":")[1])
        
        # Calculate the coordinates for the piece
        rect_x = i * piece_size
        rect_y = j * piece_size
        
        # Draw a rectangle for the piece
        rect = plt.Rectangle((rect_x, rect_y), piece_size, piece_size, fill=None, edgecolor='black', linewidth=2)
        ax.add_patch(rect)
        
        # Add text for the connections and piece ID
        ax.text(rect_x + piece_size / 2, rect_y + piece_size + 0.05, str(top), ha='center', fontsize=10)    # Top
        ax.text(rect_x + piece_size + 0.1, rect_y + piece_size / 2, str(right), va='center', fontsize=10)  # Right
        ax.text(rect_x + piece_size / 2, rect_y - 0.05, str(bottom), ha='center', fontsize=10)              # Bottom
        ax.text(rect_x - 0.1, rect_y + piece_size / 2, str(left), va='center', fontsize=10)                # Left
        
        # Add piece ID in the middle
        ax.text(rect_x + piece_size / 2, rect_y + piece_size / 2, f"({y}, {x})", ha='center', va='center', fontsize=10)

# Set the limits of the plot
ax.set_xlim(0, len(puzzle) * piece_size)
ax.set_ylim(0, len(puzzle) * piece_size)
print(puzzle)
# Reverse the y-axis to match grid orientation (0,0 at bottom-left)
plt.gca()

# Show the plot
plt.show()
