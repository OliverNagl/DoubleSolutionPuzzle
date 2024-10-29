import numpy

def checker(side_length, placed_pieces, pieces_remaining, Sol):
    dead_end = True
    if len(pieces_remaining) == 0:
        Sol.append(placed_pieces)
    
    current_spot = len(placed_pieces)
    xpos = current_spot % side_length
    ypos = int(current_spot/side_length)

    requirements = ["-","-","-","-"]

    if xpos == 0:
        requirements[0] = 0
    if xpos == side_length - 1:
        requirements[2] = 0
    if ypos == 0:
        requirements[1] = 0
    if ypos == side_length -1:
        requirements[3] = 0


    #check pieces left or above
    if requirements[0] == "-":
        requirements[0] = placed_pieces[current_spot-1][2]

    if requirements[1] == "-":
        requirements[1] = placed_pieces[current_spot-side_length][3]

    #see which pieces are possible
    test_edge = requirements[0]
    for i in pieces_remaining:
        candidate_potential = True
        for k in requirements:
            if k != "-":
                if k not in i:
                    candidate_potential = False
        
        if candidate_potential:
            scan = 0
            while scan < len(requirements):
                rotations_needed = scan
                candidate = [j for j in i]
                #rotate to req. position
                while rotations_needed != 0:
                    candidate.append(candidate.pop(0))
                    rotations_needed -= 1
                works = True
                scan_B = 0
                while scan_B < len(requirements):
                    if requirements[scan_B] != "-":
                        if requirements[scan_B] != candidate[scan_B]:
                            works = False
                    scan_B += 1

                if works:
                    dead_end = False
                    new_placed_pieces = [m for m in placed_pieces]
                    new_placed_pieces.append(candidate)
                    new_pieces_remaining = [l for l in pieces_remaining]
                    new_pieces_remaining.remove(i)
                    checker(side_length, new_placed_pieces, new_pieces_remaining, Sol)

