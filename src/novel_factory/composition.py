"""The composition root chooses adapters; core contracts do not."""
from pathlib import Path

from novel_factory.style.sqlite_store import SQLiteAnalysisStore
from novel_factory.style.workflow import AnalysisWorkflow
from novel_factory.style.legacy_release import accepted_release, legacy_status
from novel_factory.style.legacy_sqlite import SQLiteLegacyStore
from novel_factory.style.dataset_release import canonical, frozen_style_packet, release_dataset, sha
from novel_factory.style.dataset_sqlite import SQLiteDatasetStore
from novel_factory.style.training_contract import request_attempt
from novel_factory.style.training_sqlite import SQLiteTrainingStore


def analysis_workflow(db: Path | str) -> AnalysisWorkflow:
    return AnalysisWorkflow(SQLiteAnalysisStore(db))


def read_accepted_release(db_path: Path | str, import_id: str) -> dict:
    """Public, fixed-release reader for viewer/export; no legacy file fallback."""
    return accepted_release(SQLiteLegacyStore(db_path), import_id)


def read_legacy_status(db_path: Path | str, import_id: str,
                       work_id: str | None = None,
                       selection_id: str | None = None) -> list[dict]:
    return legacy_status(SQLiteLegacyStore(db_path), import_id, work_id, selection_id)


def publish_dataset_release(db_path: Path | str, import_id: str, role: str) -> dict:
    return release_dataset(SQLiteDatasetStore(db_path), import_id, role)


def read_dataset_release(db_path: Path | str, release_id: str) -> dict:
    return SQLiteDatasetStore(db_path).read_dataset(release_id)


def prepare_style_packet(db_path: Path | str, release_id: str) -> dict:
    return frozen_style_packet(SQLiteDatasetStore(db_path), release_id)


def request_training_attempt(db_path: Path | str, request: dict) -> dict:
    return request_attempt(SQLiteTrainingStore(db_path), request)


def import_training_result(db_path: Path | str, result: dict) -> dict:
    return SQLiteTrainingStore(db_path).import_attempt_result(result, sha(canonical(result)))


def read_training_run(db_path: Path | str, run_id: str) -> dict:
    return SQLiteTrainingStore(db_path).read_run(run_id)
