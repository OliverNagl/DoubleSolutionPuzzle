import numpy as np
import random as rnd
from checker_v1 import checker
from generator_v1 import gen_rdm_mat

def simple_search(n, m):
    for i in range(0,1000):
        puzzle = gen_rdm_mat(n,m)
        puzzle_bag = puzzle.reshape(-1, puzzle.shape[-1]).tolist()
        
        #print(puzzle)
        #print(puzzle_bag)
        Sol = []

        checker(5,[puzzle_bag[0]], puzzle_bag[1:], Sol)

        if len(Sol) > 1:
            return Sol
        
    print("Fail")    
    return Sol

print(simple_search(2,3))
