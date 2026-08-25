from pathlib import Path
from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.embeddings import get_embedding_model
from schema import FaultType, KnowledgeRef

KNOWLEDGE_DIR = Path("docs/knowledge")
CHROMA_DIR = Path("data/chroma/logmind_knowledge")
COLLECTION_NAME = "logmind_knowledge"


def _parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    metadata_text = parts[1].strip()
    body = parts[2].strip()
    metadata: dict[str, Any] = {}

    current_key: str | None = None
    for raw_line in metadata_text.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue

        if line.startswith("  - ") and current_key:
            metadata.setdefault(current_key, []).append(line[4:].strip())
            continue

        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        current_key = key

        if value:
            metadata[key] = value
        else:
            metadata[key] = []

    return metadata, body


def load_knowledge_documents(knowledge_dir: Path = KNOWLEDGE_DIR) -> list[Document]:
    documents: list[Document] = []

    for path in sorted(knowledge_dir.glob("*.md")):
        if path.name == "README.md":
            continue

        text = path.read_text(encoding="utf-8")
        metadata, body = _parse_front_matter(text)
        metadata["source"] = str(path)
        metadata["title"] = metadata.get("title") or path.stem

        documents.append(Document(page_content=body, metadata=metadata))

    return documents


def split_knowledge_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=120,
        separators=["\n## ", "\n### ", "\n\n", "\n", "。", ".", " "],
    )
    return splitter.split_documents(documents)


def _metadata_for_chroma(metadata: dict[str, Any]) -> dict[str, str]:
    chroma_metadata: dict[str, str] = {}
    for key, value in metadata.items():
        if isinstance(value, list):
            chroma_metadata[key] = ",".join(str(item) for item in value)
        elif value is not None:
            chroma_metadata[key] = str(value)
    return chroma_metadata


def build_knowledge_base(
    *,
    knowledge_dir: Path = KNOWLEDGE_DIR,
    persist_dir: Path = CHROMA_DIR,
) -> int:
    documents = load_knowledge_documents(knowledge_dir)
    chunks = split_knowledge_documents(documents)
    chunks = [
        Document(
            page_content=chunk.page_content,
            metadata=_metadata_for_chroma(chunk.metadata),
        )
        for chunk in chunks
    ]

    persist_dir.mkdir(parents=True, exist_ok=True)

    Chroma.from_documents(
        documents=chunks,
        embedding=get_embedding_model(),
        persist_directory=str(persist_dir),
        collection_name=COLLECTION_NAME,
    )

    return len(chunks)


def get_knowledge_vectorstore(persist_dir: Path = CHROMA_DIR) -> Chroma:
    return Chroma(
        persist_directory=str(persist_dir),
        embedding_function=get_embedding_model(),
        collection_name=COLLECTION_NAME,
    )


def retrieve_knowledge(
    query: str,
    *,
    fault_type: FaultType | None = None,
    k: int = 4,
    persist_dir: Path = CHROMA_DIR,
) -> list[KnowledgeRef]:
    vectorstore = get_knowledge_vectorstore(persist_dir)

    filter_query = None
    if fault_type and fault_type != FaultType.UNKNOWN:
        filter_query = {"fault_type": fault_type.value}

    docs = vectorstore.similarity_search(
        query,
        k=k,
        filter=filter_query,
    )

    return [
        KnowledgeRef(
            title=str(doc.metadata.get("title", "未命名知识")),
            source=str(doc.metadata.get("source", "")),
            snippet=doc.page_content[:500],
        )
        for doc in docs
    ]