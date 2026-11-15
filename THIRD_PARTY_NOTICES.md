# Third-party notices

The repository-wide Apache-2.0 license applies to original ECHO software and
documentation. It does not change the rights or terms for data, libraries, or
branding provided by others.

## Earth-observation sources

Retained case and research records identify their source providers, product
IDs, acquisition dates, source URLs, and available checksums. The included
records contain metadata and ECHO-produced diagnostic summaries; full SAR and
optical source products are not included.

- NASA/ASF DAAC: NISAR, OPERA RTC-S1, and related product QA and catalog records.
- NASA: DSWx-HLS, GPM IMERG, SMAP, HLS, and other products identified in the
  case records and research documentation.
- NASA GIBS: contextual basemap imagery requested by the browser at runtime;
  imagery is not bundled here. See the [GIBS usage guidance](https://nasa-gibs.github.io/gibs-api-docs/).
- Natural Earth: 1:110m coastline data, version 4.1.0, public domain. ECHO's
  retained source and conversion details are in
  [map geography data notes](docs/research/map-geography-data-2026-11-12.md).
- EESAR Systems: the provided wordmark is included for project identification.
  The Apache-2.0 grant does not grant trademark rights.

## Software dependencies

Dependency versions are declared in `pyproject.toml`, `requirements.lock`, and
`requirements-nisar.lock`. These packages are installed separately; they are
not vendored into this repository. Each dependency remains under its own
upstream license. Consult the package metadata and license files for the exact
versions in the lock files.

## Space Apps materials

NASA Space Apps 2026 participant terms require source attribution and license
documentation for submitted materials. See the
[official participant terms](https://www.spaceappschallenge.org/legal/) and
the source citations retained in the README and case records.
