"""Run paired wiki-only and evidence-enriched 31B candidate extractions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from run import MODEL, REVISION


INSTRUCTIONS = """Extract source-attributed H/K/B ontology *candidates*, not
verified historical truth, from the EVIDENCE SOURCES. Only each source's text
field is exact quotable evidence; context is a navigation summary. Use no model memory as
evidence. Separate H historical events/states, K independent knowledge or
concept identities/content, and B historical formulation, publication,
transmission, adoption or actual use of K. A concept can exist independently
of when a person knew or used it. A B claim must refer to a K local ID when
the source supports that identity. Do not equate knowing, spreading and being
able to produce a technology. Preserve unknown origin/date/actor as unknown.
Keep actor and affected roles separate; do not invent causal or self-object
relations. Distinguish a ruler's reign interval from the date a text, script,
or technique was created or published. Preserve modal wording such as
'moved to create' instead of strengthening it to 'created'. Distinguish the
Hangul script from a book describing it. Focus on roughly pre-1950 content;
clearly later facts are out of scope, uncertain near-boundary dates stay
uncertain. If sources conflict or do not establish a needed fact, put the
question in unresolved. Every evidence item must cite an exact substring of
one supplied source using its source_id. No ellipses or paraphrase in quotes.
Use applicable existing mapping IDs only: SD-PEOPLE-01, SD-PEOPLE-02,
SD-POLITY-04, SD-TECH-01, SD-LANG-01, SD-LANG-02, EX-001, EX-005,
EX-012, EX-029, EX-031, RM-POWER-01, RM-CONCEPT-05, RM-TECH-04,
RM-TECH-07, IN-055, IN-060. These refer to the existing full
mapping, not a new ontology. Return JSON only with this shape:
{"source_unit_id":"...","K":[{"id":"K1","mapping_refs":["..."],
"name":"...","content":"...","evidence":[{"source_id":"...",
"quote":"..."}],"uncertainty":null}],
"H":[{"id":"H1","mapping_refs":["..."],"event_or_state":"...",
"actor":null,"affected":null,"time_text":null,
"time_role":"event_time|reign_interval|other|unknown",
"evidence":[{"source_id":"...","quote":"..."}],"uncertainty":null}],
"B":[{"id":"B1","mapping_refs":["..."],"knowledge_ref":"K1",
"bridge_type":"formulation|publication|transmission|adoption|use|other",
"actor":null,"time_text":null,
"time_role":"event_time|reign_interval|other|unknown",
"evidence":[{"source_id":"...","quote":"..."}],"uncertainty":null}],
"unresolved":["..."]}. Use empty arrays where appropriate, at most 12
combined candidates. No markdown fences."""


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def evidence_for(unit: dict, extra: dict | None) -> list[dict]:
    sources = [{"source_id": unit["source_unit_id"], "text": unit["text"]}]
    if extra is not None:
        for item in extra.get(unit["source_unit_id"], []):
            if sha(item["text"].encode("utf-8")) != item["source_sha256"]:
                raise ValueError(f"Additional evidence hash mismatch: {item['source_id']}")
            sources.append({"source_id": item["source_id"], "text": item["text"],
                            "context": item.get("context_summary")})
    if len({item["source_id"] for item in sources}) != len(sources):
        raise ValueError("Duplicate evidence source ID")
    return sources


def make_prompt(unit: dict, sources: list[dict]) -> str:
    return (INSTRUCTIONS + "\nsource_unit_id: " + unit["source_unit_id"]
            + "\nEVIDENCE SOURCES:\n"
            + json.dumps(sources, ensure_ascii=False, sort_keys=True))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--packet", type=Path, required=True)
    p.add_argument("--mode", choices=["wiki_only", "enriched"], required=True)
    p.add_argument("--extra-evidence", type=Path)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--cache-dir", type=Path, required=True)
    args = p.parse_args()
    if (args.mode == "enriched") != (args.extra_evidence is not None):
        raise ValueError("Only enriched mode takes --extra-evidence")
    packet_raw = args.packet.read_bytes()
    units = json.loads(packet_raw)["units"]
    if len(units) != 5:
        raise ValueError("Comparison requires the same five baseline units")
    extra_raw = args.extra_evidence.read_bytes() if args.extra_evidence else None
    extra = json.loads(extra_raw) if extra_raw else None
    for unit in units:
        if sha(unit["text"].encode("utf-8")) != unit["source_unit_sha256"]:
            raise ValueError("Baseline unit hash mismatch")
        evidence_for(unit, extra)
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
        sources = evidence_for(unit, extra)
        prompt = make_prompt(unit, sources)
        target = args.output_dir / f"{unit['source_unit_id']}.json"
        if target.exists():
            previous = json.loads(target.read_bytes())
            if (previous.get("prompt_sha256") != sha(prompt.encode("utf-8"))
                    or previous.get("model_revision") != REVISION
                    or previous.get("mode") != args.mode
                    or previous.get("extra_evidence_sha256") != (sha(extra_raw) if extra_raw else None)):
                raise ValueError(f"Different re-extraction already exists: {target}")
            print(json.dumps({"unit": unit["source_unit_id"], "state": "existing"}))
            continue
        encoded = processor.apply_chat_template(
            [{"role": "user", "content": prompt}], tokenize=True,
            add_generation_prompt=True, enable_thinking=False,
            return_dict=True, return_tensors="pt")
        encoded = {key: value.to("cuda") for key, value in encoded.items()}
        input_length = encoded["input_ids"].shape[-1]
        with torch.inference_mode():
            generated = model.generate(**encoded, max_new_tokens=1900, do_sample=False)
        result = {
            "source_unit_id": unit["source_unit_id"],
            "source_unit_sha256": unit["source_unit_sha256"],
            "packet_sha256": sha(packet_raw),
            "extra_evidence_sha256": sha(extra_raw) if extra_raw else None,
            "mode": args.mode, "model": MODEL, "model_revision": REVISION,
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
