# OIS foundations

Delta-function kernel optimal image subtraction (Alard & Lupton 1998; Miller 2008; Oelkers+2015).

Given reference `R` and science `S`, find kernel `K` such that `S ≈ R * K` (convolution).
Residual: `D = S - R * K`.

Kernel size: `(2w+1)²` where `w = kernel` parameter. Stamp size: `(2·stamp+1)²`.
Polynomial degree `order` allows space-varying kernels.

Linear system: build `C` (Q×Q) and `D` (Q) from star stamps, solve via LU decomposition
(matching reference C implementation including indexing conventions).

Output: `Diff[i] = Sci[i] - Con[i]`.
