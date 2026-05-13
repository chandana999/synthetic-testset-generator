
<h1 align="center">Synthetic test set generation (RAGAS)</h1>



---

## Web application (API + UI)

An enterprise-style console calls a local **FastAPI** backend that wraps two RAGAS flows aligned with the assignment notebook:

| Mode | RAGAS behavior |
|------|----------------|
| **Structured (knowledge graph)** | Explicit knowledge graph, default transforms, mixed query synthesizers. |
| **High-level test set generator** | Managed pipeline over LangChain documents (`generate_with_langchain_docs`). |

### UI preview

Add your own screenshots under `docs/screenshots/` so they render on GitHub:

| Screen | Suggested filename |
|--------|----------------------|
| Console (configuration) | `docs/screenshots/ui-console.png` |
| Run output (metadata + table) | `docs/screenshots/ui-output.png` |

![Configuration console](docs/screenshots/ui-console.png)

![Run manifest and synthetic rows](docs/screenshots/ui-output.png)

*If images do not render yet, add PNG exports to `docs/screenshots/` using the filenames above (see `docs/screenshots/README.md`).*

### Requirements

| Item | Notes |
|------|--------|
| **Python** | **3.12+** (see `.python-version` and `requires-python` in `pyproject.toml` files). |
| **[uv](https://docs.astral.sh/uv/)** | Used to install dependencies for the assignment and for `backend/`. |
| **OpenAI API key** | Required for LLM + embeddings. Set `OPENAI_API_KEY` in `backend/.env` (copy from `backend/env.example`). |
| **Git** | For cloning and pushing this repository. |
| **Windows: Visual C++ Redistributable** | If `pymupdf` fails with a DLL error, install the [VC++ 2015–2022 x64 redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist). |

**Backend stack** (`backend/pyproject.toml`): FastAPI, Uvicorn, python-dotenv, LangChain OpenAI / Community (**0.3.x**), **RAGAS 0.2.10**, **rapidfuzz**, PyMuPDF, NLTK, pandas.

**Assignment notebook stack** (root `pyproject.toml`): Jupyter, LangChain, LangGraph, RAGAS, Qdrant client, unstructured, NLTK, PyMuPDF, NumPy, etc.

### Quick start (API + UI)

```bash
cd backend
copy env.example .env   # Windows CMD; or: cp env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...

uv sync --python 3.12
uv run uvicorn app.main:app --reload --reload-exclude ".venv" --host 127.0.0.1 --port 8000
```

Or PowerShell:

```powershell
cd backend
.\run.ps1
```

Then open **http://127.0.0.1:8000/** for the console and **http://127.0.0.1:8000/docs** for OpenAPI.

**Corpus:** by default the service reads document files from the **`data/`** directory at the assignment root (override with `SDG_DATA_ROOT` in `.env` or the “Source repository path” field in the UI).

### Project layout

```
├── backend/                 # FastAPI app (own pyproject + .venv recommended)
│   ├── app/main.py          # Routes, static UI, CORS
│   ├── app/sdg.py           # RAGAS pipelines (KG + managed)
│   ├── run.ps1
│   └── env.example
├── frontend/                # Static HTML/CSS/JS (served by FastAPI)
├── data/                    # Default corpus location for the API
├── docs/screenshots/        # Add ui-console.png, ui-output.png here
├── Synthetic_Data_Generation_RAGAS_&_LangSmith_Assignment.ipynb
├── pyproject.toml           # Notebook / course dependencies (uv)
└── README.md
```

### API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness. |
| `POST` | `/api/generate` | JSON body: `mode` (`knowledge_graph` \| `abstract`), `testset_size`, optional `max_documents`, `data_dir`, model fields. |
| `GET` | `/` | Web console. |
| `GET` | `/docs` | Swagger UI. |

---


---

<p align="center">
  <sub>README updated for this repo to document the RAGAS API/UI. Course links preserved for AIE8 Session 7.</sub>
</p>
