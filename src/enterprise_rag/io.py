import json
from pathlib import Path
from typing import Iterable, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def write_jsonl(path: Path, records: Iterable[BaseModel]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(record.model_dump_json() + "\n")


def read_jsonl(path: Path, model: type[T]) -> list[T]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [model.model_validate(json.loads(line)) for line in handle if line.strip()]

