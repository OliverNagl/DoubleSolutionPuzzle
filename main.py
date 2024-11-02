from jig_SAT_V2 import *

if __name__ == "__main__":
    # Record start time and initial resource usage
    start_time = time.time()
    process = psutil.Process()
    start_memory = process.memory_info().rss

    solutions = []
    while len(solutions) < 2:
        n = 3
        # Execute the main function
        solutions = jig_main(n = n,
        threshold = 0,
        Same_pieces_k = 0,
        same_neighbours_k = n**3*4,
        disable_rotations = int(n**2-n))

        # Record end time and final resource usage
        end_time = time.time()
        end_memory = process.memory_info().rss

        # Calculate elapsed time and memory usage
        elapsed_time = end_time - start_time
        memory_usage = end_memory - start_memory

        # Print performance metrics
        print(f"Elapsed time: {elapsed_time:.2f} seconds")
        print(f"Memory usage: {memory_usage / (1024 * 1024):.2f} MB")