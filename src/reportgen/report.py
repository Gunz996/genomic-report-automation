"""Arma el contexto y renderiza el reporte sobre la plantilla Word."""
from datetime import date
from pathlib import Path

import pandas as pd
from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage

from .ai import redactar_resumen
from .charts import grafico_cobertura
from .validate import ETIQUETAS


def construir_hechos(corrida, datos, estado, hallazgos, reglas) -> dict:
    """Resumen numérico que recibe la IA (y el texto de respaldo)."""
    aptas = set(estado.loc[estado["estado"] != "NO APTA", "sample_id"])
    v = datos["variants"]
    rel = v[v["sample_id"].isin(aptas) & v["clasificacion"].isin(reglas["variantes"]["clasificaciones_relevantes"])]
    errores = hallazgos[hallazgos["nivel"] == "ERROR"]
    causas = (errores[errores["sample_id"].isin(estado["sample_id"])]
              .groupby("regla")["sample_id"].nunique().sort_values(ascending=False))
    return {
        "corrida": corrida,
        "panel": datos["samplesheet"]["panel"].iloc[0],
        "total_muestras": int(len(estado)),
        "estados": {k: int(n) for k, n in estado["estado"].value_counts().items()},
        "causas_rechazo": [f"{ETIQUETAS.get(r, r)} ({n} muestra{'s' if n > 1 else ''})" for r, n in causas.items()],
        "variantes_relevantes": {g: int(n) for g, n in rel["gen"].value_counts().items()},
    }, rel


def _fmt(df: pd.DataFrame, formatos: dict) -> list[dict]:
    out = df.copy()
    for col, f in formatos.items():
        out[col] = out[col].map(lambda x, f=f: f.format(x) if pd.notna(x) else "—")
    return out.fillna("—").to_dict("records")


def generar_reporte(corrida, datos, estado, hallazgos, reglas, plantilla, carpeta_salida,
                    laboratorio="Laboratorio de Genómica") -> dict:
    salida = Path(carpeta_salida)
    salida.mkdir(parents=True, exist_ok=True)

    hechos, rel = construir_hechos(corrida, datos, estado, hallazgos, reglas)
    resumen, fuente = redactar_resumen(hechos)

    qc = (datos["samplesheet"][["sample_id", "tipo_muestra"]]
          .merge(datos["qc_metrics"], on="sample_id", how="left")
          .merge(estado, on="sample_id"))
    png = grafico_cobertura(datos["qc_metrics"], estado,
                            reglas["qc"]["cobertura_media"]["fail_min"], salida / f"{corrida}_cobertura.png")

    tpl = DocxTemplate(plantilla)
    contexto = {
        "laboratorio": laboratorio,
        "corrida": corrida,
        "panel": hechos["panel"],
        "total_muestras": hechos["total_muestras"],
        "fecha_emision": date.today().strftime("%d/%m/%Y"),
        "resumen": resumen,
        "fuente_resumen": fuente,
        "qc": _fmt(qc, {"total_reads": "{:,.0f}", "pct_q30": "{:.1f}", "pct_duplicados": "{:.1f}",
                        "cobertura_media": "{:.0f}", "pct_bases_20x": "{:.1f}"}),
        "grafico_cobertura": InlineImage(tpl, str(png), width=Mm(165)),
        "variantes": _fmt(rel.sort_values(["sample_id", "gen"]),
                          {"posicion": "{:,.0f}", "vaf": "{:.2f}", "profundidad": "{:.0f}"}),
        "hallazgos": hallazgos.sort_values(["nivel", "sample_id"]).to_dict("records"),
        "n_errores": int((hallazgos["nivel"] == "ERROR").sum()),
        "n_advertencias": int((hallazgos["nivel"] == "WARN").sum()),
    }
    tpl.render(contexto, autoescape=True)
    docx_path = salida / f"Reporte_{corrida}.docx"
    tpl.save(docx_path)

    log_path = salida / f"{corrida}_validacion.csv"
    hallazgos.to_csv(log_path, index=False, encoding="utf-8-sig")
    return {"reporte": docx_path, "log": log_path, "grafico": png, "fuente_resumen": fuente}
