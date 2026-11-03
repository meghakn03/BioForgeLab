**Tech stack:** Python, Biopython, scikit-learn, FastAPI, React, TypeScript, PostgreSQL, SQLAlchemy, MLflow, Plotly, Docker Compose

# BioForge Lab

An end-to-end computational biology workspace: FASTA analysis, labelled protein data ingestion, solubility regression, reproducible evaluation, candidate comparison, and a polished React dashboard.

## Start the entire app

Prerequisites: Node.js / npm and a running Docker Desktop (or Docker Engine with Compose). The first start needs internet access to build the images.

```sh
npm start
```

This single command builds and starts **the React frontend, FastAPI backend, PostgreSQL, and MLflow**, then waits for all services to be healthy. No local Python environment or separate terminals are needed. Services keep running in the background.

- App: **http://localhost:8002**
- API documentation: **http://localhost:8002/docs**
- MLflow: **http://localhost:5000**

Run `npm stop` to stop the entire stack, or `npm run logs` to follow its logs. Data and models persist across restarts. Override the app port with `APP_PORT=8003 npm start`. Local database credentials are for development only.

### Optional lightweight local mode

With Python 3.9+ and Node.js 20.19+ (or 22.12+), run `npm run start:local`. This installs dependencies and runs the UI and API using SQLite, without the Docker services. It prints its selected URL (first free port from 8000 through 8020). Ctrl+C stops this local server.

## Use the platform

1. Click **Explore the demo workspace** to generate 160 explicitly synthetic labelled proteins and a starter sequence collection.
2. Create an experiment. Choose Random Forest or Extra Trees, a fixed seed, tree count, and held-out fraction.
3. Inspect held-out MAE/RMSE/R², baseline performance, 95% bootstrap MAE interval, observed-versus-predicted scatter, and feature importance. Export the complete run as JSON.
4. Train another model with the same dataset, seed, and hold-out fraction. Compare both runs; the UI checks that held-out IDs match.
5. Upload protein FASTA and predict candidates. The UI marks exact dataset overlap and reports ensemble disagreement separately from calibrated uncertainty.
6. Upload DNA FASTA for GC content, base composition, frame +1 codon usage, and translation. Small illustrative uploads are included in `data/examples/`.
7. In Datasets, click **Import public eSOL data** to download the pinned, checksum-verified experimental training partition (2,481 proteins). The importer converts fraction labels to percentages, preserves upstream partition provenance, and records that homology clusters are absent. Or import a measured protein-solubility CSV with a source citation and assay context. Format:

```csv
id,sequence,solubility,group
protein_001,MKTAYIAKQRQISFVKSHFSRQDILDLWIYHTQGYFP,65.2,cluster_01
```

Supply at least 12 unique canonical protein sequences and four groups. `solubility` is a percentage from 0 to 100. `group` is optional but external homology clusters are necessary for credible homology-aware evaluation. The platform does not automatically cluster homologs. See [data policy](data/README.md) and [scientific case study](docs/CASE_STUDY.md).

The research assistant is an optional deterministic summary of stored run evidence, with provenance references. It has no LLM dependency and does not generate open-ended scientific answers.

## Architecture

- **React + TypeScript + Vite**, Plotly charts, Lucide icons; responsive, accessible controls.
- **FastAPI**, Pydantic validation and OpenAPI; Biopython sequence analysis.
- **scikit-learn** forests and mean baseline; group hold-out, bootstrap MAE, persisted joblib artifacts.
- **SQLAlchemy** JSON run/dataset/analysis records; SQLite locally, PostgreSQL in Compose.
- **MLflow** optional via `MLFLOW_TRACKING_URI`; failure preserves local artifacts and records an explicit tracking status.
- **pytest** integration and biology checks; GitHub Actions builds frontend and tests backend.

## Development & checks

Test the running full stack:

```sh
docker compose exec -T app python -m pytest backend/tests -q
```

For local development, run `npm run start:local` once to install dependencies, then:

```sh
npm test
npm run build
# Optional hot reload: run these in separate terminals
.venv/bin/python -m uvicorn backend.app.main:app --reload
npm --prefix frontend run dev
```

Vite proxies `/api` to FastAPI on port 8000. Optional environment variables: `DATABASE_URL`, `BIOFORGE_DATA_DIR`, `MLFLOW_TRACKING_URI`, and `PORT` (single-command local server).

## Boundaries

The bundled demonstration is not a public experimental benchmark. No pretrained protein language model or PyTorch model is claimed; this release deliberately implements a transparent descriptor-based solubility regression baseline. Uploaded dataset source declarations are researcher supplied. The public importer verifies its pinned mirror file checksum; it does not independently verify the experimental assay. No authentication or multi-user isolation is included: keep the app on localhost / a trusted development environment. Synchronous training and upload caps suit a portfolio-scale deployment; a production system needs authentication, background workers, quotas, migration tooling, and validated external evaluation.
