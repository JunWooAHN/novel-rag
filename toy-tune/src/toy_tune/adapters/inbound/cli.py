import argparse


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="toy-tune", description="Portable experiment bootstrap (CPU foundation).")
    commands = root.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="Inspect current machine without importing accelerator libraries.")
    doctor.add_argument("--runtime", required=True)
    doctor.add_argument("--workspace")
    doctor.add_argument("--probe-gpu", action="store_true")
    prepare = commands.add_parser("prepare", help="Validate and publish a frozen source bundle as a dataset.")
    prepare.add_argument("--runtime", required=True)
    prepare.add_argument("--workspace")
    prepare.add_argument("--source", required=True)
    prepare.add_argument("--split", required=True)
    prepare.add_argument("--allow-context-overlap", action="store_true")
    verify = commands.add_parser("verify-dataset", help="Verify all payload checksums of a published dataset.")
    verify.add_argument("--runtime", required=True)
    verify.add_argument("--workspace")
    verify.add_argument("--dataset-id", required=True)
    return root
