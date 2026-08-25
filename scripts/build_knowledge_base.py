import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.knowledge_base import build_knowledge_base


def main() -> None:
    chunk_count = build_knowledge_base()
    print(f"知识库构建完成，写入 chunk 数量：{chunk_count}")


if __name__ == "__main__":
    main()