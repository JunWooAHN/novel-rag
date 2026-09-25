from dataclasses import dataclass
from pathlib import Path
import tomllib

from toy_tune.domain.errors import UnsupportedError, ValidationError


@dataclass(frozen=True)
class Runtime:
    name: str
    execution: str
    engine: str
    workspace_root: str | None
    knowledge: str


def load_runtime(path: Path, workspace_override: str | None = None) -> Runtime:
    try:
        config = tomllib.loads(path.read_text())
        if set(config) != {"runtime"}:
            raise ValueError()
        fields = config["runtime"]
        if set(fields) - {"name", "execution", "engine", "workspace_root", "knowledge"}:
            raise ValueError()
        runtime = Runtime(**(fields | {"workspace_root": workspace_override or fields.get("workspace_root")}))
        if not all(isinstance(v, str) and v for v in
                   (runtime.name, runtime.execution, runtime.engine, runtime.knowledge)):
            raise ValueError()
        if runtime.workspace_root is not None and not isinstance(runtime.workspace_root, str):
            raise ValueError()
    except (OSError, ValueError, TypeError):
        raise ValidationError("Invalid runtime profile; expected only documented runtime fields.") from None
    if runtime.execution not in {"local", "backendai", "ssh"}:
        raise ValidationError("Unknown execution profile.")
    if runtime.engine not in {"none", "hf-peft", "mlx"}:
        raise ValidationError("Unknown engine.")
    if runtime.knowledge != "snapshot":
        raise UnsupportedError("Only frozen source bundles are implemented. SQLite/PostgreSQL adapters are pending.")
    return runtime


def load_counts(path: Path) -> tuple[int, int, int]:
    try:
        config = tomllib.loads(path.read_text())
        if set(config) != {"split"} or set(config["split"]) != {"train", "validation", "test"}:
            raise ValueError()
        counts = tuple(config["split"][k] for k in ("train", "validation", "test"))
        if any(type(v) is not int or v <= 0 for v in counts):
            raise ValueError()
        return counts
    except (OSError, ValueError, TypeError):
        raise ValidationError("Invalid dataset split profile.") from None
