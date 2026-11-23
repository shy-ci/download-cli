"""A small, resumable command line downloader powered by aria2."""

from __future__ import annotations

import argparse
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def sha256_digest(value: str) -> str:
    if not re.fullmatch(r"[0-9a-fA-F]{64}", value):
        raise argparse.ArgumentTypeError("must be a 64-character hexadecimal SHA-256 digest")
    return value.lower()


def filename_from_url(url: str) -> str:
    name = PurePosixPath(unquote(urlsplit(url).path)).name
    if not name or name in {".", ".."}:
        raise ValueError("URL has no filename; specify one with --output")
    return name


def build_command(args: argparse.Namespace, aria2: str, target: Path) -> list[str]:
    command = [
        aria2,
        "--continue=true",
        "--auto-file-renaming=false",
        "--allow-overwrite=false",
        "--file-allocation=none",
        f"--max-connection-per-server={args.connections}",
        f"--split={args.connections}",
        f"--min-split-size={args.min_split_size}",
        f"--max-tries={args.retries}",
        f"--retry-wait={args.retry_wait}",
        f"--connect-timeout={args.connect_timeout}",
        f"--timeout={args.timeout}",
        "--summary-interval=10",
        f"--dir={target.parent}",
        f"--out={target.name}",
    ]
    if args.max_speed:
        command.append(f"--max-overall-download-limit={args.max_speed}")
    if args.sha256:
        command.append(f"--checksum=sha-256={args.sha256}")
    command.append(args.url)
    return command


def is_hls_url(url: str) -> bool:
    return urlsplit(url).path.lower().endswith(".m3u8")


def build_hls_command(args: argparse.Namespace, target: Path) -> list[str]:
    output_template = target.with_suffix("").with_name(target.stem + ".%(ext)s")
    command = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--continue",
        "--concurrent-fragments",
        str(args.connections),
        "--retries",
        str(args.retries),
        "--fragment-retries",
        str(args.retries),
        "--retry-sleep",
        f"fragment:{args.retry_wait}",
        "--socket-timeout",
        str(args.timeout),
        "--output",
        str(output_template),
    ]
    if args.max_speed:
        command.extend(["--limit-rate", args.max_speed])
    command.append(args.url)
    return command


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="download-cli",
        description="Download direct files or HLS streams with concurrency and resume support.",
    )
    parser.add_argument("url", help="HTTP or HTTPS download URL")
    parser.add_argument("-o", "--output", type=Path, help="output filename or path (default: URL filename)")
    parser.add_argument("-d", "--directory", type=Path, default=Path.cwd(), help="download directory")
    parser.add_argument("-c", "--connections", type=positive_int, default=8, help="parallel connections or HLS fragments (default: 8)")
    parser.add_argument("--min-split-size", default="1M", help="minimum segment size (default: 1M)")
    parser.add_argument("--retries", type=positive_int, default=20, help="attempts per segment (default: 20)")
    parser.add_argument("--retry-wait", type=positive_int, default=5, help="seconds between retries (default: 5)")
    parser.add_argument("--connect-timeout", type=positive_int, default=30, help="connection timeout in seconds")
    parser.add_argument("--timeout", type=positive_int, default=60, help="idle timeout in seconds")
    parser.add_argument("--max-speed", help="optional total speed cap, e.g. 2M or 500K")
    parser.add_argument("--sha256", type=sha256_digest, help="expected SHA-256 digest; verify after download")
    parser.add_argument("--verify-dmg", action="store_true", help="verify a macOS DMG with hdiutil after download")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    parsed = urlsplit(args.url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        parser.error("URL must be HTTP or HTTPS")
    hls = is_hls_url(args.url)
    if hls:
        if args.sha256:
            parser.error("--sha256 is not supported for HLS streams")
        if args.verify_dmg:
            parser.error("--verify-dmg is not supported for HLS streams")
        if importlib.util.find_spec("yt_dlp") is None:
            parser.exit(2, "yt-dlp is required for .m3u8 streams. Install it with: py -m pip install -U yt-dlp\n")
        name = args.output or Path(filename_from_url(args.url))
        target = (args.directory / name).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading HLS stream with {args.connections} parallel fragments to {target.parent}", flush=True)
        result = subprocess.run(build_hls_command(args, target), check=False)
        if result.returncode:
            print(f"HLS download failed (yt-dlp exit code {result.returncode}). Run the same command to resume.", file=sys.stderr)
            return result.returncode
        print(f"HLS download complete: {target.parent / (target.stem + '.*')}")
        return 0

    aria2 = shutil.which("aria2c")
    if aria2 is None:
        if sys.platform == "darwin":
            hint = "Install with: brew install aria2"
        elif sys.platform == "win32":
            hint = "Get aria2c.exe from https://github.com/aria2/aria2/releases and add its folder to PATH"
        else:
            hint = "Install aria2 with your package manager"
        parser.exit(2, f"aria2c is required. {hint}.\n")
    try:
        name = args.output or Path(filename_from_url(args.url))
    except ValueError as error:
        parser.error(str(error))
    target = (args.directory / name).expanduser().resolve()
    if args.verify_dmg and (sys.platform != "darwin" or target.suffix.lower() != ".dmg"):
        parser.error("--verify-dmg requires macOS and a .dmg output file")
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading to {target}", flush=True)
    result = subprocess.run(build_command(args, aria2, target), check=False)
    if result.returncode:
        print(f"Download failed (aria2c exit code {result.returncode}). Run the same command to resume.", file=sys.stderr)
        return result.returncode
    if not target.is_file():
        print("Download reported success but the output file is missing.", file=sys.stderr)
        return 1
    if args.verify_dmg:
        verification = subprocess.run(["hdiutil", "verify", str(target)], check=False)
        if verification.returncode:
            print("DMG verification failed.", file=sys.stderr)
            return verification.returncode
    print(f"Complete: {target} ({target.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
