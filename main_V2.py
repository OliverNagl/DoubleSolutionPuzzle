from jig_SAT_V3 import *

def main(n=5, initialized_connections=0,m=4, balance=100,row_constraint = 100, verbose=True):
    
    solutions = []
    solutions = jig_main(n = n,
                         initialized_connections=initialized_connections, 
                         m=m,
                         verbose=verbose,
                         balance=balance,
                         row_constraint=row_constraint)
    return solutions
    

if __name__ == "__main__":
    start_time = time.time()
    process = psutil.Process()
    start_memory = process.memory_info().rss
    n = 5
    balance =  int(8*n**2)
    row_constraint = int(n)
    q = 2*n*2.71**(-1/2)
    m = int((2 + q)/2)
    for i in range(0,20):
        for j in range(4):
            main(n, initialized_connections = i, m=m, balance=balance,row_constraint = row_constraint, verbose=True)   
         # Print performance metrics
        # Calculate elapsed time and memory usage
        # Record end time and final resource usage
        end_time = time.time()
        end_memory = process.memory_info().rss
        elapsed_time = end_time - start_time
        memory_usage = end_memory - start_memory
        print("------------------------------------------------------")
        print(f"Elapsed time at {i}: {elapsed_time:.2f} seconds")
        print(f"Memory usage at {i}: {memory_usage / (1024 * 1024):.2f} MB")
        print("------------------------------------------------------")
        
            