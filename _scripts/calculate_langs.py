#!/usr/bin/env python3
"""Write `_stats/languages.json` with each solution's primary language.

For each task, this script counts non-blank lines in recognized source files
inside `submission.tar.gz` and picks the language with the largest count. It
uses a local archive when available; otherwise it temporarily downloads the
archive referenced by `submission.tar.gz.url` and verifies its SHA-256.
"""

import argparse
import hashlib
import json
import os
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from pathlib import Path, PurePosixPath


RUN_DIR = Path(__file__).resolve().parent.parent
DOWNLOAD_TIMEOUT = 120
DOWNLOAD_ATTEMPTS = 6

# These identifiers match the language values used by ProgramBench task metadata.
EXTENSIONS = {
    ".c": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".h": "_c_header",
    ".hh": "cpp",
    ".hpp": "cpp",
    ".hxx": "cpp",
    ".go": "go",
    ".rs": "rs",
    ".hs": "hs",
    ".lhs": "hs",
    ".java": "java",
    ".py": "py",
    ".pyi": "py",
    ".pyw": "py",
    ".js": "js",
    ".jsx": "js",
    ".mjs": "js",
    ".cjs": "js",
    ".ts": "ts",
    ".tsx": "ts",
    ".sh": "sh",
    ".bash": "sh",
    ".zsh": "sh",
    ".rb": "rb",
    ".php": "php",
    ".cs": "cs",
    ".lua": "lua",
    ".zig": "zig",
    ".nim": "nim",
    ".ex": "ex",
    ".exs": "ex",
    ".erl": "erl",
    ".hrl": "erl",
    ".pl": "pl",
    ".pm": "pl",
    ".r": "r",
    ".scala": "scala",
    ".clj": "clj",
    ".cljs": "clj",
    ".fs": "fs",
    ".fsx": "fs",
    ".ml": "ml",
    ".mli": "ml",
    ".dart": "dart",
    ".v": "v",
    ".vsh": "v",
    ".jl": "jl",
    ".sol": "sol",
    ".swift": "swift",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".m": "objc",
    ".mm": "objc",
}

IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "vendor",
    "target",
    "build",
    "dist",
    "__pycache__",
}


def language_loc(archive: Path) -> dict[str, int]:
    """Count non-blank source lines by language without extracting the archive."""
    counts: Counter[str] = Counter()
    with tarfile.open(archive, "r:*") as tar:
        for member in tar:
            if not member.isfile():
                continue
            path = PurePosixPath(member.name)
            if any(part.lower() in IGNORED_DIRS for part in path.parts):
                continue
            language = "cpp" if path.suffix == ".C" else EXTENSIONS.get(path.suffix.lower())
            if language is None:
                continue
            source = tar.extractfile(member)
            if source is not None:
                counts[language] += sum(1 for line in source if line.strip())

    # Attribute shared C/C++ headers to whichever implementation has more lines.
    header_lines = counts.pop("_c_header", 0)
    if header_lines:
        counts["cpp" if counts["cpp"] > counts["c"] else "c"] += header_lines
    return dict(counts)


def primary_language(counts: dict[str, int]) -> str:
    if not counts:
        return "unknown"
    return min(counts, key=lambda language: (-counts[language], language))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_archive(archive: Path, checksum: Path) -> None:
    if not checksum.exists():
        return
    expected = checksum.read_text().split()[0].lower()
    actual = sha256(archive)
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch: expected {expected}, got {actual}")


def download(url: str, destination: Path) -> None:
    """Download an artifact, retrying rate limits and transient service errors."""
    headers = {"User-Agent": "programbench-language-stats/1"}
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    for attempt in range(DOWNLOAD_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response, destination.open("wb") as out:
                while chunk := response.read(1024 * 1024):
                    out.write(chunk)
            return
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            retryable = not isinstance(error, urllib.error.HTTPError) or error.code == 429 or error.code >= 500
            if not retryable or attempt == DOWNLOAD_ATTEMPTS - 1:
                raise
            retry_after = error.headers.get("Retry-After") if isinstance(error, urllib.error.HTTPError) else None
            delay = int(retry_after) if retry_after and retry_after.isdigit() else min(2**attempt, 30)
            print(f"Retrying {url} in {delay}s ({error})")
            time.sleep(delay)


@contextmanager
def solution_archive(task_dir: Path):
    """Yield a verified local path for one task's solution archive."""
    archive = task_dir / "submission.tar.gz"
    checksum = task_dir / "submission.tar.gz.sha256"
    if archive.exists():
        verify_archive(archive, checksum)
        yield archive
        return

    pointer = task_dir / "submission.tar.gz.url"
    if not pointer.exists():
        raise FileNotFoundError("no submission.tar.gz or submission.tar.gz.url")
    url = pointer.read_text().strip()
    if urllib.parse.urlparse(url).scheme not in ("http", "https"):
        raise ValueError(f"refusing to fetch non-HTTP URL: {url!r}")

    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=f"{task_dir.name}-", suffix=".tar.gz", delete=False) as file:
            temporary = Path(file.name)
        download(url, temporary)
        verify_archive(temporary, checksum)
        yield temporary
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def classify(task_dir: Path) -> tuple[str, str]:
    with solution_archive(task_dir) as archive:
        return task_dir.name, primary_language(language_loc(archive))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=min(8, os.cpu_count() or 1), help="parallel downloads")
    args = parser.parse_args()

    tasks = sorted(
        path
        for path in RUN_DIR.iterdir()
        if path.is_dir()
        and not path.name.startswith("_")
        and ((path / "submission.tar.gz").exists() or (path / "submission.tar.gz.url").exists())
    )
    if not tasks:
        parser.error("no solution archives or URL pointers found")

    languages: dict[str, str] = {}
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as executor:
        pending = {executor.submit(classify, task): task for task in tasks}
        for future in as_completed(pending):
            task = pending[future]
            try:
                instance_id, language = future.result()
            except Exception as error:
                failures.append(f"{task.name}: {error}")
                continue
            languages[instance_id] = language
            print(f"{instance_id}: {language}")

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        raise SystemExit(f"Failed to classify {len(failures)} of {len(tasks)} instance(s)")

    stats_dir = RUN_DIR / "_stats"
    stats_dir.mkdir(exist_ok=True)
    (stats_dir / "languages.json").write_text(json.dumps(languages, indent=2, sort_keys=True) + "\n")
    print(f"Wrote _stats/languages.json for {len(languages)} instance(s)")


if __name__ == "__main__":
    main()
