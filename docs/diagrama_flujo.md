# Diagrama de flujo del pipeline

Flujo completo de `python -m reportgen.cli <carpeta> --corrida <ID>`, desde los archivos de entrada hasta el reporte Word.
GitHub dibuja el diagrama automáticamente (Mermaid).

```mermaid
flowchart TD
    %% ---------- Entradas ----------
    subgraph IN["📥 Entradas"]
        SS[/"samplesheet<br/>(.csv / .xlsx)"/]
        QC[/"qc_metrics<br/>(.csv / .xlsx)"/]
        VA[/"variants<br/>(.csv / .xlsx)"/]
        RU[/"config/rules.yaml<br/>umbrales y reglas"/]
        TP[/"templates/<br/>plantilla_reporte.docx"/]
    end

    CLI(["▶ cli.py<br/>lee argumentos y reglas YAML"])
    RU --> CLI

    %% ---------- 1. Carga ----------
    subgraph S1["1 · Carga — loader.py"]
        L1["cargar_corrida()<br/>busca los 3 archivos"]
        L2["Normaliza columnas<br/>(minúsculas) y espacios"]
        L1 --> L2
    end
    SS & QC & VA --> L1
    CLI --> L1
    L1 -- "falta un archivo" --> STOP

    %% ---------- 2. Validación ----------
    subgraph S2["2 · Validación — validate.py"]
        V1{"Estructura<br/>¿columnas obligatorias<br/>y archivos no vacíos?"}
        V2["Tipos<br/>valores no numéricos · filas duplicadas"]
        V3["Consistencia entre archivos<br/>ID desconocido · ID duplicado · sin QC"]
        V4["Umbrales de QC<br/>lecturas · %Q30 · %dup · cobertura · %≥20x · GC"]
        V5["Reglas de variantes<br/>VAF ∈ [0,1] · profundidad · cromosoma · alelos · ACMG"]
        H[("Hallazgos<br/>ERROR / WARN")]
        E{"Estado por muestra"}
        V1 -- sí --> V2 --> V3 --> V4 --> V5 --> H --> E
    end
    L2 --> V1
    V1 -- "no (ErrorEstructura)" --> STOP

    STOP[["⛔ DETENIDO<br/>exit code 2"]]

    E -- "≥1 ERROR" --> NA["🔴 NO APTA"]
    E -- "solo WARN" --> AO["🟡 APTA CON OBSERVACIONES"]
    E -- "sin hallazgos" --> AP["🟢 APTA"]

    %% ---------- 3. Resumen IA ----------
    subgraph S3["3 · Resumen ejecutivo — report.py + ai.py"]
        F["construir_hechos()<br/>JSON con cifras validadas:<br/>estados, causas de rechazo,<br/>variantes P/LP en muestras aptas"]
        K{"¿Hay<br/>ANTHROPIC_API_KEY?"}
        C["Claude redacta el resumen<br/>(solo redacta, no calcula)"]
        X{"¿Respondió sin error?"}
        CK{"Control anti-alucinación<br/>¿todas las cifras del texto<br/>están en el JSON?"}
        TB["Texto determinístico<br/>(plantilla automática)"]
        TI["Texto IA<br/>— requiere revisión"]
        F --> K
        K -- sí --> C --> X
        X -- sí --> CK
        X -- "no (red, clave inválida…)" --> TB
        K -- no --> TB
        CK -- sí --> TI
        CK -- no --> TB
    end
    NA & AO & AP --> F
    H --> F

    %% ---------- 4. Reporte ----------
    subgraph S4["4 · Reporte — report.py + charts.py"]
        G["grafico_cobertura()<br/>barras por muestra coloreadas<br/>por estado + línea de umbral"]
        T["Tablas de QC, variantes P/LP<br/>y observaciones de validación"]
        R["docxtpl renderiza la plantilla<br/>(+ fuente del resumen y firmas)"]
        G --> R
        T --> R
    end
    TB & TI --> R
    E --> G
    E --> T
    H --> T
    TP --> R

    %% ---------- Salidas ----------
    subgraph OUT["📤 Salidas — output/"]
        O1[/"Reporte_&lt;corrida&gt;.docx"/]
        O2[/"&lt;corrida&gt;_validacion.csv<br/>log de hallazgos"/]
        O3[/"&lt;corrida&gt;_cobertura.png"/]
    end
    R --> O1
    H --> O2
    G --> O3

    %% ---------- Estilos ----------
    classDef stop fill:#C62828,color:#fff,stroke:#8E0000
    classDef ok fill:#2E7D32,color:#fff,stroke:#1B5E20
    classDef warn fill:#F9A825,color:#000,stroke:#C17900
    classDef ia fill:#E8EAF6,stroke:#3949AB
    class STOP,NA stop
    class AP ok
    class AO warn
    class C,TI ia
```

## Cómo leerlo

| Etapa | Módulo | Qué hace | Si falla |
|---|---|---|---|
| 1. Carga | `loader.py` | Lee los 3 archivos (CSV o Excel) y normaliza columnas | Falta un archivo → **se detiene** |
| 2. Validación | `validate.py` | Estructura → tipos → consistencia → QC → variantes | Falla de estructura → **se detiene**; el resto se registra como hallazgo |
| Estado | `validate.py` | ERROR → NO APTA · solo WARN → APTA CON OBS. · nada → APTA | — |
| 3. Resumen | `report.py`, `ai.py` | Claude redacta a partir de cifras ya validadas | Sin clave, error de API o cifra inventada → texto determinístico |
| 4. Reporte | `report.py`, `charts.py` | Llena la plantilla Word con tablas, gráfico y firmas | — |

Los umbrales del paso 2 se configuran en [`config/rules.yaml`](../config/rules.yaml).
