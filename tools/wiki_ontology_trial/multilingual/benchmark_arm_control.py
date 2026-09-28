"""Start/stop one fixed H200 benchmark arm, never the source-unit measurement."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen


ARM_COUNT = {"A": 1, "B2": 2, "B3": 3}
ARM_FRACTION = {"A": 0.85, "B2": 0.42, "B3": 0.28}
ARM_SEQS = {"A": 6, "B2": 3, "B3": 2}


def health(port: int) -> bool:
    try:
        with urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


def belongs(pid: int, model: Path, port: int) -> bool:
    try:
        cmd = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8")
    except FileNotFoundError:
        return False
    return "vllm" in cmd and " serve " in cmd and str(model) in cmd and f"--port {port}" in cmd


def owned_group(pid: int, model: Path, port: int) -> bool:
    try:
        return belongs(pid, model, port) and os.getpgid(pid) == pid
    except ProcessLookupError:
        return False


def pid_file(root: Path, arm: str, index: int) -> Path:
    return root / "setup" / f"{arm}-{index}.pid.json"


def stop(root: Path, arm: str) -> None:
    for index in reversed(range(ARM_COUNT[arm])):
        path = pid_file(root, arm, index)
        if not path.exists():
            continue
        record = json.loads(path.read_text())
        pid, port, model = record["pid"], record["port"], Path(record["model"])
        if owned_group(pid, model, port):
            os.killpg(pid, signal.SIGTERM)
            for _ in range(30):
                if not belongs(pid, model, port) and not health(port):
                    break
                time.sleep(1)
            else:
                if not owned_group(pid, model, port):
                    raise RuntimeError(f"Launcher identity changed during stop: {pid}; inspect PID record")
                os.killpg(pid, signal.SIGKILL)
                for _ in range(10):
                    if not belongs(pid, model, port) and not health(port):
                        break
                    time.sleep(1)
                else:
                    raise RuntimeError(f"Owned benchmark server still alive after bounded stop: {pid}")
        elif health(port):
            # A child server may outlive its launcher. Preserve the PID record
            # and require inspection rather than losing ownership evidence.
            raise RuntimeError(f"Port still healthy without verified launcher: {port}; inspect PID record")
        path.unlink()


def start(args) -> None:
    report = json.loads(args.preflight.read_text())
    if report["unit_count"] != 100 or report["selection_sha256"] != args.selection_sha256:
        raise ValueError("Fixed input preflight missing or changed")
    model_len = int(report["configured_model_len"])
    if model_len < int(report["required_model_len"]):
        raise ValueError("Model length would truncate a prompt")
    args.root.joinpath("setup").mkdir(parents=True, exist_ok=True)
    if any(pid_file(args.root, args.arm, i).exists() for i in range(ARM_COUNT[args.arm])):
        raise RuntimeError("Arm already has recorded processes; inspect/stop first")
    ports = [args.first_port + i for i in range(ARM_COUNT[args.arm])]
    if any(health(port) for port in ports):
        raise RuntimeError("Benchmark port already in use")
    model = args.base_model if args.arm == "A" else args.fp8_model
    name = "benchmark-bf16" if args.arm == "A" else "benchmark-fp8"
    try:
        for index, port in enumerate(ports):
            command = [str(args.vllm), "serve", str(model), "--host", "127.0.0.1",
                       "--port", str(port), "--served-model-name", name,
                       "--tokenizer", str(args.base_model), "--dtype", "bfloat16",
                       "--kv-cache-dtype", "bfloat16", "--max-model-len", str(model_len),
                       "--max-num-seqs", str(ARM_SEQS[args.arm]),
                       "--gpu-memory-utilization", str(ARM_FRACTION[args.arm]),
                       "--language-model-only"]
            log = args.root / "setup" / f"{args.arm}-{index}.vllm.log"
            with log.open("ab") as output:
                process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT,
                                           start_new_session=True, env={**os.environ,
                                           "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
            pid_file(args.root, args.arm, index).write_text(json.dumps(
                {"pid": process.pid, "port": port, "model": str(model),
                 "command": command, "log": str(log)}, indent=2) + "\n")
            deadline = time.monotonic() + args.start_timeout
            while time.monotonic() < deadline:
                if health(port):
                    break
                if process.poll() is not None:
                    raise RuntimeError(f"vLLM exited before healthy: arm={args.arm} index={index} rc={process.returncode}")
                time.sleep(3)
            else:
                raise TimeoutError(f"vLLM health timeout: arm={args.arm} index={index}")
            print(json.dumps({"arm": args.arm, "engine_index": index, "pid": process.pid,
                              "port": port, "gpu_memory_utilization": ARM_FRACTION[args.arm],
                              "max_model_len": model_len, "health": "ok"}), flush=True)
    except Exception:
        stop(args.root, args.arm)
        raise


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["start", "stop"])
    p.add_argument("--arm", choices=ARM_COUNT, required=True)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--preflight", type=Path)
    p.add_argument("--selection-sha256", default="45f58bccc92f7b0455bd3c7902da200c24b579d3b706a495721132eeb9b856f0")
    p.add_argument("--vllm", type=Path)
    p.add_argument("--base-model", type=Path)
    p.add_argument("--fp8-model", type=Path)
    p.add_argument("--first-port", type=int, default=8101)
    p.add_argument("--start-timeout", type=int, default=900)
    return p


if __name__ == "__main__":
    args = parser().parse_args()
    if args.command == "start":
        if not all((args.preflight, args.vllm, args.base_model, args.fp8_model)):
            raise ValueError("Start needs preflight, vLLM executable and both model paths")
        start(args)
    else:
        stop(args.root, args.arm)
