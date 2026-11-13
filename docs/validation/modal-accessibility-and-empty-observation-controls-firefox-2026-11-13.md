# Dialog naming and empty-observation controls — Firefox, 2026-11-13

## Findings and changes

A browser accessibility inventory found eight of the eleven native dialogs had no programmatic name. Each now has an `aria-labelledby` reference to its visible heading; dialogs whose heading changes at runtime keep a stable heading ID. The observation-details panel also left **View Record** and **Fetch QA** enabled in cases with no selected acquisitions. Both controls now start disabled and are enabled only when an observation is selected.

## Browser verification

Firefox 158.0.1 checked the interactive workbench at 1366×900 and 500×800:

- All eleven dialogs had a nonempty accessible-name source; all `aria-labelledby` references resolved to headings.
- No horizontal page overflow was present at either viewport.
- **About**, **Find Observations**, **OPERA RTC-S1**, **NISAR S-SAR**, and the selected observation's **View Record** dialog opened and closed. Focus entered each dialog and returned to its invoking control.
- At 500×800, each exercised dialog remained within the browser viewport. The longer Bhoonidhi form used its dialog's internal scrolling rather than expanding beyond the viewport.
- In the T163 case, whose current catalog query has no acquisitions, **View Record** and **Fetch QA** were disabled. In the Iraq case, which has selected NISAR acquisitions, both were enabled and the source-record dialog opened.
- No catalog or provider request was submitted. `Fetch QA` was enabled-state checked only; its remote retrieval was not invoked.

This is a focused browser accessibility and empty-state check, not a complete screen-reader audit or a claim that every dialog and keyboard path has been validated.
