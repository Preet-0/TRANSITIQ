from __future__ import annotations
import json
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
    page_title="TRANSITIQ | Signal Analysis",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
:root{--bg:#070b16;--panel:#0d1424;--line:#1d2a40;--text:#e7efff;--muted:#91a3bf;--cyan:#5ce1e6;--violet:#9d8bff}
.stApp{background:radial-gradient(ellipse at 76% -10%,#15284b 0%,transparent 38%),var(--bg);color:var(--text);font-family:Manrope,sans-serif}
[data-testid="stSidebar"]{background:#080e1a;border-right:1px solid var(--line)}
.block-container{padding-top:2rem;max-width:1440px}
h1,h2,h3{letter-spacing:-.035em} h1{font-weight:800}
.metric-card{background:linear-gradient(145deg,#101a2c,#0a111e);border:1px solid var(--line);border-radius:14px;padding:18px 20px;min-height:98px}
.metric-label{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted)}
.metric-value{font-size:25px;font-weight:700;margin-top:5px;color:#f4f7ff}
.eyebrow{font:500 11px 'DM Mono',monospace;color:var(--cyan);letter-spacing:.17em;text-transform:uppercase}
.small-note{color:var(--muted);font-size:13px}.stButton>button{border-radius:8px;border:1px solid #32516b;background:#122338;color:#d9faff}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:10px}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)
PAGES = [
    "Mission Control",
    "Analyze Star",
    "Candidate Explorer",
    "Signal Investigation",
    "Validation Lab",
    "Research & Methods",
]


def select_page(name):
    st.session_state.page_select = name


with st.sidebar:
    st.markdown('<div class="eyebrow">✦ TRANSITIQ</div>', unsafe_allow_html=True)
    st.caption("Intelligent Exoplanet Discovery")
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
        title=title,
        xaxis_title=xlabel,
        yaxis_title=ylabel,
        height=390,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(8,14,26,.55)",
        font={"color": "#c7d5eb", "family": "Manrope"},
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


if page == "Mission Control":
    header(
        "RESEARCH OPERATIONS / 01",
        "Mission Control",
        "A transparent workspace for turning faint stellar dimmings into testable candidate evidence.",
    )
    a = st.session_state.analysis
    cols = st.columns(4)
    values = [
        ("OBSERVATIONS PROCESSED", f"{a['n_clean']:,}" if a else "—"),
        ("CANDIDATES IN SESSION", "1" if a else "0"),
        ("PLANET-LIKE FLAGS", str(a["vetting"]["label"] == "Planet-like") if a else "—"),
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
            "Open Validation Lab →",
            use_container_width=True,
            on_click=select_page,
            args=("Validation Lab",),
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
        st.info("Run an analysis first on the Analyze Star page.")
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
        st.dataframe(pd.DataFrame([row]), use_container_width=True, hide_index=True)
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
                file_name="transitiq_investigation.html",
                mime="text/html",
            )
            st.download_button(
                "Download full measurements (JSON)",
                json.dumps(a, indent=2),
                file_name="transitiq_analysis.json",
                mime="application/json",
            )
            if st.button("Prepare plotted PDF report"):
                with st.spinner("Rendering report plots…"):
                    st.session_state.pdf_report = make_pdf_report(a)
            if "pdf_report" in st.session_state:
                st.download_button(
                    "Download investigation report (PDF)",
                    st.session_state.pdf_report,
                    file_name="transitiq_investigation.pdf",
                    mime="application/pdf",
                )
        else:
            st.write("Candidate details are available under Signal Investigation.")

elif page == "Validation Lab":
    header(
        "EXPERIMENTS / 04",
        "Validation Lab",
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

else:
    header(
        "DOCUMENTATION / 05",
        "Research & Methods",
        "The evidence chain, data provenance and limitations are part of the result.",
    )
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
