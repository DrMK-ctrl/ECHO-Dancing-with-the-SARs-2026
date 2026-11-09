# Link acquisition chronology tracks to source records

## Decision

Move acquisition-date positioning and interval rendering into a shared chronology component that accepts normalized observation-pair rows. Each track includes its evidence-record identifier and exposes a direct source-inspector action.

## Rationale

The investigation timeline showed acquisition dates and intervals but did not let a reviewer inspect the records behind each track. A product-independent renderer keeps timestamp handling and presentation reusable while product-specific code remains responsible for extracting valid acquisition times and selecting the correct source record.

Invalid or reversed timestamps make the chronology unavailable. The shared renderer does not infer pixel alignment, sensor equivalence, event timing, or cause from temporal proximity.

## Scope

The T024 and T163 adapters remain case-data-specific and are checked against their current evidence inventories. This creates a reusable presentation contract; it does not generalize the scientific observation readers or create arbitrary-case processing.

See [validation](../validation/investigation-acquisition-chronology-source-links-2026-11-09.md).
