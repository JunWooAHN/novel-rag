"""Pinned Gemma candidate extractor; loaded only for the bounded GPU command."""

from __future__ import annotations

MODEL = "google/gemma-4-31B-it"
MODEL_REVISION = "842da3794eaa0b77d5f08bae87a17459d91ff475"


class GemmaExtractor:
    def __init__(self, cache_dir: str):
        import torch
        from transformers import AutoModelForMultimodalLM, AutoProcessor

        self.torch = torch
        self.processor = AutoProcessor.from_pretrained(
            MODEL, revision=MODEL_REVISION, cache_dir=cache_dir, local_files_only=True
        )
        self.model = AutoModelForMultimodalLM.from_pretrained(
            MODEL, revision=MODEL_REVISION, cache_dir=cache_dir,
            local_files_only=True, dtype=torch.bfloat16, device_map="cuda"
        )
        self.model.eval()

    def extract(self, prompt: str, max_new_tokens: int = 1000) -> str:
        encoded = self.processor.apply_chat_template(
            [{"role": "user", "content": prompt}], tokenize=True,
            add_generation_prompt=True, enable_thinking=False,
            return_dict=True, return_tensors="pt"
        )
        encoded = {key: value.to("cuda") for key, value in encoded.items()}
        input_length = encoded["input_ids"].shape[-1]
        self.last_input_tokens = int(input_length)
        with self.torch.inference_mode():
            generated = self.model.generate(**encoded, max_new_tokens=max_new_tokens, do_sample=False)
        self.last_generated_tokens = int(generated.shape[-1] - input_length)
        return self.processor.decode(generated[0][input_length:], skip_special_tokens=True)
