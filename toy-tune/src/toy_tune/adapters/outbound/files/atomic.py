"""Publish a small immutable JSON result without leaving a partial final file."""
import json
import os
from pathlib import Path
import tempfile

from toy_tune.domain.errors import ValidationError


def publish_json_once(path: Path, value: dict, conflict: str) -> None:
    payload = (json.dumps(value, sort_keys=True) + "\n").encode()
    if path.exists():
        if path.read_bytes() != payload:
            raise ValidationError(conflict)
        return
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=".result-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise ValidationError(conflict) from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
