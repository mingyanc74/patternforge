"""Fetch checksum-pinned public weights; optionally run an isolated Windows CPU model server."""

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path

MODEL_NAME = "Qwen3-4B-Q4_K_M.gguf"
MODEL_REVISION = "bc640142c66e1fdd12af0bd68f40445458f3869b"
MODEL_SHA256 = "7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5"
MODEL_URL = (
    "https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/"
    + MODEL_REVISION
    + "/"
    + MODEL_NAME
    + "?download=true"
)
RUNTIME_URL = (
    "https://github.com/ggml-org/llama.cpp/releases/download/b11669/llama-b11669-bin-win-cpu-x64.zip"
)
RUNTIME_SHA256 = "37b3efcf962847ca869745fd4ccf7f5e7e8dacfeff9fa3523b4ca8cdc66d632b"


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download_verified(url, destination, expected):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and checksum(destination) == expected:
        return
    partial = destination.with_suffix(destination.suffix + ".partial")
    print(f"Downloading {destination.name} from the official publisher...", flush=True)
    with urllib.request.urlopen(url, timeout=60) as response, partial.open("wb") as output:
        shutil.copyfileobj(response, output, length=1024 * 1024)
    if checksum(partial) != expected:
        raise SystemExit("Checksum mismatch. The downloaded file will not be used.")
    partial.replace(destination)


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-only", action="store_true", help="Only download verified model weights")
    parser.add_argument("--model-dir", type=Path, default=root / "data/models")
    parser.add_argument("--runtime-dir", type=Path, default=root / "data/model-runtime")
    parser.add_argument("--threads", type=int, default=min(4, os.cpu_count() or 2))
    args = parser.parse_args()
    model = args.model_dir.resolve() / MODEL_NAME
    download_verified(MODEL_URL, model, MODEL_SHA256)
    if args.download_only:
        print("Official model verified. No API subscription or model-service charge is required.")
        return
    if platform.system() != "Windows" or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise SystemExit("This native launcher supports Windows x64. Use compose.local-model.yml on Linux.")
    runtime_dir = args.runtime_dir.resolve()
    archive = runtime_dir / "llama-b11669-win.zip"
    download_verified(RUNTIME_URL, archive, RUNTIME_SHA256)
    # Only extract the verified official archive, and reject escaping member paths.
    with zipfile.ZipFile(archive) as package:
        for member in package.infolist():
            if not (runtime_dir / member.filename).resolve().is_relative_to(runtime_dir):
                raise SystemExit("Unsafe archive path rejected.")
        package.extractall(runtime_dir)
    executable = runtime_dir / "llama-server.exe"
    print("Starting real CPU inference at http://localhost:18089/v1 (loopback only).", flush=True)
    subprocess.run(
        [
            str(executable),
            "-m",
            str(model),
            "--alias",
            "patternforge-local",
            "--host",
            "localhost",
            "--port",
            "18089",
            "--ctx-size",
            "2048",
            "--threads",
            str(args.threads),
            "--parallel",
            "1",
            "--no-ui",
            "--no-slots",
            "--cors-origins",
            "localhost",
            "--temp",
            "0",
            "--reasoning",
            "off",
            "--no-repack",
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
