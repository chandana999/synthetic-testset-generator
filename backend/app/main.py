from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.sdg import run_abstract_sdg, run_knowledge_graph_sdg

_backend_root = Path(__file__).resolve().parent.parent
load_dotenv(_backend_root / ".env")

logger = logging.getLogger(__name__)

app = FastAPI(title="SDG API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("SDG_CORS_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateBody(BaseModel):
    mode: Literal["knowledge_graph", "abstract"] = Field(
        ...,
        description="knowledge_graph = explicit KG + transforms + generate; abstract = generate_with_langchain_docs",
    )
    testset_size: int = Field(5, ge=1, le=100)
    max_documents: int | None = Field(
        20,
        description="Max LangChain documents to load (PyMuPDF: usually one per PDF page), not max PDF files. null = load all segments.",
    )
    data_dir: str | None = Field(
        None,
        description="Optional absolute path to a folder of PDFs; default is SDG_DATA_ROOT or ../data from assignment root.",
    )
    chat_model: str = Field("gpt-4.1-nano")
    embedding_model: str = Field("text-embedding-3-small")

    @field_validator("max_documents")
    @classmethod
    def validate_max_documents(cls, v: int | None) -> int | None:
        if v is None:
            return None
        if v < 1 or v > 500:
            raise ValueError("max_documents must be between 1 and 500, or null (caps LangChain segments/pages, not PDF file count)")
        return v


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/generate")
def generate(body: GenerateBody) -> JSONResponse:
    data_path = Path(body.data_dir).expanduser().resolve() if body.data_dir else None
    try:
        if body.mode == "knowledge_graph":
            examples, meta = run_knowledge_graph_sdg(
                data_dir=data_path,
                testset_size=body.testset_size,
                max_documents=body.max_documents,
                chat_model=body.chat_model,
                embedding_model=body.embedding_model,
                raise_exceptions=False,
            )
        else:
            examples, meta = run_abstract_sdg(
                data_dir=data_path,
                testset_size=body.testset_size,
                max_documents=body.max_documents,
                chat_model=body.chat_model,
                embedding_model=body.embedding_model,
            )
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("SDG pipeline failed")
        raise HTTPException(status_code=500, detail=f"SDG failed: {e!s}") from e

    payload: dict[str, Any] = {"examples": examples, "metadata": meta}
    return JSONResponse(content=payload)


_frontend_dir = Path(__file__).resolve().parents[2] / "frontend"


@app.get("/")
def serve_ui():
    index = _frontend_dir / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=404, detail="frontend/index.html missing")
    return FileResponse(index)


if _frontend_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_frontend_dir)), name="assets")
