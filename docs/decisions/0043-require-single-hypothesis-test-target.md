# Decision 0043: Require a single hypothesis per test design

Date: 2026-11-08

## Context

The pre-search contract named one `hypothesis_under_test_id`, but allowed a follow-up to target multiple hypotheses. That left the test scope ambiguous: one expected observation and one weakening condition could be presented as testing several competing mechanisms.

## Decision

When a follow-up includes a discriminating test design, its `target_hypothesis_ids` must contain exactly the declared `hypothesis_under_test_id`. Follow-ups without a test design, including shared quality prerequisites, may still have multiple targets where their action genuinely applies to several hypotheses.

## Consequences

Open evidence searches have a mechanically enforced single-mechanism scope. The contract does not rank hypotheses, infer evidence relationships, or determine whether the chosen test is scientifically valid; those remain separate evaluation responsibilities.

## Validation

The automated contract test rejects a two-target follow-up carrying a one-hypothesis test design. Existing T024 and T163 open designs target one hypothesis and remain structurally valid. See [validation](../validation/single-hypothesis-test-target-2026-11-08.md).
