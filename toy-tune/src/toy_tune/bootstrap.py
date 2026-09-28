import hashlib
import json
from pathlib import Path
import sys

from toy_tune.adapters.inbound.cli import parser
from toy_tune.adapters.outbound.environment import LocalEnvironmentInspector
from toy_tune.adapters.outbound.files.sources import JsonSourceReader
from toy_tune.adapters.outbound.files.storage import FilesystemArtifactStore, workspace_path
from toy_tune.adapters.outbound.files.atomic import publish_json_once
from toy_tune.application.use_cases.preflight import preflight
from toy_tune.application.use_cases.prepare_dataset import prepare_dataset, prepare_reviewed_packet
from toy_tune.application.services.frozen_packet import verify_frozen_derivation
from toy_tune.application.use_cases.train_lora import canonical, validate_offline_attempt
from toy_tune.configuration import load_counts, load_runtime
from toy_tune.domain.errors import ToyTuneError, ValidationError


def _write_result_once(path: Path, result: dict) -> None:
    publish_json_once(path, result, "Existing result differs from the pinned attempt.")


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
            if args.command in ("train-lora", "verify-lora"):
                if runtime.engine != "hf-peft":
                    raise ValidationError("The selected runtime does not permit HF PEFT training.")
                output = Path(args.output_dir).expanduser().resolve()
                if not output.is_relative_to(workspace) or output == workspace:
                    raise ValidationError("Training output must be inside the dedicated workspace.")
                from toy_tune.adapters.outbound.hf_peft import HFPeftGemma4Engine, REPOSITORY, REVISION, verify_reload
                if args.command == "train-lora":
                    manifest = store.verify(args.dataset_id)
                    manifest_path = workspace / "datasets" / args.dataset_id / "manifest.json"
                    verify_frozen_derivation(
                        (manifest_path.parent / "frozen-packet.json").read_bytes(), manifest)
                    try:
                        raw_request = Path(args.request).read_bytes()
                        manifest_raw = manifest_path.read_bytes()
                    except OSError:
                        raise ValidationError("The selected offline training request is unavailable.") from None
                    training_request, request_data, request_sha = validate_offline_attempt(
                        raw_request, manifest_raw, manifest, args.dataset_id, args.max_steps,
                        REPOSITORY + "@" + REVISION, args.sample_id)
                    adapter = HFPeftGemma4Engine(manifest_path.parent, output,
                                                  tuple(args.sample_id), args.max_tokens,
                                                  request_data["attempt_id"], request_sha).train(training_request)
                    (output / "run-request.json").write_bytes(raw_request)
                    result = {"run_id": request_data["run_id"], "attempt_id": request_data["attempt_id"],
                              "request_sha256": request_sha, "adapter_path": adapter,
                              "state": "trained_pending_fresh_process_reload"}
                else:
                    proof = verify_reload(output)
                    request_data = json.loads((output / "run-request.json").read_bytes())
                    result = {"schema_version": 1, "run_id": request_data["run_id"],
                              "attempt_id": request_data["attempt_id"],
                              "request_sha256": hashlib.sha256(canonical(request_data)).hexdigest(),
                              "status": "completed", "artifact_path": proof["artifact_path"],
                              "artifact_sha256": proof["artifact_sha256"],
                              "validation_scope": "real_tokenizer_and_reload", "training_completed": True,
                              "reload_verified": True, "token_validation": "passed_real_tokenizer",
                              "loss_mask_validation": "passed_real_tokenizer"}
                    _write_result_once(output / "result.json", result)
                    result = {"run_id": result["run_id"], "attempt_id": result["attempt_id"],
                              "state": "reload_verified_pending_product_review",
                              "artifact_sha256": result["artifact_sha256"],
                              "generated_token_count": proof["generated_token_count"]}
            elif args.command == "prepare":
                if args.frozen_packet:
                    if args.split or args.allow_context_overlap:
                        raise ValidationError("Frozen reviewed splits cannot be replaced or relaxed.")
                    try:
                        raw = Path(args.frozen_packet).read_bytes()
                    except OSError:
                        raise ValidationError("Cannot read the selected reviewed packet.") from None
                    manifest = prepare_reviewed_packet(raw, store)
                else:
                    if not args.split:
                        raise ValidationError("An explicit split profile is required with --source.")
                    manifest = prepare_dataset(
                        JsonSourceReader(Path(args.source)), store, load_counts(Path(args.split)),
                        args.allow_context_overlap)
            else:
                manifest = store.verify(args.dataset_id)
            if args.command in ("prepare", "verify-dataset"):
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
    except Exception:
        if args.command in ("train-lora", "verify-lora"):
            print("HF trial failed; inspect pinned environment and private run output without exposing prose.",
                  file=sys.stderr)
            return 2
        raise
