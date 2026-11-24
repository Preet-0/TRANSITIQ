# Pip responsive screenshot gallery

Captured locally with Chromium through `scripts/visual_check.py` after running the Streamlit app. The viewport report records document and body widths for each required size, chart rendering, and browser errors.

| Page | Mobile · 390px | Tablet · 768px | Desktop · 1440px |
|---|---|---|---|
| Discover | [390px](discover-390.png) | [768px](discover-768.png) | [1440px](discover-1440.png) |
| Mobile navigation drawer | [Open at 390px](discover-nav-390.png) | — | — |
| Analyze a Star · Kepler-10 | [390px](analyze-390.png) | [768px](analyze-768.png) | [1440px](analyze-1440.png) |
| Signal Investigation · Kepler-10 | [390px](signal-390.png) | — | — |
| Candidate Explorer · Kepler-10 | [390px](candidate-390.png) | — | — |
| Real Kepler-10 showcase | [Raw · 390px](showcase-raw-390.png) | — | [Raw](showcase-raw-1440.png) · [Cleaned](showcase-cleaned-1440.png) · [Folded](showcase-folded-1440.png) |

Every principal route and the computed Kepler-10 showcase were measured at 320, 360, 390, 430, 768, 1024, 1280 and 1440px. `viewport_report.json` contains document/body width measurements; all checked routes reported zero horizontal overflow. The test also verified the SVG favicon, browser title, browser console, real BLS workflow, and four rendered Plotly charts on Signal Investigation. Kepler-10 charts and measurements use the included real Kepler Q17 data; the signal is shown as photometric evidence, not an independent confirmation.

Recreate the gallery from the project root:

```powershell
streamlit run app.py
python scripts/visual_check.py
```
