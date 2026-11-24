# Architecture

Pip’s Streamlit application owns user interaction and per-session analysis state. `transitiq.data` validates arrays. `preprocess` estimates a transit-aware median baseline. `detection` wraps Astropy BLS. `tls` independently verifies with limb-darkened Transit Least Squares. `vetting` derives photometric triage indicators. `mast` uses Lightkurve public MAST search/download. `experiments` performs synthetic injections through the same cleaning and BLS paths. `archive` obtains the NASA KOI table and prepares grouped ML inputs. `reports` serializes result metadata.

No persistent database is required. Render uses ephemeral storage; downloads and model artifacts created at runtime are not durable. Archive calls can be unavailable due to network/API incidents.
