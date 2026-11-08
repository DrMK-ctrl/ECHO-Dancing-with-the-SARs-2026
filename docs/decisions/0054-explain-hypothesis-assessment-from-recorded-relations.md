# Explain hypothesis assessments from recorded evidence relations

**Status:** Implemented in the product-independent investigation reasoning view

## Decision

Show a short per-hypothesis explanation derived from its validated state and evidence-relationship labels. For unresolved hypotheses, the view summarizes the non-directional relationship types and their count. For a within-scope directional state, it states the scope boundary and that the relationship summary is not causal confirmation or independent validation. With no assessed evidence, it explains that the hypothesis remains unevaluated.

The source-linked relationship list remains visible beside the summary. Evidence dependencies and shared observations continue to be presented separately.

## Rationale

The assessment previously showed the disposition and its linked relationships, but readers had to infer why a hypothesis remained unresolved. A transparent summary connects the declared evidence review to the displayed state and makes gaps and mixed interpretation visible without adding a score or a new scientific inference.

## Boundaries

- Relationship labels remain analyst-authored. The summary does not verify the scientific correctness of a label or the validity of a source.
- Link counts are descriptive interface aids, not counts of independent evidence, weights, confidence, or probabilities.
- Product QA, measurement suitability, and source dependencies retain their existing separate gates and records.
- The summary does not revise the assessment or produce a causal conclusion.
