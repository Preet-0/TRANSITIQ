# Pip redesign notes

## Product identity

Pip — The Little Star Detective is the user-facing identity. The tagline is “Tiny dips. Hidden worlds.” The original vector mascot and inline hero illustration are in `assets/pip.svg` and `assets/pip-hero.svg`. The hero transit scene respects reduced-motion preferences. Browser title, navigation, export names, generated report headings, README and deployment name use Pip.

## Preserved science

The redesign keeps the current Streamlit interaction model and reuses the existing Python astronomy modules. MAST search/download, CSV/FITS validation, provenance tracking, transit-aware detrending, Astropy BLS, optional independent TLS, photometric vetting, injection/recovery, candidate review and reports continue to use real input data and existing code paths. The homepage Kepler-10 chart uses the cached real Q17 observations. It is explicitly labelled as archival data; a new analysis remains a photometric reanalysis, not independent confirmation.

## Architecture decision

This release does not migrate to React/Vite/FastAPI. The current application is a working single-process Streamlit product with analysis state bound to a user session. Replacing it would require new API contracts for MAST acquisition, uploads, session-held arrays, long-running BLS/TLS work, experiment grids and report exports, plus a new deployment topology. Implementing that migration alongside a visual rebrand would risk changing the tested scientific behavior and the user workflow. The delivered version is the brief’s safe fallback: a cohesive responsive redesign over the existing science, with a separate Model Performance route and clear navigation for science, discovery and experiments.

A future frontend migration can be staged behind versioned FastAPI endpoints while retaining Streamlit and the current Render service for rollback. The UI currently has no genuine live ML probability; the catalogue model remains a separate benchmark.

## Responsive verification

`scripts/visual_check.py` runs the local Streamlit site in Chromium, opens the real Kepler-10 analysis, checks Plotly chart rendering and reports horizontal overflow at 320, 360, 390, 430, 768, 1024, 1280 and 1440 pixels. Screenshots and the measured report are in `docs/screenshots/`.
