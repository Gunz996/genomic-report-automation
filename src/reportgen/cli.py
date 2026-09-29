"""Uso: python -m reportgen.cli data/ejemplo --corrida RUN-2609 --salida output"""
import argparse
import sys
from pathlib import Path

import yaml

from .loader import cargar_corrida
from .report import generar_reporte
from .validate import ErrorEstructura, validar

RAIZ = Path(__file__).resolve().parents[2]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Genera el reporte técnico de una corrida.")
    ap.add_argument("carpeta", help="Carpeta con samplesheet, qc_metrics y variants (.csv/.xlsx)")
    ap.add_argument("--corrida", required=True, help="Identificador de la corrida")
    ap.add_argument("--salida", default=str(RAIZ / "output"))
    ap.add_argument("--reglas", default=str(RAIZ / "config" / "rules.yaml"))
    ap.add_argument("--plantilla", default=str(RAIZ / "templates" / "plantilla_reporte.docx"))
    ap.add_argument("--laboratorio", default="Laboratorio de Genómica")
    a = ap.parse_args(argv)

    reglas = yaml.safe_load(Path(a.reglas).read_text(encoding="utf-8"))
    try:
        datos = cargar_corrida(a.carpeta)
        hallazgos, estado = validar(datos, reglas)
    except (FileNotFoundError, ErrorEstructura) as e:
        print(f"[DETENIDO] {e}", file=sys.stderr)
        return 2

    print(f"Validación: {(hallazgos.nivel == 'ERROR').sum()} errores, {(hallazgos.nivel == 'WARN').sum()} advertencias")
    print(estado["estado"].value_counts().to_string())

    res = generar_reporte(a.corrida, datos, estado, hallazgos, reglas, a.plantilla, a.salida, a.laboratorio)
    print(f"Resumen: {res['fuente_resumen']}")
    print(f"Reporte: {res['reporte']}\nLog:     {res['log']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
