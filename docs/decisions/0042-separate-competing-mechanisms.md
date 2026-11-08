# Decision 0042: Separate competing investigation mechanisms

Date: 2026-11-08

## Context

The T163 assessment grouped soil-moisture, vegetation, and acquisition-condition effects under one hypothesis. That grouping conflicted with ECHO's predeclared-test contract: an evidence search should test one mechanism, while stating which alternatives remain outside its scope. It also caused NASA/USGS HLS vegetation associations to be attached to a hypothesis that purported to include soil moisture and acquisition conditions.

## Decision

Represent the mechanisms as separate hypotheses:

- H3: soil-moisture change
- H4: vegetation-state change
- H5: acquisition-conditions effect
- H6: SAR product-quality effect

Keep the optical-class and water explanations as H1 and H2. Link GPM and SMAP context only to H3; HLS NDVI associations only to H4; and use separate, explicit follow-up designs for H3, H4, and H5. Evidence may describe a relationship or limit interpretation without resolving its target hypothesis.

## Consequences

The user-facing assessment can show which explanation each observation can address, what remains untested, and which next search would test one branch. Existing measurements and source records are unchanged. T024 and T163 assessment records were regenerated to use the same schema and hypothesis set.

This is a reasoning-structure change, not a new scientific result. No causal conclusion, probability, or ranking is produced. The OPERA RTC-S1 pairs remain diagnostic, and their unresolved QA boundary remains in force.

## Validation

See [the mechanism-scope validation record](../validation/investigation-mechanism-scope-2026-11-08.md) for record validation and automated test results.
