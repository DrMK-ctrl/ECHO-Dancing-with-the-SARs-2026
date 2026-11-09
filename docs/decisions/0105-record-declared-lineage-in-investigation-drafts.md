# Decision 0105: Record declared source lineage in investigation drafts

**Date:** 2026-11-09  
**Status:** Implemented and locally validated

## Context

Investigation drafts allowed up to twelve additional sources, but the staging path required every source to have empty derivation and shared-observation links. That made it impossible to preserve a known dependency between two staged records, even though the retained case investigation can display such links. A missing link must not imply independence, but a known link should not be discarded.

## Decision

When staging a source, an analyst may declare that it was derived from or shares source observations with evidence records already in the draft. References must use existing ECHO evidence IDs. The draft validator rejects unknown references, duplicate links, conflicting relationship types for the same ID, and cycles in derivation links. The declaration is copied into source-staging history and exposed beside the source with links to inspect the referenced records.

Each staged artifact retains `independence_state: NOT_ASSESSED`. The UI labels lineage as analyst-declared and unverified. A declaration does not verify provider records, determine independence, count evidence, change a hypothesis relationship, or change its disposition. Existing drafts without explicit lineage continue to validate with empty links.

## Consequences

- A known derivation or shared-acquisition dependency can be preserved in a new draft and inspected without treating dependent records as independent corroboration.
- Lineage only references records already staged; the workflow does not silently accept unresolved external identifiers.
- Lineage is a human declaration. ECHO does not infer source overlap from provider names, product IDs, or the content of arbitrary records.
- Case-source import restrictions and all SAR QA gates remain unchanged.

## Validation

See [investigation draft lineage validation](../validation/investigation-draft-lineage-2026-11-09.md).
