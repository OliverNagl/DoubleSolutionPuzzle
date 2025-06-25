## Douple solution Jigsaw Puzzles
Many types of Jigsaw puzzles have multiple solutions trivially, where one could place any piece at any place, just
without actually making a picture. Then there is the kind of jigsaw puzzle where the only solution that is possible is the 
arrangment showing the correct picture. With the recent success of diffusion based image generation Ryan Burgert (& co.) 
where able to produce illusions in which a jigsaw puzzle, that can be solved physically in exactly 2 ways, also has two 
different non trivial image solutions. (https://diffusionillusions.com/) Their website hosts some examples using the double solution
created by Matt Parker for this purpose (https://www.youtube.com/watch?v=b5nElEbbnfU).

The creation of a set of Jigs that can be solved in exactly 2 (non-trivial) ways is not an easy problem. Therefore Matt Parker`s 
brute force solution of creating such sets of jigs is limited to jigsaws of about 6 x 6. 
In this little code project I did over my last winter holidays I tried to find a algorithm that would be able to go to larger 
grids of jigs. The code is super crap and full of bugs. But it works, I was able to extend the possible dimension that one can create
non trivial double solution jigsaw up to ca. 20x20. (on a Laptop running overnight).

