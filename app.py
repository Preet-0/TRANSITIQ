from __future__ import annotations
import json
import base64
import html
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from astropy.io import fits
from transitiq.data import LightCurve
from transitiq.preprocess import detrend
from transitiq.detection import search_bls
from transitiq.vetting import vet_candidate
from transitiq.experiments import run_injection, injection_grid
from transitiq.mast import search_observations, download_observation
from transitiq.reports import save_analysis, make_html_report, make_pdf_report
from transitiq.tls import verify_tls

st.set_page_config(
    page_title="Pip — The Little Star Detective",
    page_icon="assets/pip.svg",
    layout="wide",
    initial_sidebar_state="auto",
)
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
:root{--bg:#08111F;--panel:#0D1728;--surface:#142238;--line:#26364c;--text:#F4F0E8;--muted:#b0bdcd;--gold:#F1C96A;--cyan:#73CFE0}
.stApp{background:radial-gradient(ellipse at 82% -12%,#182b43 0%,transparent 38%),var(--bg);color:var(--text);font-family:Manrope,sans-serif}
header[data-testid="stHeader"]{background:rgba(8,17,31,.97)!important;background-color:rgba(8,17,31,.97)!important;border-bottom:1px solid rgba(38,54,76,.55)!important}
header[data-testid="stHeader"] [data-testid="stToolbar"]{background:transparent!important}
header[data-testid="stHeader"] button{color:var(--text)}header[data-testid="stHeader"] [data-testid="stAppDeployButton"]{display:none!important}
[data-testid="stRadio"] label:has(input:checked)>div:first-child>div{background:#F1C96A!important;border-color:#F1C96A!important}
[role="tab"][aria-selected="true"]{color:#F1C96A!important;border-bottom-color:#F1C96A!important}
a:focus-visible,button:focus-visible,[role="radio"]:focus-visible,[role="tab"]:focus-visible{outline:2px solid #F1C96A!important;outline-offset:3px!important}
[data-testid="stSidebar"]{background:#0a1422;border-right:1px solid var(--line)}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{color:#b0bdcd}
.block-container{padding:2.2rem clamp(1rem,4vw,3.5rem) 4rem;max-width:1500px}
h1,h2,h3{letter-spacing:-.035em;color:var(--text)} h1{font-weight:750;font-size:clamp(2rem,4vw,3.25rem)}
.metric-card{background:linear-gradient(145deg,#142238,#0d1728);border:1px solid var(--line);border-radius:16px;padding:18px 20px;min-height:98px}
.metric-label{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted)}
.metric-value{font-size:25px;font-weight:700;margin-top:5px;color:var(--text)}
.eyebrow{font:500 11px 'DM Mono',monospace;color:var(--gold);letter-spacing:.17em;text-transform:uppercase}
.small-note{color:var(--muted);font-size:14px;line-height:1.7}.stButton>button{border-radius:10px;border:1px solid #40536b;background:#17283d;color:var(--text);min-height:2.8rem;transition:transform .15s ease,border-color .15s ease}
.stButton>button:hover{border-color:var(--gold);color:var(--text);transform:translateY(-1px)}
.stButton>button[kind="primary"]{background:var(--gold);border-color:var(--gold);color:#172132;font-weight:700}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:12px;overflow:hidden}
.pip-hero{display:grid;grid-template-columns:1.12fr .88fr;gap:clamp(1rem,4vw,4rem);align-items:center;padding:clamp(1.2rem,4vw,3.5rem) 0 2.6rem}
.pip-hero-copy{max-width:700px}.pip-hero h1{font-size:clamp(2.6rem,5.6vw,5.15rem);line-height:1.03;letter-spacing:-.065em;margin:.7rem 0 1.1rem}
.pip-hero p{font-size:clamp(1rem,1.5vw,1.2rem);line-height:1.75;color:#c1ccda;max-width:650px}
.pip-art{width:100%;max-width:560px;justify-self:end;display:block}
.pip-panel{border:1px solid var(--line);border-radius:18px;background:linear-gradient(150deg,rgba(20,34,56,.93),rgba(13,23,40,.96));padding:clamp(1rem,3vw,2rem);height:100%}
.pip-step{color:var(--gold);font:500 12px 'DM Mono',monospace;letter-spacing:.12em}.pip-panel h3{font-size:1.1rem;margin:.7rem 0}.pip-panel p{font-size:.94rem;line-height:1.65;color:#b0bdcd}
.pip-rule{height:1px;background:var(--line);margin:2rem 0}.pip-footnote{font-size:.82rem;color:#aebdce;line-height:1.6}
@media(max-width:800px){.pip-hero{grid-template-columns:1fr;padding-top:1.2rem}.pip-art{max-width:430px;justify-self:center;grid-row:1}.pip-hero-copy{grid-row:2}.block-container{padding-top:2.6rem}.pip-panel{margin-bottom:.4rem}}
@media(max-width:480px){.pip-hero h1{font-size:2.6rem}.pip-art{max-width:320px}.block-container{padding-left:1rem;padding-right:1rem}.metric-card{padding:14px;min-height:82px}.metric-value{font-size:21px}}
@media(max-width:640px){[data-testid="stHorizontalBlock"]{flex-wrap:wrap;gap:.6rem}[data-testid="stHorizontalBlock"]>[data-testid="column"]{flex:1 1 calc(50% - .6rem)!important;min-width:calc(50% - .6rem)!important}.candidate-mobile{display:block!important}.candidate-desktop{display:none!important}}
@media(max-width:380px){[data-testid="stHorizontalBlock"]>[data-testid="column"]{flex-basis:100%!important;min-width:100%!important}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)
PIP_HERO = base64.b64encode(Path("assets/pip-hero.svg").read_bytes()).decode("ascii")
PAGES = [
    "Discover",
    "Overview",
    "Analyze Star",
    "Candidate Explorer",
    "Signal Investigation",
    "Planet Recovery Lab",
    "Model Performance",
    "Research & Methods",
]


def select_page(name):
    st.session_state.page_select = name


with st.sidebar:
    st.image("assets/pip.svg", width=72)
    st.markdown('<div class="eyebrow">PIP · THE LITTLE STAR DETECTIVE</div>', unsafe_allow_html=True)
    st.caption("Tiny dips. Hidden worlds.")
    page = st.radio("NAVIGATION", PAGES, label_visibility="collapsed", key="page_select")
    st.divider()
    st.caption("DATA SOURCES")
    st.markdown("NASA Exoplanet Archive · MAST · Kepler · TESS")
    st.caption("No external AI API required")

if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "curve" not in st.session_state:
    st.session_state.curve = None


def header(kicker, title, sub):
    st.markdown(
        f'<div class="eyebrow">{kicker}</div><h1>{title}</h1><p class="small-note">{sub}</p>',
        unsafe_allow_html=True,
    )


def metric(label, value):
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def chart(x, y, title, xlabel, ylabel, color="#5ce1e6", name="observations"):
    fig = go.Figure(
        go.Scattergl(
            x=x, y=y, mode="markers", marker={"size": 4, "color": color, "opacity": 0.72}, name=name
        )
    )
    fig.update_layout(
        title={"text": title, "font": {"color": "#F4F0E8", "size": 16}},
        xaxis_title=xlabel,
        yaxis_title=ylabel,
        height=390,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(8,14,26,.55)",
        font={"color": "#D2DCE7", "family": "Manrope"},
        margin={"l": 20, "r": 15, "t": 55, "b": 35},
        xaxis={"gridcolor": "#1d2a40"},
        yaxis={"gridcolor": "#1d2a40"},
    )
    return fig


def analyze(c, limits, window=1.5):
    raw = c.flux.copy()
    clean, baseline, params = detrend(c, window_days=window)
    det = search_bls(c.time, clean, min_period=limits[0], max_period=limits[1])
    vet = vet_candidate(c.time, clean, det)
    return {
        "target": (c.provenance or {}).get("target", "Uploaded target"),
        "provenance": c.provenance or {},
        "n_raw": len(raw),
        "n_clean": len(clean),
        "time": c.time.tolist(),
        "raw_flux": raw.tolist(),
        "cleaned_flux": clean.tolist(),
        "baseline": baseline.tolist(),
        "processing": params,
        "detection": det,
        "vetting": vet,
        "data_note": "Unconfirmed photometric candidate; no external confirmation implied.",
    }


if page == "Discover":
        st.markdown(f'''
        <section class="pip-hero">
          <div class="pip-hero-copy">
            <div class="eyebrow">MEET YOUR NEW COSMIC DETECTIVE</div>
            <h1>A tiny dip in starlight could reveal a whole new world.</h1>
            <p>Meet Pip, your little star detective. Pip explores real observations from distant stars, spots repeating dips in their light and helps uncover possible hidden planets.</p>
            <p><strong>Tiny dips. Hidden worlds.</strong></p>
          </div>
          <img class="pip-art" src="data:image/svg+xml;base64,{PIP_HERO}" alt="Pip observes a planet crossing a distant star; a light curve shows the small dip in brightness." />
        </section>
        ''', unsafe_allow_html=True)
        cta, meet = st.columns([1, 1])
        with cta:
            st.button("Explore the stars →", type="primary", use_container_width=True, on_click=select_page, args=("Analyze Star",))
        with meet:
            st.button("Meet Pip", use_container_width=True, on_click=select_page, args=("Research & Methods",))
        st.markdown('<div class="pip-rule"></div><div class="eyebrow">A SMALL SIGNAL, A BIG QUESTION</div><h2>Stars don’t need to disappear to reveal a secret.</h2><p class="small-note">Sometimes, they only need to become a little dimmer. When a planet passes in front of its star, telescopes can record a tiny, repeating change in brightness.</p>', unsafe_allow_html=True)
        st.markdown("### How the investigation works")
        steps = st.columns(3)
        for col, (number, title, copy) in zip(steps, [
            ("01 — WATCH THE STARS", "A record of starlight", "Telescope observations record how bright distant stars appear over time."),
            ("02 — SPOT THE TINY DIPS", "Look for a pattern", "A planet crossing its star makes the light slightly dimmer. Repeating dips can reveal an orbit."),
            ("03 — CHECK THE CLUES", "Test the signal", "Pip examines each signal and checks for clues that could point to a false alarm.")]):
            with col:
                st.markdown(f'<div class="pip-panel"><div class="pip-step">{number}</div><h3>{title}</h3><p>{copy}</p></div>', unsafe_allow_html=True)
        st.markdown('<div class="pip-rule"></div>', unsafe_allow_html=True)
        st.markdown("### A real observation, ready to explore")
        st.markdown('<p class="small-note">Start with real NASA Kepler Q17 observations of Kepler-10. The built-in example is actual telescope data; Pip’s photometric analysis is an investigation, not independent confirmation.</p>', unsafe_allow_html=True)
        preview = Path("data/demo/kepler10_q17_longcadence.csv")
        if preview.exists():
            demo = pd.read_csv(preview)
            st.plotly_chart(chart(demo["time"], demo["flux"], "Kepler-10 · Kepler Q17 · raw light curve", "Time (days)", "Normalized flux", color="#F1C96A"), use_container_width=True)
        st.caption("Real NASA Kepler data · KOI-72.01 has an archive confirmed disposition. A fresh run here remains a photometric reanalysis and is not an external confirmation.")
        if st.button("Run the real Kepler-10 example", type="secondary"):
            try:
                with st.spinner("Cleaning the archived observations and searching for repeating dips…"):
                    meta = json.loads(Path("data/demo/kepler10_q17_longcadence.json").read_text(encoding="utf-8"))
                    frame = pd.read_csv(preview)
                    demo_curve = LightCurve.from_frame(frame, "time", "flux", "flux_err", "quality", meta)
                    demo_analysis = analyze(demo_curve, (0.5, 15.0), 1.5)
                    demo_analysis["search_limits"] = {"min_period": 0.5, "max_period": 15.0}
                    st.session_state.curve = demo_curve
                    st.session_state.analysis = demo_analysis
                    st.session_state.kepler_demo_analysis = demo_analysis
            except Exception as exc:
                st.error(f"The Kepler-10 example could not be analyzed: {exc}")
        demo_result = st.session_state.get("kepler_demo_analysis")
        if demo_result:
            detection = demo_result["detection"]
            st.success("Analysis completed on real Kepler Q17 observations. This is a photometric reanalysis, not independent confirmation.")
            result_cols = st.columns(4)
            for column, (label, value) in zip(result_cols, [
                ("BLS period", f"{detection['period_days']:.6f} days"),
                ("Transit depth", f"{detection['depth_ppm']:.1f} ppm"),
                ("Duration", f"{detection['duration_hours']:.2f} hours"),
                ("Photometric triage", demo_result["vetting"]["label"]),
            ]):
                with column:
                    metric(label, value)
            raw_tab, clean_tab, fold_tab = st.tabs(["Raw light curve", "Cleaned light curve", "Folded transit"])
            with raw_tab:
                st.plotly_chart(chart(demo_result["time"], demo_result["raw_flux"], "Kepler-10 raw observations", "Time (days)", "Normalized flux", color="#F1C96A"), use_container_width=True)
            with clean_tab:
                st.plotly_chart(chart(demo_result["time"], demo_result["cleaned_flux"], "Transit-aware cleaned observations", "Time (days)", "Relative flux", color="#73CFE0"), use_container_width=True)
            with fold_tab:
                phase = ((np.asarray(demo_result["time"]) - detection["epoch_days"] + detection["period_days"] / 2) % detection["period_days"]) / detection["period_days"]
                order = np.argsort(phase)
                st.plotly_chart(chart((phase[order] - .5) * detection["period_days"] * 24, np.asarray(demo_result["cleaned_flux"])[order], "Kepler-10 transit folded at the measured BLS period", "Hours from transit center", "Relative flux", color="#F1C96A"), use_container_width=True)
            st.caption(f"Source: {meta['source']} · {meta['description']} · {demo_result['n_clean']:,} quality-filtered measurements. Catalog disposition is reference context only; measured BLS period is {detection['period_days']:.6f} days.")
            st.button("Open signal investigation →", on_click=select_page, args=("Signal Investigation",))
        st.markdown('<div class="pip-rule"></div><div class="pip-panel"><div class="eyebrow">FOLLOW THE EVIDENCE</div><h2>Promising clues are candidates, not confirmed discoveries.</h2><p>Every result keeps its measurements, data source and limitations visible. A repeating dip can be a planet candidate, an eclipsing binary or an instrumental effect. Follow-up observations are needed for confirmation.</p></div>', unsafe_allow_html=True)
        st.button("Start an investigation →", type="primary", on_click=select_page, args=("Analyze Star",))
        st.markdown('<footer class="pip-footnote" style="border-top:1px solid #26364c;margin-top:3rem;padding-top:1.2rem">PIP · THE LITTLE STAR DETECTIVE &nbsp; · &nbsp; Tiny dips. Hidden worlds. &nbsp; · &nbsp; Real observations, transparent methods, candidates that still need follow-up.</footer>', unsafe_allow_html=True)
elif page == "Overview":
    header("YOUR WORKSPACE / 01", "Overview", "A clear view of this session’s investigation and the next useful step.")
    a = st.session_state.analysis
    cols = st.columns(4)
    values = [
        ("OBSERVATIONS PROCESSED", f"{a['n_clean']:,}" if a else "—"),
        ("SIGNALS IN SESSION", "1" if a else "0"),
        ("PLANET-LIKE FLAG", ("Yes" if a["vetting"]["label"] == "Planet-like" else "No") if a else "—"),
        ("PIPELINE STATE", "READY" if a else "IDLE"),
    ]
    for col, (lab, val) in zip(cols, values):
        with col:
            metric(lab, val)
    st.markdown("### Start an investigation")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            "**Analyze a star**\n\nSearch Kepler or TESS observations in MAST, or upload a CSV/FITS light curve."
        )
        st.button(
            "Open Analyze Star →",
            use_container_width=True,
            on_click=select_page,
            args=("Analyze Star",),
        )
    with c2:
        st.markdown(
            "**Measure signal recoverability**\n\nInject known transits into the observed noise and measure what your pipeline recovers."
        )
        st.button(
            "Open Planet Recovery Lab →",
            use_container_width=True,
            on_click=select_page,
            args=("Planet Recovery Lab",),
        )
    if a:
        st.markdown("### Latest analysis")
        cc = st.columns(4)
        for col, (lab, val) in zip(
            cc,
            [
                ("Period", f"{a['detection']['period_days']:.6g} d"),
                ("Depth", f"{a['detection']['depth_ppm']:.0f} ppm"),
                ("Duration", f"{a['detection']['duration_hours']:.2f} h"),
                ("Vetting", a["vetting"]["label"]),
            ],
        ):
            with col:
                metric(lab, val)
        st.plotly_chart(
            chart(
                a["time"], a["raw_flux"], "Latest raw observation", "Time (days)", "Normalized flux"
            ),
            use_container_width=True,
        )
    st.info(
        "No application-wide counts are claimed: metrics above reflect this browser session only. Archive dispositions are not live confirmations."
    )

elif page == "Analyze Star":
    header(
        "DATA ACQUISITION / 02",
        "Analyze Star",
        "Use public archive observations or upload your own validated light curve.",
    )
    mode = st.radio(
        "Input source",
        [
            "Cached real Kepler-10 example",
            "Cached KOI false-positive example",
            "Search MAST",
            "Upload light curve",
        ],
        horizontal=True,
    )
    curve = None
    if mode == "Cached real Kepler-10 example":
        demo_path = Path("data/demo/kepler10_q17_longcadence.csv")
        meta_path = demo_path.with_suffix(".json")
        if demo_path.exists() and meta_path.exists():
            demo_meta = json.loads(meta_path.read_text(encoding="utf-8"))
            demo_frame = pd.read_csv(demo_path)
            curve = LightCurve.from_frame(
                demo_frame,
                "time",
                "flux",
                "flux_err",
                "quality",
                {**demo_meta, "source": "cached real Kepler observation"},
            )
            st.info(
                "Real NASA Kepler Q17 observations for Kepler-10. KOI-72.01 is cataloged as confirmed; "
                "the signal measured below is still a photometric reanalysis, not independent confirmation. "
                "This cached sample works without archive access."
            )
        else:
            st.error("Cached real demonstration data are missing.")
    elif mode == "Search MAST":
        x1, x2 = st.columns([2, 1])
        with x1:
            target = st.text_input(
                "Target identifier", placeholder="Kepler-10, KIC 11904151, TIC 261136679"
            )
        with x2:
            mission = st.selectbox("Mission", ["Kepler", "TESS"])
        if st.button("Search public observations", type="primary"):
            if not target.strip():
                st.warning("Enter a target name or catalog identifier.")
            else:
                with st.spinner("Querying MAST through Lightkurve…"):
                    try:
                        results, rows = search_observations(target.strip(), mission)
                        st.session_state.search_results = results
                        st.session_state.search_rows = rows
                        st.session_state.search_target = target.strip()
                    except Exception as e:
                        st.error(f"MAST search failed: {e}")
        if st.session_state.get("search_rows"):
            rows = st.session_state.search_rows
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            idx = st.selectbox(
                "Choose a product",
                range(len(rows)),
                format_func=lambda i: f"{i}: {rows[i]['product']} · {rows[i]['author']} · sector {rows[i]['sector']} quarter {rows[i]['quarter']}",
            )
            if st.button("Download selected observation"):
                try:
                    t, f, e, q = download_observation(st.session_state.search_results, idx)
                    curve = LightCurve(
                        t,
                        f,
                        e,
                        q,
                        {
                            "target": st.session_state.search_target,
                            "mission": mission,
                            "archive": "MAST via Lightkurve",
                            "product": rows[idx],
                            "product_index": idx,
                        },
                    )
                except Exception as exc:
                    st.error(f"Download failed: {exc}")
    else:
        upload = st.file_uploader(
            "Upload CSV or FITS", type=["csv", "fits", "fit", "fz"], max_upload_size=100
        )
        if upload:
            try:
                if upload.name.lower().endswith("csv"):
                    df = pd.read_csv(upload, nrows=500_000)
                    st.caption(f"{len(df):,} rows · columns: {', '.join(df.columns)}")
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        tc = st.selectbox("Time column", df.columns)
                    with c2:
                        fc = st.selectbox(
                            "Flux column", df.columns, index=min(1, len(df.columns) - 1)
                        )
                    with c3:
                        ec = st.selectbox("Uncertainty (optional)", ["None", *df.columns])
                    with c4:
                        qc = st.selectbox("Quality flag (optional)", ["None", *df.columns])
                    if st.button("Validate uploaded CSV"):
                        curve = LightCurve.from_frame(
                            df,
                            tc,
                            fc,
                            None if ec == "None" else ec,
                            None if qc == "None" else qc,
                            {
                                "target": upload.name,
                                "source": "user upload",
                                "filename": upload.name,
                            },
                        )
                else:
                    with fits.open(upload, memmap=False) as hdul:
                        tables = [
                            hdu
                            for hdu in hdul
                            if getattr(hdu, "data", None) is not None
                            and getattr(hdu.data, "names", None)
                        ]
                        if not tables:
                            raise ValueError("No binary table found in FITS file.")
                        names = tables[0].data.names
                        st.write("FITS columns:", ", ".join(names))
                        tc = st.selectbox(
                            "Time column",
                            names,
                            index=next((i for i, n in enumerate(names) if "TIME" in n.upper()), 0),
                        )
                        fc = st.selectbox(
                            "Flux column",
                            names,
                            index=next(
                                (
                                    i
                                    for i, n in enumerate(names)
                                    if "FLUX" in n.upper() and "ERR" not in n.upper()
                                ),
                                min(1, len(names) - 1),
                            ),
                        )
                        if st.button("Validate uploaded FITS"):
                            arr = tables[0].data
                            ec = next((n for n in names if "FLUX_ERR" in n.upper()), None)
                            qc = next((n for n in names if "QUALITY" in n.upper()), None)
                            curve = LightCurve(
                                np.asarray(arr[tc], float),
                                np.asarray(arr[fc], float),
                                np.asarray(arr[ec], float) if ec else None,
                                np.asarray(arr[qc]) if qc else None,
                                {
                                    "target": upload.name,
                                    "source": "user FITS upload",
                                    "filename": upload.name,
                                },
                            ).validate()
            except Exception as exc:
                st.error(f"Upload could not be validated: {exc}")
    if curve:
        try:
            curve.validate()
            st.session_state.curve = curve
        except Exception as exc:
            st.error(str(exc))
    curve = st.session_state.curve
    if curve:
        st.success(
            f"Validated {len(curve.time):,} unique observations. Provenance: {json.dumps(curve.provenance)}"
        )
        st.plotly_chart(
            chart(curve.time, curve.flux, "Original measurements", "Time (days)", "Flux"),
            use_container_width=True,
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            low = st.number_input("Minimum period (days)", 0.1, 100.0, 0.5, 0.1)
        with c2:
            high = st.number_input(
                "Maximum period (days)",
                1.0,
                500.0,
                min(max(float(np.ptp(curve.time) / 2), 2), 30),
                0.5,
            )
        with c3:
            window = st.number_input("Detrending window (days)", 0.25, 10.0, 1.5, 0.25)
        if st.button("Run BLS analysis", type="primary"):
            with st.spinner("Conservative detrending and BLS period search…"):
                try:
                    # User-selected detrending window flows into the same scientific engine.
                    from transitiq.preprocess import detrend as detrender

                    clean, base, params = detrender(curve, window_days=window)
                    result = analyze(curve, (low, high), window)
                    result["cleaned_flux"] = clean.tolist()
                    result["baseline"] = base.tolist()
                    result["processing"] = params
                    result["search_limits"] = {"min_period": low, "max_period": high}
                    st.session_state.analysis = result
                    st.success("Analysis completed.")
                except Exception as e:
                    st.error(f"Analysis could not be completed: {e}")
        if st.session_state.analysis:
            a = st.session_state.analysis
            st.plotly_chart(
                chart(
                    a["time"],
                    a["cleaned_flux"],
                    "Cleaned light curve",
                    "Time (days)",
                    "Relative flux",
                    color="#9d8bff",
                ),
                use_container_width=True,
            )
            d = a["detection"]
            st.write(
                f"**Best BLS period:** {d['period_days']:.7g} days · **Depth:** {d['depth_ppm']:.1f} ppm · **Duration:** {d['duration_hours']:.2f} hours · **Epoch:** {d['epoch_days']:.6f} days"
            )
            st.caption(
                "BLS power is a periodogram statistic and is not a probability. S/N shown in candidate review is approximate."
            )
            if st.button("Save analysis exports"):
                p = save_analysis(a)
                st.success(f"Saved JSON metadata: {p} and candidate CSV under outputs/.")

elif page in ("Candidate Explorer", "Signal Investigation"):
    header(
        "CANDIDATE REVIEW / 03",
        "Candidate Explorer" if page == "Candidate Explorer" else "Signal Investigation",
        "Inspect the measurements and caveats behind the strongest periodic dimming.",
    )
    a = st.session_state.analysis
    if not a:
        empty_left, empty_copy = st.columns([1, 3])
        with empty_left:
            st.image("assets/pip.svg", width=90)
        with empty_copy:
            st.info("Pip is ready to investigate. Run an analysis on Analyze Star to see real candidate evidence here.")
    else:
        d, v = a["detection"], a["vetting"]
        row = {
            "Candidate": "BLS-01",
            "Target": a["target"],
            "Period (d)": d["period_days"],
            "Depth (ppm)": d["depth_ppm"],
            "Duration (h)": d["duration_hours"],
            "Epoch (d)": d["epoch_days"],
            "BLS power": d["bls_power"],
            "Approx. S/N": d["snr_approx"],
            "Events": d["event_count"],
            "Photometric triage": v["label"],
            "Ranking score": round(
                min(
                    100,
                    10 * np.log10(max(d["bls_power"], 1e-10))
                    + 5 * d["event_count"]
                    + min(d["snr_approx"], 20),
                ),
                1,
            ),
        }
        st.markdown("<style>@media(max-width:640px){[data-testid=\"stDataFrame\"]{display:none}}</style>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([row]), use_container_width=True, hide_index=True)
        st.markdown(
            f'''<article class="pip-panel candidate-mobile" style="display:none">
            <div class="eyebrow">{html.escape(row['Candidate'])} · {html.escape(str(row['Target']))}</div>
            <h3>{html.escape(str(row['Photometric triage']))} candidate signal</h3>
            <p><strong>{row['Period (d)']:.6g} days</strong> orbital period · {row['Depth (ppm)']:.1f} ppm depth</p>
            <p>{row['Duration (h)']:.2f} hours duration · {row['Events']} estimated events</p>
            <p class="pip-footnote">Photometric triage is a clue for review, not a planet confirmation.</p></article>''',
            unsafe_allow_html=True,
        )
        c = st.columns(4)
        for col, (lab, val) in zip(
            c,
            [
                ("Orbital period", f"{d['period_days']:.6f} days"),
                ("Transit depth", f"{d['depth_ppm']:.1f} ppm"),
                ("Duration", f"{d['duration_hours']:.2f} hours"),
                ("Vetting", v["label"]),
            ],
        ):
            with col:
                metric(lab, val)
        st.caption(
            "Ranking is a transparent heuristic; BLS power, event count and approximate S/N remain distinct evidence. No ML probability is shown without a validated model."
        )
        if page == "Signal Investigation":
            tab1, tab2, tab3, tab4 = st.tabs(["RAW", "CLEANED", "FOLDED", "PERIODOGRAM"])
            with tab1:
                st.plotly_chart(
                    chart(
                        a["time"],
                        a["raw_flux"],
                        "Original raw light curve",
                        "Time (days)",
                        "Normalized flux",
                    ),
                    use_container_width=True,
                )
            with tab2:
                st.plotly_chart(
                    chart(
                        a["time"],
                        a["cleaned_flux"],
                        "Transit-aware cleaned light curve",
                        "Time (days)",
                        "Relative flux",
                        color="#9d8bff",
                    ),
                    use_container_width=True,
                )
                st.json(a["processing"])
            with tab3:
                phase = (
                    (np.asarray(a["time"]) - d["epoch_days"] + d["period_days"] / 2)
                    % d["period_days"]
                ) / d["period_days"]
                order = np.argsort(phase)
                st.plotly_chart(
                    chart(
                        (phase[order] - 0.5) * d["period_days"] * 24,
                        np.asarray(a["cleaned_flux"])[order],
                        "Phase-folded transit",
                        "Hours from transit center",
                        "Relative flux",
                        color="#ffca7a",
                    ),
                    use_container_width=True,
                )
            with tab4:
                pg = d["periodogram"]
                st.plotly_chart(
                    chart(
                        pg["period"],
                        pg["power"],
                        "BLS periodogram",
                        "Trial period (days)",
                        "BLS power",
                        color="#5ce1e6",
                    ),
                    use_container_width=True,
                )
            st.markdown("#### Independent Transit Least Squares verification")
            if st.button("Run TLS verification", type="secondary"):
                limits = a.get("search_limits", {"min_period": 0.5, "max_period": 15.0})
                with st.spinner("Running the independent limb-darkened TLS search…"):
                    st.session_state.tls_result = verify_tls(
                        a["time"], a["cleaned_flux"], limits["min_period"], limits["max_period"]
                    )
            tls_result = st.session_state.get("tls_result")
            if tls_result:
                if not tls_result["available"]:
                    st.warning(tls_result["error"])
                else:
                    period_delta = (
                        abs(tls_result["period_days"] - d["period_days"]) / d["period_days"]
                    )
                    depth_delta = abs(tls_result["depth_fraction"] - d["depth_fraction"]) / max(
                        abs(d["depth_fraction"]), 1e-12
                    )
                    st.write(
                        f"TLS period **{tls_result['period_days']:.7g} d**, depth "
                        f"**{tls_result['depth_ppm']:.1f} ppm**, duration "
                        f"**{tls_result['duration_hours']:.2f} h**, SDE **{tls_result['sde']:.2f}**, "
                        f"S/N **{tls_result['snr']:.2f}**."
                    )
                    if period_delta > 0.02 or depth_delta > 0.5:
                        st.warning(
                            f"TLS and BLS disagree beyond review tolerances (period difference "
                            f"{period_delta:.1%}; depth difference {depth_delta:.1%})."
                        )
                    else:
                        st.success(
                            "TLS and BLS agree within the 2% period and 50% depth review tolerances."
                        )
                    st.plotly_chart(
                        chart(
                            tls_result["periodogram"]["period"],
                            tls_result["periodogram"]["power"],
                            "TLS periodogram",
                            "Trial period (days)",
                            "TLS power",
                            color="#ffca7a",
                        ),
                        use_container_width=True,
                    )
                    if tls_result["warnings"]:
                        st.caption("TLS diagnostics: " + "; ".join(tls_result["warnings"]))
            st.markdown("#### Photometric vetting")
            st.write(v["label"])
            st.json(v["flags"])
            [st.warning(x) for x in v["reasons"]]
            st.caption(v["caveat"])
            st.download_button(
                "Download investigation report (HTML)",
                make_html_report(a),
                file_name="pip_investigation.html",
                mime="text/html",
            )
            st.download_button(
                "Download full measurements (JSON)",
                json.dumps(a, indent=2),
                file_name="pip_analysis.json",
                mime="application/json",
            )
            if st.button("Prepare plotted PDF report"):
                with st.spinner("Rendering report plots…"):
                    st.session_state.pdf_report = make_pdf_report(a)
            if "pdf_report" in st.session_state:
                st.download_button(
                    "Download investigation report (PDF)",
                    st.session_state.pdf_report,
                    file_name="pip_investigation.pdf",
                    mime="application/pdf",
                )
        else:
            st.write("Candidate details are available under Signal Investigation.")

elif page == "Planet Recovery Lab":
    header(
        "EXPERIMENTS / 04",
        "Planet Recovery Lab",
        "Measure detection recovery on your observed noise. Injection metrics are synthetic signal experiments, not catalogue benchmark accuracy.",
    )
    c = st.session_state.curve
    if c is None:
        st.warning(
            "Load an observed light curve on Analyze Star to run injection/recovery experiments."
        )
    else:
        x1, x2, x3, x4, x5 = st.columns(5)
        with x1:
            depth = st.number_input("Injected depth (ppm)", 100.0, 20000.0, 1000.0, 100.0) / 1e6
        with x2:
            period = st.number_input("Period (days)", 0.5, 100.0, 5.0, 0.25)
        with x3:
            dur = st.number_input("Duration (hours)", 0.5, 24.0, 3.0, 0.5)
        with x4:
            noise = st.number_input("Added noise (× robust scatter)", 0.0, 3.0, 0.0, 0.25)
        with x5:
            repeats = st.number_input("Grid repeats", 1, 10, 1)
        if st.button("Inject & recover", type="primary"):
            try:
                with st.spinner("Injecting synthetic transits into the real measurements…"):
                    result = run_injection(
                        c.time,
                        c.flux / np.nanmedian(c.flux),
                        period,
                        dur,
                        depth,
                        noise_scale=noise,
                        seed=42,
                    )
                st.session_state.injection = result
                st.success("Experiment completed")
            except Exception as e:
                st.error(f"Experiment failed: {e}")
        if st.session_state.get("injection"):
            r = st.session_state.injection
            cols = st.columns(4)
            for col, (lab, val) in zip(
                cols,
                [
                    ("Recovery status", "RECOVERED" if r["recovered"] else "NOT RECOVERED"),
                    ("Period error", f"{100*r['period_error_fraction']:.2f}%"),
                    ("Depth error", f"{100*r['depth_error_fraction']:.1f}%"),
                    (
                        "Attenuation",
                        f"{100*r['transit_preservation_attenuation']:.1f}%"
                        if r["transit_preservation_attenuation"] is not None
                        else "n/a",
                    ),
                ],
            ):
                with col:
                    metric(lab, val)
            st.caption(
                "Recovery criterion defined in advance: period error ≤2% and relative depth error ≤50%."
            )
            st.plotly_chart(
                chart(
                    c.time,
                    r["injected_flux"],
                    "Observed light curve with injected transit",
                    "Time (days)",
                    "Flux",
                    color="#ffca7a",
                ),
                use_container_width=True,
            )
            st.plotly_chart(
                chart(
                    c.time,
                    r["cleaned_flux"],
                    "Cleaned injected light curve",
                    "Time (days)",
                    "Relative flux",
                    color="#9d8bff",
                ),
                use_container_width=True,
            )
        if st.button("Run depth × period × noise grid"):
            with st.spinner("Running repeated injections and searches…"):
                st.session_state.grid = injection_grid(
                    c.time,
                    c.flux / np.nanmedian(c.flux),
                    depths=(0.0005, 0.001, 0.002),
                    periods=(2.0, 5.0),
                    noise_levels=(0.0, 0.5, 1.0),
                    repeats=int(repeats),
                )
        if st.session_state.get("grid"):
            g = st.session_state.grid
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            k: v
                            for k, v in x.items()
                            if k
                            not in (
                                "detection",
                                "cleaned_flux",
                                "injected_flux",
                                "processing",
                                "matching_tolerances",
                            )
                        }
                        for x in g
                    ]
                ),
                use_container_width=True,
            )
            st.metric("Observed grid recovery rate", f"{sum(x['recovered'] for x in g)/len(g):.1%}")
            grouped = pd.DataFrame(g).groupby("added_noise_sigma_scatter")["recovered"].mean()
            st.write("Recovery rate by added-noise level (multiples of measured robust scatter):")
            st.dataframe(
                grouped.rename("recovery_rate").reset_index(),
                hide_index=True,
                use_container_width=True,
            )
            st.download_button(
                "Download experiment CSV",
                pd.DataFrame(
                    [
                        {
                            k: v
                            for k, v in x.items()
                            if k not in ("detection", "cleaned_flux", "injected_flux", "processing")
                        }
                        for x in g
                    ]
                ).to_csv(index=False),
                "injection_recovery.csv",
                "text/csv",
            )
    st.divider()
    st.markdown("### NASA Exoplanet Archive catalogue benchmark")
    benchmark_path = Path("docs/benchmark_results.json")
    if benchmark_path.exists():
        benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
        st.caption(
            f"Retrieved {benchmark['retrieved_at_utc']} · {benchmark['sample_rows']:,} labeled KOIs · "
            f"held-out test {sum(benchmark['test_class_counts'].values()):,} rows, grouped by target star."
        )
        model_metrics = benchmark["models"]["random_forest"]
        cols = st.columns(4)
        for col, (label, value) in zip(
            cols,
            [
                ("ACCURACY", model_metrics["accuracy"]),
                ("F1", model_metrics["f1"]),
                ("PR-AUC", model_metrics["pr_auc"]),
                ("ROC-AUC", model_metrics["roc_auc"]),
            ],
        ):
            with col:
                metric(label, f"{value:.3f}")
        baseline = benchmark["models"]["logistic_baseline"]
        st.write(
            f"Random Forest Brier score: {model_metrics['brier_score']:.3f}; calibrated held-out Brier: "
            f"{benchmark['calibrated_random_forest']['test_brier_score']:.3f}. "
            f"Logistic baseline PR-AUC: {baseline['pr_auc']:.3f}."
        )
        tn, fp, fn, tp = model_metrics["confusion_matrix_tn_fp_fn_tp"]
        fig = go.Figure(
            go.Heatmap(
                z=[[tn, fp], [fn, tp]],
                x=["Predicted FP", "Predicted candidate"],
                y=["Actual FP", "Actual candidate"],
                text=[[tn, fp], [fn, tp]],
                texttemplate="%{text}",
                colorscale=[[0, "#111a2b"], [1, "#4e9ca7"]],
                showscale=False,
            )
        )
        fig.update_layout(
            title="Held-out Random Forest confusion matrix",
            height=330,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#c7d5eb"},
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Catalog-label benchmark only. KOI features and dispositions are selection-biased; it is not validated for live light-curve predictions."
        )
    else:
        st.write(
            "Run `python scripts/benchmark.py` to fetch and evaluate the latest NASA Exoplanet Archive KOI table."
        )

elif page == "Model Performance":
    header("MODEL EVALUATION / 06", "Model Performance", "Measured benchmark results with their scope and limitations in view.")
    benchmark_path = Path("docs/benchmark_results.json")
    if benchmark_path.exists():
        benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
        m = benchmark["models"]["random_forest"]
        st.caption(f"NASA Exoplanet Archive catalogue benchmark · retrieved {benchmark['retrieved_at_utc']} · {benchmark['sample_rows']:,} labeled KOIs · target-star grouped held-out evaluation.")
        cols = st.columns(4)
        for col, (label, value) in zip(cols, [("Accuracy",m["accuracy"]),("Precision",m["precision"]),("Recall",m["recall"]),("F1",m["f1"])]):
            with col:
                metric(label, f"{value:.3f}")
        cols = st.columns(3)
        for col, (label, value) in zip(cols, [("PR-AUC",m["pr_auc"]),("ROC-AUC",m["roc_auc"]),("Brier score",m["brier_score"])]):
            with col:
                metric(label, f"{value:.3f}")
        baseline = benchmark["models"]["logistic_baseline"]
        tn, fp, fn, tp = m["confusion_matrix_tn_fp_fn_tp"]
        fig = go.Figure(go.Heatmap(z=[[tn,fp],[fn,tp]],x=["Predicted false positive","Predicted candidate"],y=["Actual false positive","Actual candidate"],text=[[tn,fp],[fn,tp]],texttemplate="%{text}",colorscale=[[0,"#142238"],[1,"#73CFE0"]],showscale=False))
        fig.update_layout(title="Held-out Random Forest confusion matrix",height=360,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font={"color":"#F4F0E8"},margin={"l":15,"r":15,"t":55,"b":35})
        st.plotly_chart(fig,use_container_width=True)
        st.write(f"Logistic baseline: accuracy {baseline['accuracy']:.3f}, F1 {baseline['f1']:.3f}, PR-AUC {baseline['pr_auc']:.3f}, ROC-AUC {baseline['roc_auc']:.3f}.")
        st.warning("These scores evaluate catalog disposition labels, not live light-curve predictions. Catalog features are selection-biased, and no AI probability is produced for an arbitrary target.")
    else:
        st.info("No saved catalogue benchmark is available in this deployment. The page does not invent model scores.")

else:
    header(
        "DOCUMENTATION / 05",
        "Research & Methods",
        "The evidence chain, data provenance and limitations are part of the result.",
    )
    with st.expander("Simple guide · How do tiny dips reveal planets?", expanded=True):
        st.markdown("""
**Light curve:** a record of how bright one star appears over time.

**Transit:** a planet passing between us and its star. The star appears slightly dimmer while the planet crosses it.

**Orbital period:** the time between repeating transits. A repeating pattern is a useful clue, but it can also come from a false alarm.

**Transit depth:** how much the measured starlight dips. It depends on the relative sizes of the planet and star, as well as the data quality.

**Phase folding:** lining up observations by the proposed period so repeated events can be compared together.

**False positive:** a signal that looks transit-like but has another cause, such as an eclipsing binary or an instrumental effect.

Pip reports **potential candidates**, never automatic confirmations. Follow-up observations are needed to confirm a planet.
""")
    st.markdown("#### Research mode")
    st.markdown("""
### Pipeline
1. **Acquire** public Kepler/TESS light-curve products through Lightkurve's MAST interface, or validate uploaded CSV/FITS time series. Raw samples are retained.
2. **Quality control** filters non-finite/non-positive flux, optional nonzero quality flags, sorts timestamps and collapses duplicate times.
3. **Detrend conservatively** with an iteratively transit-masked median baseline. Negative residuals are excluded from baseline estimation to reduce transit attenuation. Parameters and masked point count are recorded.
4. **Search with Astropy BLS** over configurable periods and box durations. Reported quantities include period (days), epoch (input time system), duration (hours), relative depth (fraction and ppm), periodogram power, rough depth S/N, and an event-count estimate.
5. **Vetting** reports odd/even depth difference, secondary-eclipse proxy, event availability, and a multi-indicator photometric triage label. Diagnostics are not a confirmation.
6. **Injection/recovery** inserts a box-shaped synthetic signal into observed data and reruns the same cleaning/BLS path. Grid recovery rates are tied to explicit 2% period and 50% depth tolerances.

### Data sources
- NASA MAST via Lightkurve: public Kepler and TESS mission light curves, product metadata retained for search/download sessions.
- NASA Exoplanet Archive: KOI cumulative table via TAP for a reproducible group-held-out classifier benchmark.
- User-supplied CSV and FITS are identified as uploads in provenance metadata.

### Machine learning status
The benchmark workflow trains a Random Forest and a logistic baseline on labeled KOI catalog rows, grouped by target star. It excludes disposition labels from predictive inputs. The archive features are catalog-derived and are not identical to features measured from a user's light curve. For that reason, this initial release does not misrepresent those outputs as live candidate probabilities. It saves metrics and model provenance after explicit benchmark execution.

### Limitations
- TLS verification uses a separate limb-darkened search and is user-triggered; computation can be slow. BLS remains available if TLS fails.
- Detection is single-best-signal in the interactive pipeline; iterative multi-planet extraction and harmonic rejection are not implemented.
- BLS and injections use a box-shaped signal; TLS provides a separate limb-darkened verification. Synthetic injections are not observed planets.
- Odd/even and secondary diagnostics need enough events and are sensitive to cadence and data gaps.
- No confirmed discoveries are claimed. Catalog dispositions are labels for benchmark evaluation, not external follow-up.
- Flux units, time system and time correction metadata may vary by uploaded file; the application records provenance but users should verify source-specific time conventions.

See `docs/SCIENTIFIC_METHODS.md` and `docs/VALIDATION_RESULTS.md` for reproducibility notes.
""")
