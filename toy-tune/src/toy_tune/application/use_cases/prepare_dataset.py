from toy_tune.application.ports.sources import SourceReader
from toy_tune.application.ports.stores import DatasetStore
from toy_tune.application.services.dataset_builder import build_dataset
from toy_tune.application.services.frozen_packet import build_frozen_packet


def prepare_dataset(source: SourceReader, store: DatasetStore, counts: tuple[int, int, int],
                    allow_context_overlap: bool = False) -> dict:
    dataset_id, files, metadata = build_dataset(source.read(), counts, allow_context_overlap, source.snapshot())
    return store.publish(dataset_id, files, metadata)


def prepare_reviewed_packet(raw: bytes, store: DatasetStore) -> dict:
    dataset_id, files, metadata = build_frozen_packet(raw)
    return store.publish(dataset_id, files, metadata)
