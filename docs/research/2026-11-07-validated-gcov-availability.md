# NISAR VALIDATED GCOV availability check

**Checked:** 2026-11-07  
**Purpose:** Determine whether the newly announced NISAR VALIDATED release can replace the current QA-held GCOV candidates.

## Findings

NASA/ASF's NISAR known-issues guide says VALIDATED products were released in November 2026 and are fully calibrated and validated. However, the ASF CMR collection directory currently lists `NISAR_L2_GCOV_V1` as having no granules. The same directory lists granules for the PROVISIONAL GCOV collection and for other validated product collections, but none for validated GCOV.

The live ASF Search check used the repository's pinned `asf_search==14.1.0` client and `processingLevel=GCOV`:

| Query | Results | Interpretation |
|---|---:|---|
| `dataMaturity=VALIDATED`, Nepal point, 2026-08-01 through 2026-09-30 | 0 | No validated GCOV candidate returned for the Rasuwa case area and event period. |
| `dataMaturity=VALIDATED`, Mozambique point, 2026-01-01 through 2026-11-07 | 0 | No validated GCOV candidate returned for the pilot area. |
| `dataMaturity=VALIDATED`, no spatial constraint, 2026-11-01 through 2026-11-07 | 0 | No validated GCOV granule returned by the pinned ASF client in this date window. |
| No maturity filter, Nepal point, 2026-08-01 through 2026-09-30 | 3 returned in the bounded query | Results included PROVISIONAL production scenes and an `NISAR_UR_L2` product. |

ASF documents `UR` as **Urgent Response**, a time-sensitive processing configuration. It is distinct from the normal production stream and is not evidence that a product belongs to a VALIDATED collection. ECHO must preserve that distinction in catalog records and pair selection.

The ASF Search user guide currently documents `dataMaturity` values BETA and PROVISIONAL, while the newer NISAR known-issues page recognizes the November VALIDATED release. This documentation and archive state are not fully synchronized. The client accepted `VALIDATED` as a query value but returned no matching granules in the checks above.

## Consequence for ECHO

The VALIDATED release is not yet a usable replacement for either current case pair through the checked ASF GCOV catalog. Keep the existing BETA and PROVISIONAL labels and QA holds intact. Do not treat `NISAR_UR_L2` as a validated GCOV substitute. Recheck the dedicated validated GCOV collection when new granules appear; in the meantime, continue case selection and product review using the maturity and processing configuration actually returned by ASF.

This is a dated catalog-availability result, not a claim that no validated NISAR data exists in any product family or that the archive cannot change.

## Sources

- ASF, [NISAR known issues and VALIDATED collection status](https://nisar-docs.asf.alaska.edu/nisar-known-issues/).
- NASA CMR, [ASF EOSDIS collection directory](https://cmr.earthdata.nasa.gov/search/site/collections/directory/ASF/gov.nasa.eosdis).
- ASF, [ASF Search API keywords](https://docs.asf.alaska.edu/api/keywords/) (`productionConfiguration` definitions for production, urgent response, and custom).
- ASF, [NISAR ASF Search guide](https://nisar-docs.asf.alaska.edu/asf-search/) (`dataMaturity` usage and authenticated streaming guidance).
