# AGI-GI rev258: implicit relation-image original-root resource envelope

## Scope

This revision advances the resource-accounting child left open by rev257 without modifying rev257's active implementation files. It is intentionally independent of the unmerged rev257 module so both sessions can proceed in parallel.

## Contract

Before constructing an exact implicit image group, the envelope reserves one complete bounded attempt covering induced auxiliary-generator construction, implicit domain/image Schreier work, complete value-preserving auxiliary-coset intersection below an original-root polynomial image-order gate, paired original-domain preimage reconstruction, and final exact transport/containment verification.

All arithmetic saturates only at `max_work + 1` using Python arbitrary-precision integers. Because `image_order_upper_bound` is only an upper bound, rev258 does **not** divide the domain-order upper bound by it to estimate the kernel; doing so could under-reserve work. The conservative kernel reservation is the full domain-order upper bound.

Admission requires the domain degree to fit the original root, the auxiliary degree to fit the explicit quadratic lift gate, the image-order bound to fit `min(max_image_order, root ** image_order_poly_power)`, and the aggregate work bound to fit `max_work`.

## Strict boundary

`admitted=True` is a finite pre-execution resource statement only. `complete` remains false. This revision does not implement the exact implicit image/value-coset intersection, does not lift a concrete intersection back to the original domain, and does not claim GI or AGI.

## Parallel safety

The claim `chatgpt-session-j-rev258-resource-envelope-20260822T064500JST-2675f756` reserves only the four new rev258 files. rev255 / PR #195 and rev257 / PR #198 remain untouched.

## Validation

The focused suite contains 11 regressions covering admission, original-root and image-order gates, cap saturation, arbitrary-precision arithmetic, invalid order bounds, monotonicity in image bound and generator count, exact gate-boundary admission, and parameter validation.
