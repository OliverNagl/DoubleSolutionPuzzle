from jig_SAT_V2 import *

def mmain(same_neighbours_k):
    # Record start time and initial resource usage
    start_time = time.time()
    process = psutil.Process()
    start_memory = process.memory_info().rss

    solutions = []
    while len(solutions) < 2:
        n = 5
        # Execute the main function
        solutions = jig_main(n = n,
        threshold = 0,
        Same_pieces_k = 0,
        same_neighbours_k = same_neighbours_k,
        disable_rotations = n**2-4*n+4)

        # Record end time and final resource usage
        end_time = time.time()
        end_memory = process.memory_info().rss

        # Calculate elapsed time and memory usage
        elapsed_time = end_time - start_time
        memory_usage = end_memory - start_memory

        # Print performance metrics
        print(f"Elapsed time: {elapsed_time:.2f} seconds")
        print(f"Memory usage: {memory_usage / (1024 * 1024):.2f} MB")

        if elapsed_time > 60*100:
            break

    return elapsed_time, solutions

def find_optimum():
    for i in range(10):
        elapsed_time, solutions = mmain(-1)
        print(f"Same neighbours k: {i}")
        print(f"Elapsed time: {elapsed_time:.2f} seconds")
        print(f"Solutions: {solutions}")

if __name__ == "__main__":
    find_optimum()