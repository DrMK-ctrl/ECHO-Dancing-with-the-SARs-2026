# T163 VV/VH polarization sensitivity validation

**Result:** Bounded authentic VH data were retrieved and compared with the existing VV record over shared spatial support. This is a diagnostic sensitivity analysis; it does not clear product QA or resolve the water hypothesis.

## Data and method

ASF catalog metadata lists both VV and VH GeoTIFF assets for both Sentinel-1A OPERA RTC-S1 T163-349925-IW2 scenes. The existing bounded RTC-S1 reader retrieved the two VH assets and product metadata for the same WGS84 AOI used by VV. Both pair records contain 1,199 valid measurements and remain `DIAGNOSTIC_PRODUCT_MASKED_COMPARISON`; the source metadata have no consolidated QA PASS/FAIL.

The same native-grid geometry overlay was run independently for VV and VH against the retained NASA OPERA DSWx-HLS WTR context. The sensitivity evaluator requires identical scene IDs, optical granules, optical raster hashes, grid CRS, cell indices, per-cell optical coverage and water-fraction change. It uses only cells valid in both polarization records with at least 75% common-valid optical area. No resampling or inferential test is used.

## Results

There are 738 shared cells. Median optical water-fraction change is zero. VV has mean/median log-ratio −2.047/−1.215 dB and descriptive Pearson correlation −0.108 with water-fraction change. VH has mean/median −1.716/−1.144 dB and correlation −0.078. The paired VV/VH log-ratio correlation is 0.644. VH minus VV has mean 0.330 dB, median 0.161 dB, and median absolute deviation 1.655 dB.

These weak, similar optical associations do not distinguish the water hypothesis. The moderate cellwise polarization relationship is descriptive only. VV and VH are from the same acquisitions and processor, so their relationship is not independent corroboration. DSWx-HLS is optical product context rather than field truth. Neighboring cells are spatially dependent, and the RTC-S1 pair has not been promoted beyond diagnostic status.

## Verification

- The bounded VH acquisition completed through the existing reader: 1,199 valid AOI pixels; provider QA remains `PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION`.
- `.venv/bin/python -m pytest -q tests/test_rtc_polarization_sensitivity.py tests/test_rtc_dswx_spatial_support.py`: **9 passed**.
- `.venv/bin/python tools/research/evaluate_rtc_polarization_sensitivity.py --vv ... --vh ... --output ...` reproduced the retained comparison artifact.
- The tests reject changed source scenes, altered optical support, and an unexpected provider QA disposition.

## Artifacts and SHA-256

- VH pair record: `f5c7ff9884ea375907c709fb7e695a86de054d1ea982f33e03f4d98f9d5e140a`
- VV spatial record: `a6c0ed14c1b09d04fdd41e6798f3fa2c5d7886ee3bd755300de2b75776f35062`
- VH spatial record: `e2d1b27748d1a41706518ccc0ea3438c4bf6b6772d65aa0d9e4c65bad6c34e4f`
- Polarization sensitivity record: `0da2e7bdcf62fa59b38d6dc0655db2c8732a70054a968c84888964248995614f`
- Sensitivity evaluator: `b5bd15f85b1d4b51528d80fcbbb3fffbf1e2903369436ab1ea14323eec2167e8`
- Spatial evaluator revision used for these overlays: `ec2751102a3b007327168ac691cedc2eccf2912d6f3c817b2fc1c6bebcd4bb3a`

See [Decision 0029](../decisions/0029-diagnostic-polarization-sensitivity.md) for the rationale and reproduction commands.
