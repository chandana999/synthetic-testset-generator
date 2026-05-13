"""
Phase-1 SDG aligned with the assignment notebook (no notebook imports).

- knowledge_graph: KnowledgeGraph + default_transforms + TestsetGenerator(..., knowledge_graph=kg)
- abstract: TestsetGenerator(llm, embeddings) + generate_with_langchain_docs (shortcut / abstracted SDG)
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

from langchain_community.document_loaders import DirectoryLoader, PyMuPDFLoader
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.testset import TestsetGenerator
from ragas.testset.graph import KnowledgeGraph, Node, NodeType
from ragas.testset.synthesizers import (
    MultiHopAbstractQuerySynthesizer,
    MultiHopSpecificQuerySynthesizer,
    SingleHopSpecificQuerySynthesizer,
)
from ragas.testset.transforms import apply_transforms, default_transforms


def _project_root() -> Path:
    # backend/app/sdg.py -> assignment root (07_Synthetic_...)
    return Path(__file__).resolve().parents[2]


def _default_data_dir() -> Path:
    override = os.environ.get("SDG_DATA_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return (_project_root() / "data").resolve()


def load_pdf_docs(data_dir: Path | None, *, max_documents: int | None) -> list:
    root = data_dir or _default_data_dir()
    if not root.is_dir():
        raise FileNotFoundError(f"Data directory not found: {root}")

    loader = DirectoryLoader(str(root), glob="*.pdf", loader_cls=PyMuPDFLoader)
    docs = loader.load()
    if max_documents is not None and max_documents > 0:
        docs = docs[:max_documents]
    if not docs:
        raise ValueError(f"No PDFs matched in {root} (glob='*.pdf').")
    return docs


def _loader_stats(docs: list) -> dict[str, Any]:
    """PyMuPDFLoader yields one LangChain Document per PDF page, not per file."""
    sources: set[str] = set()
    for d in docs:
        src = d.metadata.get("source") or d.metadata.get("file_path") or ""
        if isinstance(src, str) and src.strip():
            sources.add(src)
    names = sorted(Path(s).name for s in sources)
    return {
        "segments_loaded": len(docs),
        "unique_pdf_files": len(sources),
        "source_file_names": names,
    }


def _ragas_wrappers(
    *,
    chat_model: str,
    embedding_model: str,
) -> tuple[LangchainLLMWrapper, LangchainEmbeddingsWrapper]:
    key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing or empty. Set it in backend/.env (same folder as pyproject.toml), "
            "then restart uvicorn."
        )

    generator_llm = LangchainLLMWrapper(ChatOpenAI(model=chat_model))
    generator_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model=embedding_model))
    return generator_llm, generator_embeddings


def _df_to_records(df) -> list[dict[str, Any]]:
    def sanitize(obj: Any) -> Any:
        if obj is None or isinstance(obj, (str, int, bool)):
            return obj
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        if hasattr(obj, "tolist"):
            try:
                return obj.tolist()
            except Exception:
                return str(obj)
        if isinstance(obj, (list, tuple)):
            return [sanitize(x) for x in obj]
        if isinstance(obj, dict):
            return {str(k): sanitize(v) for k, v in obj.items()}
        return str(obj)

    records = df.to_dict(orient="records")
    return [sanitize(r) for r in records]


def run_knowledge_graph_sdg(
    *,
    data_dir: Path | None = None,
    testset_size: int = 5,
    max_documents: int | None = 20,
    chat_model: str = "gpt-4.1-nano",
    embedding_model: str = "text-embedding-3-small",
    raise_exceptions: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Notebook flow: KG from docs -> default_transforms -> TestsetGenerator with knowledge_graph.
    Query mix matches the notebook (single-hop + multi-hop abstract + multi-hop specific).
    """
    docs = load_pdf_docs(data_dir, max_documents=max_documents)
    generator_llm, embedding_model_wrapped = _ragas_wrappers(
        chat_model=chat_model, embedding_model=embedding_model
    )

    kg = KnowledgeGraph()
    for doc in docs:
        kg.nodes.append(
            Node(
                type=NodeType.DOCUMENT,
                properties={"page_content": doc.page_content, "document_metadata": doc.metadata},
            )
        )

    transformer_llm = generator_llm
    transforms = default_transforms(documents=docs, llm=transformer_llm, embedding_model=embedding_model_wrapped)
    apply_transforms(kg, transforms)

    generator = TestsetGenerator(
        llm=generator_llm,
        embedding_model=embedding_model_wrapped,
        knowledge_graph=kg,
    )
    query_distribution = [
        (SingleHopSpecificQuerySynthesizer(llm=generator_llm), 0.5),
        (MultiHopAbstractQuerySynthesizer(llm=generator_llm), 0.25),
        (MultiHopSpecificQuerySynthesizer(llm=generator_llm), 0.25),
    ]
    testset = generator.generate(
        testset_size=testset_size,
        query_distribution=query_distribution,
        raise_exceptions=raise_exceptions,
    )
    df = testset.to_pandas()
    stats = _loader_stats(docs)
    meta = {
        "mode": "knowledge_graph",
        "nodes": len(kg.nodes),
        "relationships": len(kg.relationships),
        **stats,
        "testset_size_requested": testset_size,
        "rows": len(df),
        "chat_model": chat_model,
        "embedding_model": embedding_model,
    }
    return _df_to_records(df), meta


def run_abstract_sdg(
    *,
    data_dir: Path | None = None,
    testset_size: int = 10,
    max_documents: int | None = 20,
    chat_model: str = "gpt-4.1-nano",
    embedding_model: str = "text-embedding-3-small",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Notebook 'Abstracted SDG': TestsetGenerator without explicit KG + generate_with_langchain_docs.
    """
    docs = load_pdf_docs(data_dir, max_documents=max_documents)
    generator_llm, generator_embeddings = _ragas_wrappers(
        chat_model=chat_model, embedding_model=embedding_model
    )
    generator = TestsetGenerator(llm=generator_llm, embedding_model=generator_embeddings)
    dataset = generator.generate_with_langchain_docs(docs, testset_size=testset_size)
    df = dataset.to_pandas()
    stats = _loader_stats(docs)
    meta = {
        "mode": "abstract",
        **stats,
        "testset_size_requested": testset_size,
        "rows": len(df),
        "chat_model": chat_model,
        "embedding_model": embedding_model,
    }
    return _df_to_records(df), meta

