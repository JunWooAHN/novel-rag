import importlib.metadata
import platform
import shutil
import subprocess

from toy_tune.domain.errors import ValidationError


class LocalEnvironmentInspector:
    def inspect(self, probe_gpu: bool = False) -> dict:
        packages = {}
        for name in ("torch", "transformers", "peft", "trl", "mlx", "mlx-lm"):
            try:
                packages[name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                packages[name] = None
        report = {"schema_version": 1, "python": platform.python_version(),
                  "system": platform.system(), "machine": platform.machine(), "packages": packages,
                  "gpu_probe": "not_requested", "training_ready": False,
                  "note": "Inventory only. Model, accelerator and checkpoint compatibility remain unverified."}
        if probe_gpu:
            if not shutil.which("nvidia-smi"):
                raise ValidationError("nvidia-smi is unavailable in this execution environment.")
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=15, check=True)
            except (OSError, subprocess.SubprocessError):
                raise ValidationError("GPU inventory command failed; raw output was omitted.") from None
            report["gpu_probe"] = result.stdout.strip().splitlines()
        return report
