import matplotlib.pyplot as plt
import numpy as np

def calculate_color_gradient(rows, cols, alpha = 1):
    gradient = np.zeros((rows, cols, 4))
    for i in range(rows):
        for j in range(cols):
            gradient[i, j] = [i / rows, j / cols, (i + j) / (rows + cols), alpha]
    return gradient


def create_color_mapping(puzzle, color_gradient):
    color_mapping = {}
    for i, row in enumerate(puzzle):
        for j, piece in enumerate(row):
            y_label, x_label = piece[4], piece[5]
            y = int(y_label.split(":")[1])
            x = int(x_label.split(":")[1])
            color_mapping[(y, x)] = color_gradient[i, j]
    return color_mapping

def plot_puzzle(ax, puzzle, color_mapping):
    piece_size = 1  # The size of each piece in the drawing

    ax.set_axis_off()
    n = puzzle.shape[0] -1
    
    for i, row in enumerate(puzzle):
        for j, piece in enumerate(row):
            top, right, bottom, left, y_label, x_label = piece
            y = int(y_label.split(":")[1])
            x = int(x_label.split(":")[1])
            
            rect_y = i * piece_size
            rect_x = j * piece_size
            
            color = color_mapping[(y, x)]
            rect = plt.Rectangle((rect_x, n-rect_y), piece_size, piece_size, facecolor=color, edgecolor='black', linewidth=2)
            ax.add_patch(rect)
            
            ax.text(rect_x + 0.5, n-rect_y + 0.8, str(top), ha='center', fontsize=10)    # Top
            ax.text(rect_x + 0.8, n-rect_y + 0.5, str(right), va='center', fontsize=10)  # Right
            ax.text(rect_x + 0.5, n-rect_y + 0.1, str(bottom), ha='center', fontsize=10) # Bottom
            ax.text(rect_x + 0.1, n-rect_y + 0.5, str(left), va='center', fontsize=10)   # Left
            
            ax.text(rect_x + piece_size / 2, n- rect_y + piece_size / 2, f"({y}, {x})", ha='center', va='center', fontsize=10)

    ax.set_xlim(0, len(puzzle) * piece_size)
    ax.set_ylim(0, len(puzzle) * piece_size)
    print(puzzle)



# Sample input array (simplified for testing)
sample_number = 1283
size = 3
conn_types = 5
puzzle = np.load(f"Solutions/Solution_{size}_{conn_types}_0_{sample_number}.npy")
puzzle_sol2 = np.load(f"Solutions/Solution_{size}_{conn_types}_1_{sample_number}.npy")

rows, cols = puzzle.shape[0], puzzle.shape[1]
color_gradient = calculate_color_gradient(rows, cols, alpha=0.5)

# Create color mapping from the first puzzle
color_mapping = create_color_mapping(puzzle, color_gradient)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(5, 5))

plot_puzzle(ax1, puzzle, color_mapping)
plot_puzzle(ax2, puzzle_sol2, color_mapping)

plt.show()