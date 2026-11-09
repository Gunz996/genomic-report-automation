# Diagrama del pipeline bioinformático (aguas arriba)

Este repositorio **no** procesa lecturas: parte de tres tablas ya generadas. El diagrama muestra el pipeline
bioinformático típico de un **panel de genes por captura (germinal, short-read Illumina)** que produce esas
tablas, y de qué paso sale cada columna que luego valida `config/rules.yaml`.

> Las herramientas indicadas son las de uso habitual (GATK Best Practices). Cada laboratorio puede usar
> equivalentes (DRAGEN, DeepVariant, ANNOVAR, etc.); lo importante es que la salida tenga las mismas columnas.

```mermaid
flowchart TD
    %% ---------- Laboratorio húmedo ----------
    subgraph WET["🧪 Laboratorio"]
        M["Muestra<br/>(sangre / saliva / tejido)"]
        D["Extracción de ADN<br/>+ cuantificación"]
        LB["Preparación de librería<br/>+ captura del panel (50 genes)"]
        SQ["Secuenciación<br/>Illumina (paired-end)"]
        M --> D --> LB --> SQ
    end

    %% ---------- Primario ----------
    subgraph P1["1 · Análisis primario"]
        BCL[/"BCL<br/>(señal del secuenciador)"/]
        DMX["Demultiplexado<br/>bcl-convert / bcl2fastq"]
        FQ[/"FASTQ por muestra<br/>R1 + R2"/]
        BCL --> DMX --> FQ
    end
    SQ --> BCL

    %% ---------- Secundario ----------
    subgraph P2["2 · Análisis secundario"]
        QC1["QC de lecturas<br/>FastQC · MultiQC"]
        TR["Recorte de adaptadores<br/>y bases de baja calidad<br/>fastp / Trimmomatic"]
        AL["Alineamiento al genoma<br/>BWA-MEM → GRCh38"]
        BAM[/"BAM ordenado<br/>+ índice"/]
        DUP["Marcado de duplicados<br/>Picard MarkDuplicates"]
        BQ["Recalibración de calidad<br/>GATK BQSR"]
        COV["Métricas de captura<br/>Picard HsMetrics · mosdepth<br/>(sobre BED del panel)"]
        VC["Llamado de variantes<br/>GATK HaplotypeCaller"]
        VF["Filtrado de variantes<br/>calidad · profundidad · strand bias"]
        VCF[/"VCF filtrado"/]
        QC1 --> TR --> AL --> BAM --> DUP --> BQ
        BQ --> COV
        BQ --> VC --> VF --> VCF
    end
    FQ --> QC1

    %% ---------- Terciario ----------
    subgraph P3["3 · Análisis terciario"]
        AN["Anotación<br/>Ensembl VEP / ANNOVAR<br/>gen · HGVS · consecuencia"]
        DB["Bases de datos<br/>ClinVar · gnomAD · predictores in silico"]
        AC["Clasificación ACMG/AMP<br/>InterVar / Franklin<br/>+ revisión del curador"]
        AN --> AC
        DB --> AN
        DB --> AC
    end
    VCF --> AN

    %% ---------- Tablas que entran al repo ----------
    subgraph OUT["📄 Tablas de entrada de este repo (data/)"]
        T0[/"samplesheet.csv<br/>sample_id · cliente · tipo_muestra<br/>panel · fecha_recepcion"/]
        T1[/"qc_metrics.csv<br/>total_reads · pct_q30 · pct_gc<br/>pct_duplicados · cobertura_media<br/>pct_bases_20x"/]
        T2[/"variants.csv<br/>gen · cromosoma · posicion · ref · alt<br/>hgvs_c · vaf · profundidad · clasificacion"/]
    end

    LIMS[("LIMS<br/>registro de muestras")] --> T0
    M -.-> LIMS

    QC1 -- "total_reads · pct_q30 · pct_gc" --> T1
    DUP -- "pct_duplicados" --> T1
    COV -- "cobertura_media · pct_bases_20x" --> T1
    VCF -- "cromosoma · posicion · ref · alt<br/>vaf (AD/DP) · profundidad (DP)" --> T2
    AN -- "gen · hgvs_c" --> T2
    AC -- "clasificacion" --> T2

    REPO(["▶ genomic-report-automation<br/>validación → resumen → reporte Word<br/>(ver diagrama_flujo.md)"])
    T0 & T1 & T2 --> REPO

    %% ---------- Estilos ----------
    classDef wet fill:#FFF3E0,stroke:#E65100
    classDef file fill:#E3F2FD,stroke:#1565C0
    classDef repo fill:#1F3A5F,color:#fff,stroke:#0D1F33
    class M,D,LB,SQ wet
    class T0,T1,T2 file
    class REPO repo
```

## De dónde sale cada métrica que valida el repo

| Columna | Paso / herramienta | Qué indica | Umbral en `rules.yaml` |
|---|---|---|---|
| `total_reads` | FastQC / demultiplexado | Lecturas totales de la muestra | fail < 1 M · warn < 2 M |
| `pct_q30` | FastQC / bcl-convert | % de bases con calidad Phred ≥ 30 (error ≤ 0,1 %) | fail < 75 · warn < 85 |
| `pct_gc` | FastQC | Contenido GC; fuera de rango sugiere contaminación o sesgo de captura | warn fuera de 35–55 |
| `pct_duplicados` | Picard MarkDuplicates | Lecturas PCR/ópticas duplicadas; alto = baja complejidad de librería | fail > 40 · warn > 30 |
| `cobertura_media` | Picard HsMetrics / mosdepth | Profundidad media sobre las regiones del panel | fail < 100x · warn < 150x |
| `pct_bases_20x` | Picard HsMetrics / mosdepth | % de bases objetivo con ≥ 20x (uniformidad) | fail < 90 · warn < 95 |
| `profundidad` | VCF (campo `DP`) | Lecturas que cubren la variante | warn < 20 |
| `vaf` | VCF (`AD` alt / `DP`) | Fracción alélica; ~0,5 heterocigota, ~1 homocigota | error fuera de [0, 1] |
| `gen`, `hgvs_c` | VEP / ANNOVAR | Gen y nomenclatura HGVS de la variante | — |
| `clasificacion` | ACMG/AMP + curador | Benigna … Patogénica | debe ser categoría ACMG |
