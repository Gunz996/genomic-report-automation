"""Carga de archivos de entrada (CSV o Excel)."""
from pathlib import Path

import pandas as pd

ARCHIVOS = ("samplesheet", "qc_metrics", "variants")


def _leer(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path, dtype=str)
    return pd.read_csv(path, dtype=str)


def cargar_corrida(carpeta: str | Path) -> dict[str, pd.DataFrame]:
    """Busca samplesheet, qc_metrics y variants (.csv o .xlsx) en la carpeta."""
    carpeta = Path(carpeta)
    datos = {}
    for nombre in ARCHIVOS:
        candidatos = [carpeta / f"{nombre}{ext}" for ext in (".csv", ".xlsx", ".xls")]
        encontrado = next((p for p in candidatos if p.exists()), None)
        if encontrado is None:
            raise FileNotFoundError(f"Falta el archivo '{nombre}' (.csv o .xlsx) en {carpeta}")
        df = _leer(encontrado)
        df.columns = [c.strip().lower() for c in df.columns]
        datos[nombre] = df.apply(lambda s: s.str.strip() if s.dtype == object else s)
    return datos
