"""Ask the pinned 31B model what its first five source-attributed drafts need checked."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from run import MODEL, REVISION


INSTRUCTIONS = """Audit a draft extraction from one Wikipedia excerpt. This is a
source-attributed candidate audit, not verification of historical truth.
SOURCE is the only evidence available to you. DRAFT is your prior model output.
Do not supply missing historical facts from memory. Do not invent dates or
citations. Identify omitted claims, possible source overstatements, uncertain
actor/patient roles or times, and possible mistakes between an independent
knowledge/concept K, a historical event/state H, and a formulation/use B.
Where SOURCE cannot resolve a question, say which additional evidence to seek.
Return JSON only:
{"source_unit_id":"...","hypotheses":[{"draft_item":0,
"possible_issue":"...","source_support":"supported|contradicted|unclear",
"reason":"..."}],"search_questions":[{"question":"...",
"why_needed":"..."}],"needed_evidence":["..."]}.
draft_item is a 1-based DRAFT index, or 0 for a missing claim. Up to five
hypotheses, five questions and five evidence needs. Do not answer your own
search questions. An empty list is valid. No markdown fences."""


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def make_prompt(unit: dict, baseline: dict) -> str:
    raw = baseline["raw_response"]
    start, end = raw.find("{"), raw.rfind("}")
    try:
        draft = json.loads(raw[start:end + 1])["candidates"]
    except (ValueError, KeyError) as exc:
        raise ValueError("Prior candidate JSON is unavailable") from exc
    return (INSTRUCTIONS + "\nsource_unit_id: " + unit["source_unit_id"]
            + "\nSOURCE:\n" + unit["text"]
            + "\nDRAFT:\n" + json.dumps(draft, ensure_ascii=False, sort_keys=True))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--packet", type=Path, required=True)
    p.add_argument("--baseline-result-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--cache-dir", type=Path, required=True)
    args = p.parse_args()
    packet_raw = args.packet.read_bytes()
    units = json.loads(packet_raw)["units"]
    baselines = {}
    for unit in units:
        path = args.baseline_result_dir / f"{unit['source_unit_id']}.json"
        raw = path.read_bytes()
        baseline = json.loads(raw)
        if (baseline["source_unit_id"] != unit["source_unit_id"]
                or baseline["source_unit_sha256"] != unit["source_unit_sha256"]
                or baseline["packet_sha256"] != sha(packet_raw)
                or baseline["model"] != MODEL or baseline["model_revision"] != REVISION):
            raise ValueError(f"Baseline result pin mismatch: {path}")
        baselines[unit["source_unit_id"]] = (baseline, sha(raw))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    from transformers import AutoModelForMultimodalLM, AutoProcessor
    import torch

    processor = AutoProcessor.from_pretrained(
        MODEL, revision=REVISION, cache_dir=str(args.cache_dir), local_files_only=True)
    model = AutoModelForMultimodalLM.from_pretrained(
        MODEL, revision=REVISION, cache_dir=str(args.cache_dir),
        local_files_only=True, dtype=torch.bfloat16, device_map="cuda")
    model.eval()
    for unit in units:
        baseline, baseline_sha = baselines[unit["source_unit_id"]]
        prompt = make_prompt(unit, baseline)
        target = args.output_dir / f"{unit['source_unit_id']}.json"
        if target.exists():
            previous = json.loads(target.read_bytes())
            if (previous.get("prompt_sha256") != sha(prompt.encode("utf-8"))
                    or previous.get("baseline_result_sha256") != baseline_sha
                    or previous.get("model_revision") != REVISION):
                raise ValueError(f"Different diagnosis already exists: {target}")
            print(json.dumps({"unit": unit["source_unit_id"], "state": "existing"}))
            continue
        encoded = processor.apply_chat_template(
            [{"role": "user", "content": prompt}], tokenize=True,
            add_generation_prompt=True, enable_thinking=False,
            return_dict=True, return_tensors="pt")
        encoded = {key: value.to("cuda") for key, value in encoded.items()}
        input_length = encoded["input_ids"].shape[-1]
        with torch.inference_mode():
            generated = model.generate(**encoded, max_new_tokens=900, do_sample=False)
        result = {
            "source_unit_id": unit["source_unit_id"],
            "source_unit_sha256": unit["source_unit_sha256"],
            "packet_sha256": sha(packet_raw),
            "baseline_result_sha256": baseline_sha,
            "model": MODEL, "model_revision": REVISION,
            "prompt_sha256": sha(prompt.encode("utf-8")),
            "input_tokens": input_length,
            "generated_tokens": generated.shape[-1] - input_length,
            "raw_response": processor.decode(
                generated[0][input_length:], skip_special_tokens=True),
        }
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        temporary.replace(target)
        print(json.dumps({"unit": unit["source_unit_id"], "state": "generated",
                          "input_tokens": input_length,
                          "generated_tokens": result["generated_tokens"]}))


if __name__ == "__main__":
    main()
