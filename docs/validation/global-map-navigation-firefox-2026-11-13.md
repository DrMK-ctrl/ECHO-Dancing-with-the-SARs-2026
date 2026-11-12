# Global map navigation: Firefox verification

**Date:** 2026-11-13  
**Application:** local ECHO workbench at `127.0.0.1:8766`  
**Browser:** Firefox headless through W3C WebDriver

## Interaction sequence

Starting from the default investigation view, Firefox exercised **World View**,
zoom-in, keyboard panning on the focused map region, and pointer drag panning.
The geographic grid labels changed after each navigation action. The world
view showed the full longitude and latitude extent; after zoom-in the grid
labels narrowed, and ArrowRight then shifted them east. A subsequent drag
shifted the displayed extent again. The page had no horizontal overflow at
1366 × 900.

The keyboard check focused the map's focusable SVG region and sent a real
WebDriver ArrowRight key. The initial attempt sent the key before explicitly
focusing the region and did not move the map; after focusing the map, the key
worked. This documents the tested focus requirement rather than claiming that
keyboard-only discovery or screen-reader behavior has been evaluated.

This pass verifies global extent, zoom, keyboard pan after map focus, and drag
pan in the browser. It does not validate map-tile availability or scientific
measurement alignment; those have separate checks.
