from io import BytesIO
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image


def _table(data, widths=None):
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                           ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                           ("FONTSIZE", (0, 0), (-1, -1), 8),
                           ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")])]))
    return t


def build_pdf(day, rows, st, ann_dir: Path):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5*cm, rightMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    S = getSampleStyleSheet()
    el = [Paragraph("DefectEye - Daily Quality Inspection Report", S["Title"]),
          Paragraph(f"Date: {day} &nbsp;&nbsp; Prepared for: Head Supervisor", S["Normal"]), Spacer(1, 12)]
    el.append(Paragraph("1. Summary", S["Heading2"]))
    el.append(_table([["Parts checked", "Verified by operator", "PASS", "REWORK", "RECYCLE", "Pass rate"],
                      [st["checked"], st["verified"], st["PASS"], st["REWORK"], st["RECYCLE"], f"{st['pass_rate']}%"]]))
    el.append(Spacer(1, 10))
    el.append(Paragraph("2. Defects found", S["Heading2"]))
    dt = st["defect_types"]
    el.append(_table([["Defect type", "Count"]] + ([[k.replace("_", " "), v] for k, v in dt.items()] or [["none", 0]]),
                     [8*cm, 3*cm]))
    flagged = [r for r in rows if r["decision"] != "PASS"]
    el.append(Spacer(1, 10))
    el.append(Paragraph("3. Flagged parts (images)", S["Heading2"]))
    imgs = []
    for r in flagged[:6]:
        p = ann_dir / r["image"]
        if p.exists():
            imgs.append([Image(str(p), 8*cm, 6.4*cm), Paragraph(f"#{r['id']} {r['name']}<br/>{r['decision']}", S["Normal"])])
    if imgs:
        grid = [sum(imgs[i:i+2], []) for i in range(0, len(imgs), 2)]
        el.append(Table(grid, colWidths=[6*cm, 2.5*cm, 6*cm, 2.5*cm][:len(grid[0])]))
    else:
        el.append(Paragraph("No flagged parts.", S["Normal"]))
    el.append(Paragraph("4. Full inspection log", S["Heading2"]))
    log = [["ID", "Time", "Part", "Type", "Defects", "Decision", "Verified"]]
    for r in reversed(rows):
        log.append([r["id"], r["ts"], r["name"][:26], r["part_type"],
                    ", ".join(d["type"] for d in r["defects"]) or "-", r["decision"], "Yes" if r["verified"] else "No"])
    el.append(_table(log))
    el += [Spacer(1, 40), Paragraph("Supervisor signature: ______________________ &nbsp;&nbsp; Date: ____________", S["Normal"])]
    doc.build(el)
    return buf.getvalue()
