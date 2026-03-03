# EIA Document Extraction Pipeline

A map-reduce pipeline that extracts structured environmental data from Environmental Impact Assessment (EIA) PDF reports using LLMs.

Given a multi-hundred-page EIA report, the pipeline splits it into batches, extracts structured data (species, impacts, mitigations, key findings), deduplicates and aggregates in Python, then generates a consolidated narrative report with priority-scenario recommendations.

## What it produces

From a single PDF, you get:

- **`consolidated_report.json`** — machine-readable structured data: species records with conservation status, impact assessments by severity, mitigation measures, qualitative key findings, and summary statistics
- **`consolidated_report.md`** — human-readable markdown report with executive summary, conclusion with three priority-scenario recommendations (high nature / balanced / high development), and tables for all extracted data

## Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** — Python package manager
- **PydanticAI Gateway API key** — get one at https://app.pydantic.dev/

## Quick start

```bash
# Clone the repo
git clone <repo-url>
cd ediscovery

# Install dependencies
uv sync

# Configure your API key
cp .env.example .env
# Edit .env and add your PYDANTIC_AI_GATEWAY_API_KEY

# Place your EIA PDF(s) in the project directory, then run:
uv run python agents.py
```

Output files (`consolidated_report.json` and `consolidated_report.md`) will appear in the current directory.

## Configuration

All configuration is via the `.env` file (or environment variables):

| Variable | Default | Description |
|---|---|---|
| `PYDANTIC_AI_GATEWAY_API_KEY` | *(required)* | Your PydanticAI Gateway API key |
| `MODEL` | `gateway/anthropic:claude-sonnet-4-5` | LLM model to use ([model options](https://ai.pydantic.dev/models/)) |
| `BATCH_SIZE` | `20` | Pages per batch (larger = fewer API calls, but may lose detail) |
| `MAX_CONCURRENT` | `5` | Max concurrent API calls during map phase |
| `PDF_GLOB` | `*.pdf` | Glob pattern to select which PDFs to process |
| `PDF_DIR` | `.` | Directory containing PDF files |
| `OUTPUT_DIR` | `.` | Directory for output files |

### Cost control

Each batch = 1 API call in the map phase, plus 1 API call for the reduce phase.

A 600-page PDF with `BATCH_SIZE=20` = 30 map calls + 1 reduce = **31 API calls total**.

To reduce costs:
- Increase `BATCH_SIZE` (e.g. 30 or 50) — fewer calls but coarser extraction
- Use `PDF_GLOB` to process only the main report (e.g. `PDF_GLOB=*Report.pdf` to skip appendices)

## Running with Docker

```bash
# Build
docker compose build

# Run (mount your PDFs into /data)
docker compose run --rm pipeline
```

PDFs go in `./pdfs/` and output appears in `./output/`. Configure via environment variables in `docker-compose.yml`.

## Project structure

```
agents.py          Main pipeline: PDF extraction, map/reduce agents, orchestration
models.py          Dataclasses: SpeciesRecord, ImpactAssessment, MitigationMeasure,
                   KeyFinding, BatchExtraction, ConsolidatedReport
prompts.py         System prompts for map (extraction) and reduce (synthesis) agents
format_report.py   Converts JSON output to formatted markdown
requirements.txt   Pinned dependencies
.env.example       Configuration template
Dockerfile         Container build
docker-compose.yml Container orchestration
agent_tests/       Test suite
```

## How it works

```
PDF(s) ──► Page extraction (pymupdf)
              │
              ▼
        Batch into groups of N pages
              │
              ▼
    ┌─── Map phase (concurrent) ───┐
    │  Batch 1 ──► LLM ──► JSON   │
    │  Batch 2 ──► LLM ──► JSON   │  N API calls
    │  ...                         │
    │  Batch N ──► LLM ──► JSON   │
    └──────────────────────────────┘
              │
              ▼
        Python aggregation
        (deduplicate, count, merge)
              │
              ▼
    ┌─── Reduce phase ────────────┐
    │  Aggregated data ──► LLM    │  1 API call
    │  ──► Executive summary      │
    │  ──► Conclusion + scenarios │
    └─────────────────────────────┘
              │
              ▼
        Python merges narrative
        with aggregated data lists
              │
              ▼
        consolidated_report.json
        consolidated_report.md
```

The LLM produces narrative (executive summary, conclusion with priority scenarios). Python owns all structured data lists and counts — this avoids the problem of LLMs struggling to copy large lists verbatim.

## Observability

The pipeline is instrumented with [Logfire](https://logfire.pydantic.dev/) for tracing PydanticAI agent calls. To enable:

```bash
uv pip install logfire
logfire auth
logfire projects use <your-project>
```

## Tests

```bash
PYTHONPATH=. uv run pytest agent_tests/ -v
```

## License

CC BY-NC-SA 4.0 — free for non-commercial use. Commercial use requires explicit permission. See [LICENSE](LICENSE) for details.
