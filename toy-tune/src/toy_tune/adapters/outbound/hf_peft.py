"""Explicit H200-only Gemma 4 LoRA trial; imported only by the train CLI path."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tarfile

from toy_tune.application.services.chat_labels import labeled_chat, text_token_ids
from toy_tune.application.use_cases.train_lora import canonical
from toy_tune.adapters.outbound.files.atomic import publish_json_once
from toy_tune.domain.errors import ValidationError
from toy_tune.domain.experiments import Capabilities, ModelRef, TrainingRequest


REPOSITORY = "google/gemma-4-E2B-it"
REVISION = "3e22461f65e89153144f8adb70e3b8c2cc9845a7"


def _hf():
    try:
        import torch
        import transformers
        import peft
        from transformers import AutoProcessor, AutoModelForMultimodalLM
        from peft import LoraConfig, PeftModel, get_peft_model
    except ImportError:
        raise ValidationError("Pinned CUDA Transformers and PEFT environment is unavailable.") from None
    if not torch.cuda.is_available():
        raise ValidationError("The small LoRA trial requires an observed CUDA device.")
    return torch, transformers, peft, AutoProcessor, AutoModelForMultimodalLM, LoraConfig, PeftModel, get_peft_model


def _text_targets(model, torch):
    targets = [name for name, module in model.named_modules()
               if name.startswith("model.language_model.layers.") and ".self_attn." in name
               and name.endswith(("q_proj", "v_proj", "q_proj.linear", "v_proj.linear"))
               and isinstance(module, torch.nn.Linear)]
    if not targets or not any(name.endswith(("q_proj", "q_proj.linear")) for name in targets) or not any(
            name.endswith(("v_proj", "v_proj.linear")) for name in targets):
        raise ValidationError("No verified text decoder attention projections were found for LoRA.")
    return targets


def _select_train_rows(rows: list[dict], sample_ids: tuple[str, ...]) -> list[dict]:
    if not 1 <= len(sample_ids) <= 4 or len(set(sample_ids)) != len(sample_ids):
        raise ValidationError("Choose 1–4 distinct train sample IDs.")
    by_id = {row["sample_id"]: row for row in rows}
    if len(by_id) != len(rows) or any(sample_id not in by_id for sample_id in sample_ids):
        raise ValidationError("A selected sample is absent from the pinned train split.")
    return [by_id[sample_id] for sample_id in sample_ids]


class HFPeftGemma4Engine:
    def __init__(self, dataset_dir: Path, output_dir: Path, sample_ids: tuple[str, ...],
                 max_tokens: int = 2048, attempt_id: str = "", request_sha256: str = ""):
        self.dataset_dir = dataset_dir
        self.output_dir = output_dir
        self.sample_ids = sample_ids
        self.max_tokens = max_tokens
        self.attempt_id = attempt_id
        self.request_sha256 = request_sha256

    def capabilities(self) -> Capabilities:
        return Capabilities(engine="hf-peft", operations=frozenset({"train"}),
                            formats=frozenset({"hf"}), dtypes=frozenset({"bfloat16"}))

    def train(self, request: TrainingRequest) -> str:
        self.capabilities().require("train", request.model, request.dtype)
        if (request.model.repository != REPOSITORY or request.model.revision != REVISION
                or request.max_steps not in (1, 2) or not 1 <= len(self.sample_ids) <= 4
                or not 0 < self.max_tokens <= 4096 or self.output_dir.exists()
                or not self.attempt_id or len(self.request_sha256) != 64):
            raise ValidationError("Gemma 4 trial needs a pinned revision, tiny budget and new output directory.")
        try:
            lines = (self.dataset_dir / "train.jsonl").read_bytes().splitlines()
            rows = _select_train_rows([json.loads(line) for line in lines], self.sample_ids)
        except (OSError, ValueError, TypeError):
            raise ValidationError("Cannot read the pinned train split.") from None
        if len(rows) != len(self.sample_ids) or any(
                set(row) != {"sample_id", "work_id", "scene_id", "order", "prompt", "answer",
                             "source_id", "source_sha256", "answer_start", "answer_end",
                             "question_method", "packet_id"} for row in rows):
            raise ValidationError("Selected train samples do not match the reviewed packet shape.")
        torch, transformers, peft, AutoProcessor, AutoModelForMultimodalLM, LoraConfig, _, get_peft_model = _hf()
        torch.manual_seed(request.seed)
        processor = AutoProcessor.from_pretrained(request.model.repository, revision=request.model.revision)
        tokenized = [labeled_chat(processor, row["prompt"], row["answer"], self.max_tokens)
                     for row in rows]
        model = AutoModelForMultimodalLM.from_pretrained(
            request.model.repository, revision=request.model.revision, dtype=torch.bfloat16)
        model.to("cuda")
        model.config.use_cache = False
        targets = _text_targets(model, torch)
        model = get_peft_model(model, LoraConfig(r=4, lora_alpha=8, lora_dropout=0.0,
                                                 bias="none", target_modules=targets))
        parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
        if not parameters or sum(parameter.numel() for parameter in parameters) <= 0:
            raise ValidationError("LoRA did not expose trainable text parameters.")
        optimizer = torch.optim.AdamW(parameters, lr=2e-4)
        model.train()
        before = [parameter.detach().clone() for parameter in parameters]
        losses = []
        for step in range(request.max_steps):
            input_ids, labels = tokenized[step % len(tokenized)]
            tokens = torch.tensor([input_ids], dtype=torch.long, device="cuda")
            supervised = torch.tensor([labels], dtype=torch.long, device="cuda")
            attention = torch.ones_like(tokens)
            optimizer.zero_grad(set_to_none=True)
            loss = model(input_ids=tokens, attention_mask=attention, labels=supervised).loss
            if loss is None or not torch.isfinite(loss).item():
                raise ValidationError("The small LoRA trial did not produce finite loss.")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(parameters, 1.0)
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
        changed_elements = sum(int(torch.count_nonzero(parameter.detach() != initial).item())
                               for parameter, initial in zip(parameters, before))
        if changed_elements == 0:
            raise ValidationError("LoRA optimizer produced no parameter change.")
        self.output_dir.mkdir(parents=True, mode=0o700)
        adapter = self.output_dir / "adapter"
        model.save_pretrained(adapter, safe_serialization=True)
        report = {"schema_version": 1, "run_id": request.run_id,
                  "attempt_id": self.attempt_id, "request_sha256": self.request_sha256,
                  "dataset_id": request.dataset_id, "model_repository": request.model.repository,
                  "model_revision": request.model.revision, "selected_sample_ids": [r["sample_id"] for r in rows],
                  "max_steps": request.max_steps, "max_tokens": self.max_tokens,
                  "token_validation": "passed_real_tokenizer",
                  "loss_mask_validation": "passed_real_tokenizer",
                  "losses": losses, "changed_lora_elements": changed_elements,
                  "trainable_parameters": sum(p.numel() for p in parameters),
                  "target_modules": targets, "torch": torch.__version__,
                  "transformers": transformers.__version__, "peft": peft.__version__,
                  "cuda_device": torch.cuda.get_device_name(0), "reload_verified": False}
        (self.output_dir / "train-report.json").write_text(json.dumps(report, sort_keys=True) + "\n")
        return str(adapter)


def verify_reload(output_dir: Path) -> dict:
    """Run from a fresh Python process after train-lora has exited."""
    report_path, adapter = output_dir / "train-report.json", output_dir / "adapter"
    if not report_path.is_file() or not adapter.is_dir():
        raise ValidationError("A complete adapter and pinned training report are required.")
    try:
        report = json.loads(report_path.read_bytes())
        request = json.loads((output_dir / "run-request.json").read_bytes())
        if (report["run_id"] != request["run_id"]
                or report["attempt_id"] != request["attempt_id"]
                or report["request_sha256"] != hashlib.sha256(canonical(request)).hexdigest()
                or report["selected_sample_ids"] != request["selected_sample_ids"]
                or report["dataset_id"] != request["prepared_dataset_id"]
                or report["model_repository"] + "@" + report["model_revision"]
                   != request["model_revision"]):
            raise ValueError()
    except (OSError, ValueError, KeyError, TypeError):
        raise ValidationError("Training report and pinned request differ or are unreadable.") from None
    archive = output_dir / "adapter.tar"
    proof_path = output_dir / "reload-report.json"
    if proof_path.exists():
        try:
            proof = json.loads(proof_path.read_bytes())
            expected = {"schema_version": 1, "run_id": report["run_id"],
                        "attempt_id": report["attempt_id"],
                        "request_sha256": report["request_sha256"],
                        "model_revision": report["model_revision"], "reload_verified": True}
            if (any(proof.get(key) != value for key, value in expected.items())
                    or type(proof.get("generated_token_count")) is not int
                    or proof["generated_token_count"] <= 0
                    or not archive.is_file()
                    or hashlib.sha256(archive.read_bytes()).hexdigest() != proof["artifact_sha256"]):
                raise ValueError()
        except (OSError, KeyError, TypeError, ValueError):
            raise ValidationError("Existing reload proof differs from the pinned attempt or artifact.") from None
        return {**proof, "artifact_path": str(archive), "training_completed": True}
    torch, _, _, AutoProcessor, AutoModelForMultimodalLM, _, PeftModel, _ = _hf()
    processor = AutoProcessor.from_pretrained(report["model_repository"], revision=report["model_revision"])
    base = AutoModelForMultimodalLM.from_pretrained(
        report["model_repository"], revision=report["model_revision"], dtype=torch.bfloat16)
    base.to("cuda")
    model = PeftModel.from_pretrained(base, adapter)
    model.eval()
    ids = text_token_ids(processor.apply_chat_template(
        [{"role": "user", "content": "Say one word."}], tokenize=True,
        add_generation_prompt=True, enable_thinking=False))
    with torch.no_grad():
        generated = model.generate(input_ids=torch.tensor([ids], device="cuda"), max_new_tokens=4)
    token_ids = generated[0].tolist()
    if len(token_ids) <= len(ids):
        raise ValidationError("Reloaded adapter did not generate tokens.")
    proof = {"schema_version": 1, "run_id": report["run_id"],
             "attempt_id": report["attempt_id"], "request_sha256": report["request_sha256"],
             "model_revision": report["model_revision"], "reload_verified": True,
             "generated_token_count": len(token_ids) - len(ids),
             "generated_ids_sha256": hashlib.sha256(json.dumps(token_ids).encode()).hexdigest()}
    with tarfile.open(archive, "w") as tar:
        for path in sorted(adapter.rglob("*")):
            if not path.is_file() or path.is_symlink():
                raise ValidationError("Adapter contains a nonregular file.")
            info = tar.gettarinfo(str(path), arcname=str(path.relative_to(output_dir)))
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            with path.open("rb") as stream:
                tar.addfile(info, stream)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    proof["artifact_sha256"] = digest
    publish_json_once(proof_path, proof, "Existing reload proof differs from the pinned attempt.")
    return {**proof, "artifact_path": str(archive),
            "training_completed": True}
