import random as rand
import numpy as np


def gen_rdm_mat(n,m):
    puzzle = np.zeros((n, n, 4))
    for y in range(0, n):
        for x in range(0, n):

            for i in range(0,4):
                puzzle[y][x][i] = rand.randrange(1,m+1)

           #edges and conditions
            if x != 0 and y != 0:
                puzzle[y][x][0] = puzzle[y][x-1][2]
                puzzle[y][x][1] = puzzle[y-1][x][3]

            if x == 0:
                puzzle[y][x][0] = 0
                if y != 0:
                    puzzle[y][x][1] = puzzle[y-1][x][3]
                  
            elif x == n-1:
                puzzle[y][x][2] = 0
                if y == 0:
                    puzzle[y][x][0] = puzzle[y][x-1][2]
                else:
                    puzzle[y][x][0] = puzzle[y][x-1][2]
                    puzzle[y][x][1] = puzzle[y-1][x][3]

            if y == 0:
                puzzle[y][x][1] = 0
                if x != 0:
                    puzzle[y][x][0] = puzzle[y][x-1][2]
                
            elif y == n-1:
                puzzle[y][x][3] = 0

                if x == 0:
                    puzzle[y][x][1] = puzzle[y-1][x][3]
                else:
                    puzzle[y][x][0] = puzzle[y][x-1][2]
                    puzzle[y][x][1] = puzzle[y-1][x][3]
            
    return puzzle

#print(gen_rdm_mat(3,3))



