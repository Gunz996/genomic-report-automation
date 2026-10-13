# Automatización de reportes técnicos de genómica

Pipeline en Python que toma los archivos de una corrida de secuenciación, los valida, redacta el resumen ejecutivo con apoyo de IA y genera el reporte final en Word sobre una plantilla.

Es una demo con datos sintéticos: 12 muestras de un panel hereditario de 50 genes. Ejemplo de salida: [`docs/ejemplo_Reporte_RUN-2609.pdf`](docs/ejemplo_Reporte_RUN-2609.pdf).

## Flujo

```
samplesheet.csv ─┐
qc_metrics.csv  ─┼─► 1. Carga ─► 2. Validación ─► 3. Resumen IA ─► 4. Plantilla Word ─► Reporte.docx
variants.csv    ─┘      (CSV/XLSX)   (reglas YAML)     (con control)      (docxtpl)          + log de validación
```

1. **Carga** (`loader.py`): lee CSV o Excel y normaliza columnas y espacios.
2. **Validación** (`validate.py`): revisa en tres niveles.
   - Estructura: columnas obligatorias y archivos vacíos. Si falla, el proceso se detiene.
   - Consistencia entre archivos: muestras que no están registradas, que están duplicadas o que no tienen QC.
   - Reglas de negocio: umbrales de QC (lecturas, %Q30, duplicación, cobertura, %≥20x, GC) y reglas de variantes (VAF en [0,1], profundidad mínima, cromosoma, alelos, clasificación ACMG).

   A cada muestra se le asigna uno de tres estados: **APTA**, **APTA CON OBSERVACIONES** o **NO APTA**.
3. **Resumen con IA** (`ai.py`): Claude redacta el resumen ejecutivo a partir de un JSON con cifras ya validadas.
   - La IA **no calcula ni clasifica**. Solo redacta.
   - **Control anti-alucinación**: si el texto trae una cifra que no está en los datos, se descarta y se usa el texto determinístico.
   - Si no hay `ANTHROPIC_API_KEY`, funciona igual con el texto de respaldo.
   - El reporte indica siempre qué fuente se usó.
4. **Reporte** (`report.py`): llena la plantilla Word con tablas de QC, un gráfico de cobertura, las variantes P/LP de las muestras aptas, las observaciones de validación y un bloque de firmas.

## Uso

```bash
pip install -r requirements.txt
python scripts/crear_plantilla.py                 # genera la plantilla de ejemplo
PYTHONPATH=src python -m reportgen.cli data/ejemplo --corrida RUN-2609

# Opcional: resumen redactado por IA
export ANTHROPIC_API_KEY=...
PYTHONPATH=src python -m reportgen.cli data/ejemplo --corrida RUN-2609
```

En Windows (PowerShell): `$env:PYTHONPATH="src"; python -m reportgen.cli data\ejemplo --corrida RUN-2609`

El reporte, el log de validación (CSV) y el gráfico se guardan en `output/`.

## Adaptar a las plantillas del laboratorio

- **Umbrales y reglas**: se editan en `config/rules.yaml`, sin tocar el código.
- **Plantilla**: se abre la plantilla Word existente y se escriben las etiquetas `{{ corrida }}`, `{{ resumen }}`, `{%tr for r in qc %}` ... `{%tr endfor %}`, etc., donde corresponda. Se conservan el formato, el logo y los encabezados originales.
- **Nuevas fuentes** (salidas de FastQC/MultiQC, VCF, LIMS): se agrega un lector en `loader.py` que devuelva un DataFrame con las mismas columnas.

## Tests

```bash
PYTHONPATH=src pytest -q
```

Los tests cubren los estados por muestra, la detección de errores, las columnas faltantes, los valores no numéricos, el control anti-alucinación, el modo sin API y la generación del reporte de principio a fin.

## Estructura

```
config/rules.yaml          umbrales y reglas
data/ejemplo/              datos sintéticos (incluyen errores a propósito)
scripts/crear_plantilla.py genera la plantilla Word de ejemplo
src/reportgen/             loader, validate, ai, charts, report, cli
templates/                 plantilla .docx
tests/                     pytest
```

## Financiamiento

Aceleradoras, fondos y créditos de nube/IA para salud y biotecnología: [`docs/financiamiento_y_aceleradoras.md`](docs/financiamiento_y_aceleradoras.md).

---
Autor: Gonzalo Zambrano, Ingeniero en Biotecnología y Analista de Datos.
