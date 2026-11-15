# Current-source wheel and browser smoke test

**Date:** November 13, 2026
**Result:** PASS for the tested wheel and case workflow
**Scope:** local package build, installation, server startup, and Firefox interaction

## Procedure

The current ECHO package source and pyproject configuration were copied to a
temporary directory outside the repository. A wheel was built with the locally
installed Python 3.14 build tools using no dependency resolution, package
index, or network access. The wheel was installed to a temporary target
directory and launched from a working directory outside the repository using
the project's existing virtual-environment runtime dependencies and an
explicit local data root.

The temporary wheel SHA-256 was
4648ffa6302c7ca4357ee7d6b9020822fcef4d57b121d02c0343d4427eb8b751.
Its packaged static assets matched the current source tree byte for byte.
The installed package served the local case registry successfully (HTTP 200,
six registered cases).

Firefox then completed the T024 investigation challenge workflow against this
wheel: the H2 challenge displayed the retained temporal comparisons, and the
408-day first-acquisition baseline opened on the map. The challenge preserved
the temporal-series checksum, acquisition identifiers, and diagnostic QA
status. There were no browser page errors; the only API call during the
challenge was a local read-only GET.

## Scientific and packaging limits

The tested observations are Sentinel-1-derived NASA OPERA RTC-S1 with no
consolidated provider PASS/FAIL verdict. This verifies package/runtime
consistency and one user workflow, not a validated event assessment or
scientific accuracy.

The wheel was temporary and was deleted after the test. It is not a portable
desktop build and does not bundle case evidence or large scientific datasets.
The desktop launcher remains tied to the repository checkout and its virtual
environment, as described in the [Linux launcher instructions](../../packaging/linux/README.md).
