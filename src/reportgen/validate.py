"""Validación de estructura, consistencia entre archivos y umbrales de QC."""
from dataclasses import dataclass, asdict

import pandas as pd


@dataclass
class Hallazgo:
    nivel: str        # ERROR | WARN
    archivo: str
    sample_id: str
    regla: str
    detalle: str


ETIQUETAS = {
    "qc_total_reads": "lecturas insuficientes",
    "qc_pct_q30": "calidad de bases baja (%Q30)",
    "qc_pct_duplicados": "duplicación alta",
    "qc_cobertura_media": "cobertura media insuficiente",
    "qc_pct_bases_20x": "uniformidad de cobertura baja (%≥20x)",
    "qc_pct_gc": "contenido GC fuera de rango",
    "vaf_rango": "VAF fuera de rango",
    "profundidad_baja": "profundidad baja en variante",
    "clasificacion": "clasificación no ACMG",
    "cromosoma": "cromosoma no válido",
    "alelos": "alelos ref/alt inválidos",
    "id_desconocido": "muestra no registrada",
    "id_duplicado": "muestra duplicada",
    "sin_qc": "sin métricas de QC",
    "tipo_numerico": "valor no numérico",
    "fila_duplicada": "fila duplicada",
}


class ErrorEstructura(Exception):
    """Falla que impide continuar (faltan columnas, archivo vacío)."""


def _estructura(datos: dict, reglas: dict) -> None:
    for nombre, cfg in reglas["archivos"].items():
        df = datos[nombre]
        if df.empty:
            raise ErrorEstructura(f"{nombre}: el archivo está vacío")
        faltan = set(cfg["columnas"]) - set(df.columns)
        if faltan:
            raise ErrorEstructura(f"{nombre}: faltan columnas {sorted(faltan)}")


def _tipos(datos: dict, reglas: dict, out: list) -> None:
    for nombre, cfg in reglas["archivos"].items():
        df = datos[nombre]
        for col in cfg.get("numericas", []):
            conv = pd.to_numeric(df[col], errors="coerce")
            malos = df[conv.isna() & df[col].notna()]
            for _, r in malos.iterrows():
                out.append(Hallazgo("ERROR", nombre, r["sample_id"], "tipo_numerico",
                                    f"{col}='{r[col]}' no es numérico"))
            df[col] = conv
        dup = df[df.duplicated(keep=False)]
        for sid in dup["sample_id"].unique():
            out.append(Hallazgo("WARN", nombre, sid, "fila_duplicada", "filas idénticas repetidas"))


def _consistencia(datos: dict, out: list) -> None:
    ss = datos["samplesheet"]
    ids = set(ss["sample_id"])
    for sid in ss.loc[ss["sample_id"].duplicated(), "sample_id"]:
        out.append(Hallazgo("ERROR", "samplesheet", sid, "id_duplicado", "sample_id repetido"))
    for nombre in ("qc_metrics", "variants"):
        for sid in sorted(set(datos[nombre]["sample_id"]) - ids):
            out.append(Hallazgo("ERROR", nombre, sid, "id_desconocido",
                                "sample_id no existe en samplesheet"))
    for sid in sorted(ids - set(datos["qc_metrics"]["sample_id"])):
        out.append(Hallazgo("ERROR", "qc_metrics", sid, "sin_qc", "muestra sin métricas de QC"))


def _n(x) -> str:
    return f"{x:,.0f}" if float(x).is_integer() else f"{x:,.1f}"


def _umbral(valor, cfg) -> str | None:
    if pd.isna(valor):
        return "ERROR"
    if "fail_min" in cfg and valor < cfg["fail_min"]:
        return "ERROR"
    if "fail_max" in cfg and valor > cfg["fail_max"]:
        return "ERROR"
    if "warn_min" in cfg and valor < cfg["warn_min"]:
        return "WARN"
    if "warn_max" in cfg and valor > cfg["warn_max"]:
        return "WARN"
    return None


def _qc(datos: dict, reglas: dict, out: list) -> None:
    for _, r in datos["qc_metrics"].iterrows():
        for metrica, cfg in reglas["qc"].items():
            nivel = _umbral(r[metrica], cfg)
            if nivel:
                clave = "fail" if nivel == "ERROR" else "warn"
                lim = cfg.get(f"{clave}_min", cfg.get(f"{clave}_max"))
                signo = "<" if f"{clave}_min" in cfg and r[metrica] < lim else ">"
                out.append(Hallazgo(nivel, "qc_metrics", r["sample_id"], f"qc_{metrica}",
                                    f"{ETIQUETAS[f'qc_{metrica}']}: {metrica} = {_n(r[metrica])} {signo} {_n(lim)}"))


def _variantes(datos: dict, reglas: dict, out: list) -> None:
    cfg = reglas["variantes"]
    bases = set(cfg["bases_validas"])
    lo, hi = cfg["vaf_rango"]
    for _, r in datos["variants"].iterrows():
        sid, tag = r["sample_id"], f"{r['gen']} {r['hgvs_c']}"
        if not (lo <= r["vaf"] <= hi):
            out.append(Hallazgo("ERROR", "variants", sid, "vaf_rango", f"{tag}: VAF={r['vaf']} fuera de [{lo},{hi}]"))
        if r["profundidad"] < cfg["profundidad_min"]:
            out.append(Hallazgo("WARN", "variants", sid, "profundidad_baja",
                                f"{tag}: profundidad={int(r['profundidad'])} < {cfg['profundidad_min']}"))
        if str(r["cromosoma"]) not in cfg["cromosomas_validos"]:
            out.append(Hallazgo("ERROR", "variants", sid, "cromosoma", f"{tag}: cromosoma '{r['cromosoma']}' no válido"))
        if not set(str(r["ref"]) + str(r["alt"])) <= bases or r["ref"] == r["alt"]:
            out.append(Hallazgo("ERROR", "variants", sid, "alelos", f"{tag}: ref/alt inválidos ({r['ref']}>{r['alt']})"))
        if r["clasificacion"] not in cfg["clasificaciones_validas"]:
            out.append(Hallazgo("ERROR", "variants", sid, "clasificacion",
                                f"{tag}: clasificación '{r['clasificacion']}' no es ACMG"))


def validar(datos: dict, reglas: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (hallazgos, estado_por_muestra). Lanza ErrorEstructura si no se puede continuar."""
    _estructura(datos, reglas)
    out: list[Hallazgo] = []
    _tipos(datos, reglas, out)
    _consistencia(datos, out)
    _qc(datos, reglas, out)
    _variantes(datos, reglas, out)

    hallazgos = pd.DataFrame([asdict(h) for h in out],
                             columns=["nivel", "archivo", "sample_id", "regla", "detalle"])

    estado = datos["samplesheet"][["sample_id"]].copy()

    def _estado(sid):
        h = hallazgos[hallazgos["sample_id"] == sid]
        if (h["nivel"] == "ERROR").any():
            return "NO APTA"
        if (h["nivel"] == "WARN").any():
            return "APTA CON OBSERVACIONES"
        return "APTA"

    estado["estado"] = estado["sample_id"].map(_estado)
    return hallazgos, estado
