from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonLineLogger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
