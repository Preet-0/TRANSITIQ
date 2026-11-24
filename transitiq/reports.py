from __future__ import annotations
import json
from io import BytesIO
from pathlib import Path
import pandas as pd


def save_analysis(data, outdir="outputs"):
    path = Path(outdir)
    path.mkdir(exist_ok=True, parents=True)
    safe = "".join(
        x if x.isalnum() or x in "-_" else "_" for x in str(data.get("target", "target"))
    )[:60]
    (path / f"{safe}_analysis.json").write_text(
        json.dumps(data, indent=2, default=str), encoding="utf-8"
    )
    pd.DataFrame(data.get("candidates", [])).to_csv(path / f"{safe}_candidates.csv", index=False)
    return path / f"{safe}_analysis.json"


def make_html_report(data):
    import html

    target = html.escape(str(data.get("target", "Unknown")))
    rows = "".join(
        f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>"
        for k, v in data.get("detection", {}).items()
        if k != "periodogram"
    )
    return (
        f"<!doctype html><meta charset='utf-8'><title>TRANSITIQ report</title>"
        f"<h1>TRANSITIQ Candidate Investigation</h1><p>Target: {target}</p>"
        f"<p>Unconfirmed candidate analysis; not a discovery claim.</p><table>{rows}</table>"
        f"<pre>{html.escape(json.dumps(data.get('vetting', {}), indent=2))}</pre>"
    )


def make_pdf_report(data):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape

    output = BytesIO()
    story = []
    styles = getSampleStyleSheet()
    story.append(Paragraph("TRANSITIQ Candidate Investigation", styles["Title"]))
    story.append(Paragraph(f"Target: {data.get('target', 'Unknown')}", styles["Heading2"]))
    story.append(
        Paragraph(
            "Unconfirmed photometric candidate analysis. This report is not an exoplanet discovery or confirmation.",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 12))
    d = data.get("detection", {})
    rows = [
        ["Measurement", "Value"],
        ["Period (days)", f"{d.get('period_days', float('nan')):.7g}"],
        ["Depth (ppm)", f"{d.get('depth_ppm', float('nan')):.2f}"],
        ["Duration (hours)", f"{d.get('duration_hours', float('nan')):.3f}"],
        ["Epoch (input time units)", f"{d.get('epoch_days', float('nan')):.7f}"],
        ["BLS power", f"{d.get('bls_power', float('nan')):.5g}"],
        ["Approximate S/N", f"{d.get('snr_approx', float('nan')):.3f}"],
        ["Photometric triage", data.get("vetting", {}).get("label", "Unavailable")],
    ]
    table = Table(rows, colWidths=[2.5 * inch, 4 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#18304b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b7c6d9")),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6fa")]),
            ]
        )
    )
    story.extend([table, Spacer(1, 12)])
    provenance = data.get("provenance", {})
    if provenance:
        story.append(Paragraph("Data provenance", styles["Heading2"]))
        story.append(Paragraph(escape(json.dumps(provenance, default=str)), styles["BodyText"]))
        story.append(Spacer(1, 10))
    story.append(Paragraph("Light-curve diagnostics", styles["Heading2"]))
    t = data.get("time", [])
    raw = data.get("raw_flux", [])
    clean = data.get("cleaned_flux", [])
    if t and raw and clean:
        period = float(d.get("period_days", 1))
        epoch = float(d.get("epoch_days", 0))
        phase_hours = (
            (__import__("numpy").asarray(t) - epoch + period / 2) % period - period / 2
        ) * 24
        fig, axes = plt.subplots(3, 1, figsize=(8, 7), constrained_layout=True)
        axes[0].plot(t, raw, ".", ms=2, color="#248c9a")
        axes[0].set(title="Original observations", xlabel="Time (days)", ylabel="Flux")
        axes[1].plot(t, clean, ".", ms=2, color="#7669cc")
        axes[1].set(title="Detrended observations", xlabel="Time (days)", ylabel="Relative flux")
        order = __import__("numpy").argsort(phase_hours)
        axes[2].plot(
            phase_hours[order],
            __import__("numpy").asarray(clean)[order],
            ".",
            ms=2,
            color="#b7791f",
        )
        axes[2].set(
            title="BLS phase fold", xlabel="Hours from transit center", ylabel="Relative flux"
        )
        image_buffer = BytesIO()
        fig.savefig(image_buffer, format="png", dpi=130)
        plt.close(fig)
        image_buffer.seek(0)
        story.append(Image(image_buffer, width=6.6 * inch, height=5.8 * inch))
    story.extend(
        [
            Spacer(1, 8),
            Paragraph("Vetting diagnostics", styles["Heading2"]),
            Paragraph(
                escape(json.dumps(data.get("vetting", {}), indent=2, default=str)), styles["Code"]
            ),
            Spacer(1, 8),
            Paragraph("Scientific limitations", styles["Heading2"]),
            Paragraph(
                "BLS power and approximate S/N are not probabilities. Photometric indicators do not replace external follow-up. Catalog performance and synthetic injection-recovery are separate from confirmation.",
                styles["BodyText"],
            ),
        ]
    )
    SimpleDocTemplate(output, pagesize=letter, title="TRANSITIQ Candidate Investigation").build(
        story
    )
    return output.getvalue()
