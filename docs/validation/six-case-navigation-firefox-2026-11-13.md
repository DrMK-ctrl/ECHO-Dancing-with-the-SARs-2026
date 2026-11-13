# Six-case navigation and investigation entry points — Firefox, 2026-11-13

**Application:** local interactive workbench at `127.0.0.1:8766`  
**Browser:** Firefox 158.0.1 with W3C WebDriver

Firefox selected each of the six cases from the application selector and waited for the selected case, its scene details, and map coordinate readout to update. All six loaded without a blank scene panel or invalid (`NaN`) coordinates:

| Case | Coordinate readout | Case assessment | Observation challenge |
|---|---|---:|---:|
| Rio Grande do Sul T163 diagnostic | 51.2350° W, 30.0350° S | Opened | Not offered for this record |
| Iraq NISAR GCOV diagnostic | 41.2100° E, 36.7100° N | Not offered | Opened |
| Istanbul flood | 28.9900° E, 41.1050° N | Not offered | Not offered |
| Mozambique | 33.5000° E, 24.5000° S | Not offered | Not offered |
| Rasuwa / Bhote Koshi | 85.5500° E, 28.3000° N | Not offered | Not offered |
| Rio Grande do Sul cross-sensor diagnostic | 51.2350° W, 30.0350° S | Opened | Not offered |

The two available case assessments rendered their evidence text. The Iraq observation challenge opened its source-linked review. No provider search, retrieval, draft mutation, or scientific conclusion was requested. Page-level JavaScript errors and unhandled rejections were monitored after each case loaded and during these interactions; none were observed.

This verifies case switching and the available assessment/challenge entry points in the local workbench. It does not validate every control within each case, provider availability, SAR quality, or scientific conclusions.
