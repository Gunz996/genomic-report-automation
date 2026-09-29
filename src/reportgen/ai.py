"""Redacción asistida por IA del resumen ejecutivo.

La IA solo redacta texto a partir de datos ya validados; no calcula ni clasifica.
Si no hay ANTHROPIC_API_KEY, o si la respuesta menciona cifras que no están en los
datos, se usa un texto determinístico. El reporte indica qué fuente se usó.
"""
import json
import os
import re

MODELO = os.getenv("REPORTGEN_MODEL", "claude-sonnet-5-5")

PROMPT = """Eres analista de un laboratorio de genómica. Redacta en español un resumen
ejecutivo técnico (máximo 150 palabras, un solo párrafo, sin viñetas) de la corrida
descrita en el JSON. Reglas:
- Usa solo cifras que aparezcan en el JSON; no inventes datos ni interpretaciones clínicas.
- Menciona cuántas muestras son aptas, aptas con observaciones y no aptas, y la causa principal de rechazo.
- Menciona las variantes patogénicas o probablemente patogénicas por gen.
- Tono formal, tercera persona.

JSON:
{hechos}"""


def _texto_base(h: dict) -> str:
    e = h["estados"]
    partes = [
        f"La corrida {h['corrida']} incluyó {h['total_muestras']} muestras del {h['panel']}.",
        f"{e.get('APTA', 0)} muestras resultaron aptas, {e.get('APTA CON OBSERVACIONES', 0)} aptas con "
        f"observaciones y {e.get('NO APTA', 0)} no aptas para reporte.",
    ]
    if h["causas_rechazo"]:
        partes.append("Las causas de rechazo fueron: " + ", ".join(h["causas_rechazo"]) + ".")
    if h["variantes_relevantes"]:
        det = ", ".join(f"{g} ({n})" for g, n in h["variantes_relevantes"].items())
        partes.append(f"Se identificaron variantes patogénicas o probablemente patogénicas en: {det}.")
    else:
        partes.append("No se identificaron variantes patogénicas o probablemente patogénicas en las muestras aptas.")
    partes.append("Los resultados deben ser revisados y firmados por el responsable técnico.")
    return " ".join(partes)


def _cifras_ok(texto: str, hechos: dict) -> bool:
    """Toda cifra del texto debe existir en los hechos (control anti-alucinación)."""
    permitidas = set(re.findall(r"\d+(?:[.,]\d+)?", json.dumps(hechos, ensure_ascii=False)))
    usadas = set(re.findall(r"\d+(?:[.,]\d+)?", texto))
    return usadas <= permitidas


def redactar_resumen(hechos: dict) -> tuple[str, str]:
    """Devuelve (texto, fuente). fuente: 'IA (<modelo>)' o 'Plantilla automática'."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return _texto_base(hechos), "Plantilla automática"
    try:
        import anthropic

        cliente = anthropic.Anthropic()
        resp = cliente.messages.create(
            model=MODELO,
            max_tokens=500,
            messages=[{"role": "user", "content": PROMPT.format(
                hechos=json.dumps(hechos, ensure_ascii=False, indent=2))}],
        )
        texto = resp.content[0].text.strip()
        if not _cifras_ok(texto, hechos):
            return _texto_base(hechos), "Plantilla automática (IA descartada: cifras no verificables)"
        return texto, f"IA ({MODELO}) — requiere revisión"
    except Exception as exc:  # sin red, clave inválida, etc.
        return _texto_base(hechos), f"Plantilla automática (IA no disponible: {type(exc).__name__})"
