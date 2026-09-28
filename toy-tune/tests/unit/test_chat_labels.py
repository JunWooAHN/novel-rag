import unittest

from toy_tune.application.services.chat_labels import labeled_chat
from toy_tune.domain.errors import ValidationError


class FakeProcessor:
    def __init__(self, mismatched=False):
        self.mismatched = mismatched

    def apply_chat_template(self, messages, **kwargs):
        if len(messages) == 1:
            return [1, 2, 3]
        return [1, 9 if self.mismatched else 2, 3, 4, 5]


class ChatLabelsTests(unittest.TestCase):
    def test_only_answer_tokens_receive_loss(self):
        input_ids, labels = labeled_chat(FakeProcessor(), "prompt", "answer", 8)
        self.assertEqual(input_ids, [1, 2, 3, 4, 5])
        self.assertEqual(labels, [-100, -100, -100, 4, 5])

    def test_template_mismatch_and_truncation_fail_closed(self):
        with self.assertRaisesRegex(ValidationError, "exact prefix"):
            labeled_chat(FakeProcessor(mismatched=True), "prompt", "answer", 8)
        with self.assertRaisesRegex(ValidationError, "token limit"):
            labeled_chat(FakeProcessor(), "prompt", "answer", 4)

    def test_single_batch_processor_shape(self):
        class GemmaShape(FakeProcessor):
            def apply_chat_template(self, messages, **kwargs):
                return [super().apply_chat_template(messages, **kwargs)]

        _, labels = labeled_chat(GemmaShape(), "prompt", "answer", 8)
        self.assertEqual(labels, [-100, -100, -100, 4, 5])
