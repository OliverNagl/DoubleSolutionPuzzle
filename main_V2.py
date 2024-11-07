from jig_SAT_V3 import *

def main():
    start_time = time.time()
    process = psutil.Process()
    start_memory = process.memory_info().rss

    solutions = []
    solutions = jig_main(n = 5,initialized_connections=0,verbose=True)

    # Record end time and final resource usage
    end_time = time.time()
    end_memory = process.memory_info().rss

    # Calculate elapsed time and memory usage
    elapsed_time = end_time - start_time
    memory_usage = end_memory - start_memory

    # Print performance metrics
    print(f"Elapsed time: {elapsed_time:.2f} seconds")
    print(f"Memory usage: {memory_usage / (1024 * 1024):.2f} MB")
    
if __name__ == "__main__":
    main()