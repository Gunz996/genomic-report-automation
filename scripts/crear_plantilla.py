"""Genera templates/plantilla_reporte.docx con etiquetas Jinja (docxtpl).

En el laboratorio se reemplaza por su plantilla real de Word: basta con escribir
las mismas etiquetas {{ ... }} y {%tr for ... %} en el documento existente.
"""
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor, Cm

DESTINO = Path(__file__).resolve().parents[1] / "templates" / "plantilla_reporte.docx"
AZUL = RGBColor(0x1F, 0x3A, 0x5F)


def titulo(doc, texto):
    p = doc.add_heading(texto, level=2)
    for r in p.runs:
        r.font.color.rgb = AZUL


def tabla_loop(doc, cabeceras, campos, loop, anchos=None):
    t = doc.add_table(rows=4, cols=len(cabeceras))
    t.style = "Light Grid Accent 1"
    t.autofit = False
    if anchos:
        for col, w in zip(t.columns, anchos):
            col.width = Cm(w)
        for row in t.rows:
            for cell, w in zip(row.cells, anchos):
                cell.width = Cm(w)
    for i, c in enumerate(cabeceras):
        t.rows[0].cells[i].text = c
    t.rows[1].cells[0].text = f"{{%tr for r in {loop} %}}"
    for i, c in enumerate(campos):
        t.rows[2].cells[i].text = f"{{{{ r.{c} }}}}"
    t.rows[3].cells[0].text = "{%tr endfor %}"
    for row in t.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(8)
    return t


def main():
    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(2)
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10)

    enc = sec.header.paragraphs[0]
    enc.text = "{{ laboratorio }} · Reporte técnico de corrida {{ corrida }}"
    enc.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    enc.runs[0].font.size = Pt(8)

    h = doc.add_heading("Reporte técnico de secuenciación", level=1)
    for r in h.runs:
        r.font.color.rgb = AZUL

    titulo(doc, "1. Datos de la corrida")
    t = doc.add_table(rows=4, cols=2)
    t.style = "Light List Accent 1"
    for i, (k, v) in enumerate([("Corrida", "{{ corrida }}"), ("Panel", "{{ panel }}"),
                                ("Muestras procesadas", "{{ total_muestras }}"),
                                ("Fecha de emisión", "{{ fecha_emision }}")]):
        t.rows[i].cells[0].text, t.rows[i].cells[1].text = k, v

    titulo(doc, "2. Resumen ejecutivo")
    doc.add_paragraph("{{ resumen }}")
    p = doc.add_paragraph("Fuente del texto: {{ fuente_resumen }}")
    p.runs[0].italic = True
    p.runs[0].font.size = Pt(8)

    titulo(doc, "3. Control de calidad por muestra")
    tabla_loop(doc, ["Muestra", "Tipo", "Lecturas", "%Q30", "%Dup", "Cob. media", "%≥20x", "Estado"],
               ["sample_id", "tipo_muestra", "total_reads", "pct_q30", "pct_duplicados",
                "cobertura_media", "pct_bases_20x", "estado"], "qc",
               anchos=[2.3, 2.3, 1.9, 1.3, 1.3, 1.8, 1.4, 4.7])
    doc.add_paragraph("{{ grafico_cobertura }}")

    titulo(doc, "4. Variantes patogénicas / probablemente patogénicas")
    doc.add_paragraph("Solo se listan variantes de muestras aptas. Clasificación según ACMG/AMP.")
    tabla_loop(doc, ["Muestra", "Gen", "Cromosoma", "Posición", "HGVS c.", "VAF", "Prof.", "Clasificación"],
               ["sample_id", "gen", "cromosoma", "posicion", "hgvs_c", "vaf", "profundidad", "clasificacion"],
               "variantes", anchos=[2.3, 1.5, 1.8, 2.2, 2.4, 1.3, 1.3, 4.2])
    doc.add_paragraph("{% if not variantes %}No se identificaron variantes relevantes.{% endif %}")

    titulo(doc, "5. Observaciones de validación")
    doc.add_paragraph("{{ n_errores }} errores y {{ n_advertencias }} advertencias detectados automáticamente.")
    tabla_loop(doc, ["Nivel", "Archivo", "Muestra", "Detalle"],
               ["nivel", "archivo", "sample_id", "detalle"], "hallazgos",
               anchos=[1.5, 2.2, 2.5, 10.8])

    titulo(doc, "6. Aprobación")
    doc.add_paragraph("\n______________________________          ______________________________\n"
                      "Elaborado por                                                 Revisado y aprobado por")

    DESTINO.parent.mkdir(exist_ok=True)
    doc.save(DESTINO)
    print(f"Plantilla creada: {DESTINO}")


if __name__ == "__main__":
    main()
