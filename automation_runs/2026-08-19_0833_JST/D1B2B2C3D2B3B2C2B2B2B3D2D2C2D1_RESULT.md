# rev79 result — deterministic fixed-skeleton continuous-attribute perturbation certificate

Status: **solved_v0_1 for this precisely scoped child**. Root remains **NOT_AGI**.

Let the per-node random-Fourier map be `phi(x)=sqrt(2/m) cos(Wx+b)`. Its Jacobian operator norm is globally bounded by `L_phi=sqrt(2/m)||W||_2`, hence `||phi(x)-phi(y)|| <= L_phi ||x-y||`.

At any structural refinement depth, WL color classes form a partition of the n vertices and the graph feature block is `n^(-1/2)` times the direct sum of the sums of `phi` inside each color class. Writing `d_i=phi(x_i)-phi(y_i)`, Cauchy-Schwarz gives, for each depth,

`n^(-1) sum_c ||sum_{i in c} d_i||^2 <= n^(-1) sum_c |c| sum_{i in c} ||d_i||^2 <= sum_i ||d_i||^2`.

Therefore each depth has displacement at most `L_phi ||X-Y||_F`. The H+1 depth blocks are a direct sum, yielding the deterministic distribution-free bound

`||F(A,X)-F(A,Y)|| <= sqrt(H+1) L_phi ||X-Y||_F`.

This proof does not rely on a training or validation distribution. Dedicated adversarial tests cover concentrated single-node perturbations, coherent translations of all nodes, very large perturbations, varied graph topologies/dimensions, and perturbation-scale linearity. Cumulative local regression rev75–79: **25 passed**.

The result applies only while the discrete skeleton A is fixed and the structural partition is computed from A alone. It does not settle bounded structural edits or population-level calibration.
