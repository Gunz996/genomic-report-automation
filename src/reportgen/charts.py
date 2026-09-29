"""Gráficos que se insertan en el reporte."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

COLORES = {"APTA": "#2E7D32", "APTA CON OBSERVACIONES": "#F9A825", "NO APTA": "#C62828"}


def grafico_cobertura(qc, estado, umbral: float, destino: Path) -> Path:
    df = qc.merge(estado, on="sample_id", how="inner").sort_values("sample_id")
    fig, ax = plt.subplots(figsize=(7.5, 3.2), dpi=150)
    ax.bar(df["sample_id"], df["cobertura_media"], color=df["estado"].map(COLORES))
    ax.axhline(umbral, ls="--", lw=1, color="#555")
    ax.text(-0.45, umbral + 5, f"mínimo {umbral:g}x", va="bottom", ha="left", fontsize=7, color="#555",
            bbox=dict(fc="white", ec="none", pad=1), zorder=5)
    ax.set_ylabel("Cobertura media (x)", fontsize=8)
    ax.tick_params(axis="x", labelrotation=60, labelsize=7)
    ax.tick_params(axis="y", labelsize=7)
    ax.spines[["top", "right"]].set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in COLORES.values()]
    ax.legend(handles, COLORES.keys(), fontsize=7, frameon=False, loc="upper left", ncol=3,
              bbox_to_anchor=(0, 1.15))
    fig.tight_layout()
    fig.savefig(destino)
    plt.close(fig)
    return destino
