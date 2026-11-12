# Local geographic context for the ECHO map

## Source and purpose

The local fallback coastlines come from Natural Earth 1:110m Physical Vectors,
Natural Earth version 4.1.0, `ne_110m_coastline`. Natural Earth describes the
110m coastline as a generalized global geographic layer. The source is public
domain; ECHO retains attribution for clarity.

- Project page: <https://www.naturalearthdata.com/downloads/110m-physical-vectors/>
- Terms: <https://www.naturalearthdata.com/about/terms-of-use/>
- Source archive: <https://naciscdn.org/naturalearth/110m/physical/ne_110m_coastline.zip>
- Retained archive SHA-256: `664449b39070027e882abb295974d182afec18ca21107273d17e9e8bf6f64817`
- Derived GeoJSON SHA-256: `666276f959174a1355a406ea5415ede184e92775c65dd4e8279623489bc01776`

The conversion is reproducible with `python tools/research/build_natural_earth_coastline.py`.
It reads the retained archive, validates the polyline records and WGS84 coordinate
bounds, and emits the compact GeoJSON served locally by ECHO. Tiny floating-point
coordinate overshoots at ±180°/±90° are clamped to those bounds by the converter.

## Scientific and display limits

This is coarse geographic orientation only. It is not satellite imagery, SAR
browse data, a measurement, a land-cover product, or evidence in an investigation.
When NASA GIBS imagery is available, the selected NASA layer remains the backdrop.
If that service fails or the backdrop is turned off, ECHO can show these retained
coastlines with an explicit Natural Earth attribution. SAR rasters and observation
footprints remain separate map layers.

The global view uses a simple WGS84 longitude/latitude layout to keep geographic
coordinates and area search bounds inspectable. It is not equal-area; shapes and
distances are distorted, increasingly toward high latitudes. Catalog requests
continue to use explicit WGS84 west, south, east, north bounds. A rectangle that
crosses the antimeridian or spans more than 180° longitude is rejected in the UI;
users must submit two non-wrapping searches. No observation coverage is implied
by global map coverage.
