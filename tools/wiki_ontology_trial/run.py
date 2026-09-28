"""One-off, bounded Gemma 4 31B extraction trial on pinned dump excerpts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


MODEL = "google/gemma-4-31B-it"
REVISION = "842da3794eaa0b77d5f08bae87a17459d91ff475"

INSTRUCTIONS = """You extract *candidate claims* from one English Wikipedia source excerpt.
Return a JSON object only. This source's prose is an attributed claim, not verified historical truth.
Use the existing CIDOC/project mapping references where supported: SD-PEOPLE-01,
SD-PEOPLE-02, SD-POLITY-04, SD-TECH-01, SD-LANG-01, SD-LANG-02,
EX-001, EX-005, EX-012, EX-029, EX-031, RM-POWER-01, RM-CONCEPT-05,
RM-TECH-04, RM-TECH-07, IN-055, IN-060. These are references into the
existing mapping, not a new ontology. Do not invent a mapping ID.
Separate H (historical event/state), K (independent knowledge/concept/content
version), and B (historical formulation, transmission, adoption, actual use).
Knowledge possession is not technical capability, and invention is not widespread use.
Target events and human knowledge content from roughly before 1950; clearly
later content is outside this trial. Later-written sources may describe older
facts. If a claim's historical time is unknown or near the boundary, keep its
original expression and mark uncertainty; do not invent a precise cutoff date.
Do not guess an origin date, participant, place, causation, or identity.
For every candidate, evidence_quote must be a short exact substring of SOURCE,
including punctuation and wikitext markup as printed. No paraphrase in evidence_quote.
Output shape: {"source_unit_id":"...","candidates":[{"layer":"H|K|B",
"mapping_refs":["existing ID"],"subject":"...","predicate":"...",
"object":"...","time_text":"... or null","evidence_quote":"...",
"uncertainty":"... or null"}],"unmapped_notes":["..."]}.
Return 0 to 8 candidates; an empty list is valid. No markdown fences."""


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def make_prompt(unit: dict) -> str:
    return (INSTRUCTIONS + "\n\nsource_unit_id: " + unit["source_unit_id"]
            + "\npage_title: " + unit["title"] + "\nSOURCE:\n" + unit["text"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    packet_raw = args.packet.read_bytes()
    packet = json.loads(packet_raw)
    units = packet["units"][: args.limit]
    if not 1 <= len(units) <= 5:
        raise ValueError("Trial accepts 1 to 5 source units")
    if any(len(unit["text"]) > 5000 for unit in units):
        raise ValueError("One source excerpt exceeds trial limit")
    if any(digest(unit["text"].encode("utf-8")) != unit["source_unit_sha256"] for unit in units):
        raise ValueError("A source excerpt differs from its declared hash")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    from transformers import AutoModelForMultimodalLM, AutoProcessor
    import torch

    processor = AutoProcessor.from_pretrained(
        MODEL, revision=REVISION, cache_dir=str(args.cache_dir), local_files_only=True
    )
    model = AutoModelForMultimodalLM.from_pretrained(
        MODEL, revision=REVISION, cache_dir=str(args.cache_dir),
        local_files_only=True, dtype=torch.bfloat16, device_map="cuda"
    )
    model.eval()

    for unit in units:
        path = args.output_dir / f"{unit['source_unit_id']}.json"
        if path.exists():
            existing = json.loads(path.read_bytes())
            if (existing.get("source_unit_sha256") != unit["source_unit_sha256"]
                    or existing.get("packet_sha256") != digest(packet_raw)
                    or existing.get("model") != MODEL
                    or existing.get("model_revision") != REVISION
                    or existing.get("prompt_sha256") != digest(make_prompt(unit).encode("utf-8"))):
                raise ValueError(f"Existing result is for a different source: {path.name}")
            print(json.dumps({"unit": unit["source_unit_id"], "state": "existing"}))
            continue
        prompt = make_prompt(unit)
        encoded = processor.apply_chat_template(
            [{"role": "user", "content": prompt}], tokenize=True,
            add_generation_prompt=True, enable_thinking=False,
            return_dict=True, return_tensors="pt"
        )
        encoded = {key: value.to("cuda") for key, value in encoded.items()}
        input_length = encoded["input_ids"].shape[-1]
        with torch.inference_mode():
            generated = model.generate(**encoded, max_new_tokens=900, do_sample=False)
        response = processor.decode(generated[0][input_length:], skip_special_tokens=True)
        result = {
            "source_unit_id": unit["source_unit_id"],
            "source_unit_sha256": unit["source_unit_sha256"],
            "packet_sha256": digest(packet_raw),
            "model": MODEL, "model_revision": REVISION,
            "prompt_sha256": digest(prompt.encode("utf-8")),
            "input_tokens": input_length,
            "generated_tokens": generated.shape[-1] - input_length,
            "raw_response": response,
        }
        path.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        print(json.dumps({"unit": unit["source_unit_id"], "state": "generated",
                          "input_tokens": input_length,
                          "generated_tokens": result["generated_tokens"]}))


if __name__ == "__main__":
    main()
