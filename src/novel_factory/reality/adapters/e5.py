"""Actual multilingual E5 embeddings; never silently truncate a source span."""

from __future__ import annotations


class E5Embedder:
    model = "intfloat/multilingual-e5-small"
    revision = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
    dimension = 384

    def __init__(self, cache_dir: str):
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model, revision=self.revision, cache_dir=cache_dir
        )
        self.encoder = AutoModel.from_pretrained(
            self.model, revision=self.revision, cache_dir=cache_dir
        )
        self.encoder.to("cpu").eval()

    def _encode(self, prefix: str, text: str) -> list[float]:
        import torch.nn.functional as F

        encoded = self.tokenizer(prefix + text, return_tensors="pt", truncation=False)
        length = int(encoded["input_ids"].shape[-1])
        if length > 512:
            raise ValueError(f"E5 input needs a smaller pinned unit: {length} > 512 tokens")
        with self.torch.inference_mode():
            hidden = self.encoder(**encoded).last_hidden_state
            mask = encoded["attention_mask"].unsqueeze(-1)
            mean = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
            vector = F.normalize(mean, p=2, dim=1)[0].tolist()
        if len(vector) != self.dimension:
            raise ValueError("E5 model returned an unexpected dimension")
        return vector

    def passage(self, text: str) -> list[float]:
        return self._encode("passage: ", text)

    def passage_token_length(self, text: str) -> int:
        encoded = self.tokenizer("passage: " + text, truncation=False)
        return len(encoded["input_ids"])

    def query(self, text: str) -> list[float]:
        return self._encode("query: ", text)
