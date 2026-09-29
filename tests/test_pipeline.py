from pathlib import Path

import pandas as pd
import pytest
import yaml

from reportgen.ai import _cifras_ok, redactar_resumen
from reportgen.loader import cargar_corrida
from reportgen.report import generar_reporte
from reportgen.validate import ErrorEstructura, validar

RAIZ = Path(__file__).resolve().parents[1]
REGLAS = yaml.safe_load((RAIZ / "config" / "rules.yaml").read_text(encoding="utf-8"))
EJEMPLO = RAIZ / "data" / "ejemplo"


@pytest.fixture
def datos():
    return cargar_corrida(EJEMPLO)


def test_estados_esperados(datos):
    hallazgos, estado = validar(datos, REGLAS)
    e = dict(zip(estado.sample_id, estado.estado))
    assert e["BS-2609-05"] == "NO APTA"                  # bajo rendimiento
    assert e["BS-2609-09"] == "NO APTA"                  # Q30 bajo
    assert e["BS-2609-11"] == "APTA CON OBSERVACIONES"   # duplicados altos
    assert e["BS-2609-01"] == "APTA"


def test_detecta_errores_de_datos(datos):
    hallazgos, _ = validar(datos, REGLAS)
    reglas = set(hallazgos.regla)
    assert {"id_desconocido", "vaf_rango", "clasificacion", "profundidad_baja"} <= reglas


def test_columna_faltante_detiene(datos):
    datos["qc_metrics"] = datos["qc_metrics"].drop(columns=["pct_q30"])
    with pytest.raises(ErrorEstructura):
        validar(datos, REGLAS)


def test_valor_no_numerico(datos):
    datos["qc_metrics"].loc[0, "total_reads"] = "N/A"
    hallazgos, estado = validar(datos, REGLAS)
    assert (hallazgos.regla == "tipo_numerico").any()
    assert estado.set_index("sample_id").loc["BS-2609-01", "estado"] == "NO APTA"


def test_control_anti_alucinacion():
    hechos = {"total_muestras": 12, "estados": {"APTA": 6}}
    assert _cifras_ok("Se procesaron 12 muestras, 6 aptas.", hechos)
    assert not _cifras_ok("Se procesaron 14 muestras.", hechos)


def test_resumen_sin_api(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    hechos = {"corrida": "R1", "panel": "P", "total_muestras": 2, "estados": {"APTA": 2},
              "causas_rechazo": [], "variantes_relevantes": {}}
    texto, fuente = redactar_resumen(hechos)
    assert "R1" in texto and fuente == "Plantilla automática"


def test_reporte_end_to_end(datos, tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    hallazgos, estado = validar(datos, REGLAS)
    res = generar_reporte("TEST", datos, estado, hallazgos, REGLAS,
                          RAIZ / "templates" / "plantilla_reporte.docx", tmp_path)
    assert res["reporte"].exists() and res["reporte"].stat().st_size > 10_000
    assert len(pd.read_csv(res["log"])) == len(hallazgos)
