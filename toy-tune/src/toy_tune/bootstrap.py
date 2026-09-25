import json
from pathlib import Path
import sys

from toy_tune.adapters.inbound.cli import parser
from toy_tune.adapters.outbound.environment import LocalEnvironmentInspector
from toy_tune.adapters.outbound.files.sources import JsonSourceReader
from toy_tune.adapters.outbound.files.storage import FilesystemArtifactStore, workspace_path
from toy_tune.application.use_cases.preflight import preflight
from toy_tune.application.use_cases.prepare_dataset import prepare_dataset
from toy_tune.configuration import load_counts, load_runtime
from toy_tune.domain.errors import ToyTuneError, ValidationError


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        runtime = load_runtime(Path(args.runtime), args.workspace)
        if args.command == "doctor":
            result = preflight(LocalEnvironmentInspector(), args.probe_gpu)
            result["runtime"] = {"name": runtime.name, "execution": runtime.execution, "engine": runtime.engine}
            if runtime.workspace_root:
                workspace_path(runtime.workspace_root)
            result["workspace_policy"] = "valid" if runtime.workspace_root else "not_configured"
            result["execution_note"] = "Commands execute on the current machine; runtime does not open SSH."
        else:
            if not runtime.workspace_root:
                raise ValidationError("Specify an absolute workspace using --workspace or runtime profile.")
            workspace = workspace_path(runtime.workspace_root)
            store = FilesystemArtifactStore(workspace)
            if args.command == "prepare":
                manifest = prepare_dataset(
                    JsonSourceReader(Path(args.source)), store, load_counts(Path(args.split)),
                    args.allow_context_overlap)
            else:
                manifest = store.verify(args.dataset_id)
            result = {"artifact_id": manifest["artifact_id"], "verified": True,
                      "counts": manifest["metadata"].get("counts"),
                      "token_validation": manifest["metadata"].get("token_validation"),
                      "loss_mask_validation": manifest["metadata"].get("loss_mask_validation"),
                      "warnings": manifest["metadata"].get("warnings", [])}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ToyTuneError as error:
        print(str(error), file=sys.stderr)
        return 2
    except OSError:
        print("Filesystem operation failed; inspect permissions and capacity. Private paths are omitted.", file=sys.stderr)
        return 2
