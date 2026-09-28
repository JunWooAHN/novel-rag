"""Make answer-only loss labels using an actual chat processor's token IDs."""

from toy_tune.domain.errors import ValidationError


def text_token_ids(value) -> list[int]:
    """Normalize a single text chat result; Gemma4Processor returns one nested batch."""
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], list):
        value = value[0]
    if not isinstance(value, list) or not value or any(type(token) is not int for token in value):
        raise ValidationError("The pinned processor did not return one text-only token sequence.")
    return value


def labeled_chat(processor, prompt: str, answer: str, max_tokens: int) -> tuple[list[int], list[int]]:
    if not isinstance(prompt, str) or not prompt.strip() or not isinstance(answer, str) or not answer.strip():
        raise ValidationError("Training prompt and answer must be nonempty.")
    user = [{"role": "user", "content": prompt}]
    try:
        prefix = text_token_ids(processor.apply_chat_template(
            user, tokenize=True, add_generation_prompt=True, enable_thinking=False))
        full = text_token_ids(processor.apply_chat_template(
            user + [{"role": "assistant", "content": answer}], tokenize=True,
            add_generation_prompt=False, enable_thinking=False))
    except (TypeError, ValueError, AttributeError):
        raise ValidationError("The pinned processor could not tokenize text-only chat.") from None
    if len(full) <= len(prefix) or full[:len(prefix)] != prefix:
        raise ValidationError("Prompt token IDs are not an exact prefix of the supervised chat.")
    if len(full) > max_tokens:
        raise ValidationError("Selected training sample exceeds the explicit token limit.")
    labels = [-100] * len(prefix) + full[len(prefix):]
    if not any(token != -100 for token in labels):
        raise ValidationError("No answer token remains after prompt masking.")
    return full, labels
