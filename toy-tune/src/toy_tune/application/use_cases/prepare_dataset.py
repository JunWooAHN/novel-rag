from toy_tune.application.ports.sources import SourceReader
from toy_tune.application.ports.stores import DatasetStore
from toy_tune.application.services.dataset_builder import build_dataset


def prepare_dataset(source: SourceReader, store: DatasetStore, counts: tuple[int, int, int],
                    allow_context_overlap: bool = False) -> dict:
    dataset_id, files, metadata = build_dataset(source.read(), counts, allow_context_overlap, source.snapshot())
    return store.publish(dataset_id, files, metadata)
