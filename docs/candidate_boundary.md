# Candidate Boundary and Attribution

The AGI candidate is the frozen cognitive artifact named by a candidate manifest. The recursive project-management solver is development infrastructure only and is never part of the candidate, its runtime, or its scored evaluation context.

## Allowed dependencies

A declared candidate may use ordinary non-cognitive facilities when they are visible to the evaluator and fully logged: deterministic libraries, compilers/interpreters, operating-system actions, search/retrieval, databases, sensors, and task APIs. These facilities may return information or execute explicit operations but may not supply an undisclosed general-purpose reasoning service.

## Prohibited attribution shortcuts

A scored candidate fails integrity if it delegates cognitive work to the project solver, a human operator, an undeclared external general model, or an endpoint whose role cannot be audited. A remote model can only be considered part of the candidate if it is explicitly frozen, versioned, included in the candidate boundary, made available to independent evaluators under the same terms, and its use is attributable to the submitted artifact; otherwise it is prohibited cognitive delegation.

## Freeze

Before task reveal, the evaluator records cryptographic hashes of the candidate artifact and runtime, the complete list of cognitive components, the complete tool list, network endpoints, resource limits, and evaluator harness. Any change to a cognitive component, prompt, executable, routing rule, memory initialization, or safety/control policy after task reveal creates a new candidate and burns the current sealed task set for that candidate lineage.

`src/jagi_eval/manifest.py` provides a minimum machine-checkable validator for this boundary. Passing the validator is necessary but not sufficient; the evaluator must also audit actual runtime traffic and process provenance.
