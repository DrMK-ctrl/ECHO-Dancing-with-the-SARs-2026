# OPERA temporal grid-offset stress-test validation — 2026-11-12

## Method

ECHO validates the retained T024 series against its exact linked T024 pair before calculating eight integer shifts of the later image: `dr,dc ∈ {-1,0,1}` except `(0,0)`. No interpolation, resampling, or wraparound occurs. For each offset it intersects finite before, nominal-after, and shifted-after samples, computes the shifted change and an unshifted control on that same support, and reports descriptive statistics. The input source record remains unchanged.

This scenario uses one native cell (30 m along either axis; diagonal shifts are about 42.4 m). NASA/JPL's [OPERA RTC-S1 product specification](https://asf.alaska.edu/wp-content/uploads/2023/11/OPERA-RTC-S1-STATIC-ProductSpec-v1.0.2-D-108764-Initial-2023-11-06-URS321268.pdf) describes RTC-S1 and static layers on the same burst grid and 30 m spacing. ASF's [RTC-S1 product guide](https://hyp3-docs.asf.alaska.edu/guides/opera_rtc_product_guide/) also describes 30 m sampling. Neither source defines this one-cell scenario as a geolocation-error model; it is ECHO's deliberate stress test.

## Retained T024 results

The source series has 1,034 valid centers in its all-date support. Each of the eight shifts has 966–1,001 matched centers due to window edges and retained valid support.

Source SHA-256:

- T024 series: `191cac49a1718c3b5c0fd85d2c7ee814c37c484e8ba7462e92aa9cd2c1bae738`
- Linked T024 pair: `4556bd0d781de4f8e99c240682e761caa10fb540d09edcec029848b6d9c758ea`

| Comparison | Nominal median | Offset medians | Median sign matching nominal | Matched support |
|---|---:|---:|---:|---:|
| 24-day adjacent step | −1.408 dB | −1.878 to −1.661 dB | 8/8 | 966–1,001 |
| 384-day adjacent step | +0.177 dB | +0.046 to +0.227 dB | 8/8 | 966–1,001 |
| 408-day first-acquisition baseline | −1.252 dB | −1.694 to −1.486 dB | 8/8 | 966–1,001 |

The per-offset unshifted control is shown beside the shifted median in the interface so support composition is not mistaken for a value-only effect. The 384-day interval's positive median coexists with roughly balanced positive and negative cell counts; median sign agreement alone does not imply spatially uniform response or robust physical interpretation.

## Verification and limits

- The calculation reproduces from the checksummed series and exact linked pair; it emits strict JSON with no NaN values and does not mutate the source record.
- Automated suite: `.venv/bin/python -m pytest -q` — **481 passed**. Focused OPERA-series, adversarial-challenge, renderer, and web API tests passed **92 tests**.
- Headless Firefox opened the local T024 case, opened the retained investigation, selected **Challenge This Finding**, expanded **Comparability and Sensitivity**, and inspected all **24** offset rows. It showed the reproduced 0.046–0.227 dB range for the 384-day step and retained the unresolved provider-QA statement. After constraining nested grid tracks, the expanded challenge panel measured 830 px scroll width against 830 px client width; the offset disclosure measured 744/744 px, with the comparison table contained in its own horizontal scroller.
- Tests verify all three comparisons, eight offsets, matched-support ranges, median values, QA-status preservation, unavailable behavior when no series is linked, challenge API integration, and rendered disclosures.
- T024 remains Sentinel-1-derived OPERA diagnostic evidence with no consolidated provider PASS/FAIL disposition. The test cannot resolve that QA gap or explain the physical cause.
- The offsets are selected scenarios, not measured registration errors or calibrated uncertainty bounds. Pixel counts are spatially dependent and are not significance tests. No generalized positional-uncertainty model is implemented.
