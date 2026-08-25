import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.knowledge_base import retrieve_knowledge
from schema import FaultType


def main() -> None:
    refs = retrieve_knowledge(
        "Web server failed to start. Port 8080 was already in use.",
        fault_type=FaultType.PORT_CONFLICT,
        k=3,
    )

    for index, ref in enumerate(refs, start=1):
        print(f"## {index}. {ref.title}")
        print(ref.source)
        print(ref.snippet[:300])
        print()


if __name__ == "__main__":
    main()