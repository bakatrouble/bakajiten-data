#!/usr/bin/env python3
"""Gzip packed artifacts + write manifest.json.

Consumes the `pack-data --json` summary lines (one JSON object per
artifact: {artifact, path, records, bytes, version}) and the *.bin
files they describe. Writes *.bin.gz next to them (level 6, mtime 0
for determinism) and OUT/manifest.json in the schema the bakajiten
web app reads ({version, build_date, files: {name: {size, gz,
version, sha256, sources, last_changed_manifest}}}).

`sha256` is the content hash of the packed artifact — the stable
change signal. Upstream `version` strings are provenance only: some
(mtime fallbacks) move every day even for byte-identical output, so
neither the skip check nor clients may treat them as change
signals. Dataset names per artifact are static (pack-data reports
one combined version string per artifact).

`last_changed_manifest` links the release manifest where that
file's content last changed: compared against --prev, identical
sha256 carries the old link forward, changed (or new) files point
at --manifest-url, the manifest being written.

Usage: python3 pack.py --summaries SUMMARIES --out OUT
    [--prev PREV_MANIFEST] [--manifest-url URL]
"""

import argparse
import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

# Artifact filename -> source datasets that went into it.
DATASETS = {
    "templates.bin": ["kanjivg"],
    "kanji.bin": ["kanjidic2", "kanjivg", "kradfile"],
    "jmdict.bin": ["jmdict"],
    "jmnedict.bin": ["jmnedict"],
    "kokugo.bin": ["kaikki", "wordnet", "jmdict"],
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summaries", required=True, help="pack-data --json output (JSON lines)")
    ap.add_argument("--out", default="out")
    ap.add_argument("--prev", default="", help="previous release manifest.json (for change links)")
    ap.add_argument("--manifest-url", default="", help="URL of the manifest being written")
    args = ap.parse_args()

    out = Path(args.out)
    prev_files = {}
    if args.prev:
        try:
            prev_files = json.load(open(args.prev))["files"]
        except (OSError, ValueError, KeyError):
            pass
    summaries = {}
    with open(args.summaries) as f:
        for line in f:
            line = line.strip()
            if line.startswith("{"):
                s = json.loads(line)
                summaries[Path(s["path"]).name] = s

    manifest = {
        "version": 1,
        "build_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "files": {},
    }
    for src in sorted(out.glob("*.bin")):
        dst = src.with_suffix(src.suffix + ".gz")
        digest = hashlib.sha256()
        with open(src, "rb") as f_in, open(dst, "wb") as f_out:
            with gzip.GzipFile(filename="", mode="wb", compresslevel=6, fileobj=f_out, mtime=0) as gz:
                while chunk := f_in.read(1 << 20):
                    digest.update(chunk)
                    gz.write(chunk)
        s = summaries.get(src.name, {})
        version = s.get("version", "")
        sha = digest.hexdigest()
        prev = prev_files.get(src.name, {})
        if prev.get("sha256") == sha and prev.get("last_changed_manifest"):
            link = prev["last_changed_manifest"]
        else:
            link = args.manifest_url
        manifest["files"][src.name] = {
            "size": s.get("bytes", src.stat().st_size),
            "gz": dst.stat().st_size,
            "version": version,
            "sha256": sha,
            "sources": DATASETS.get(src.name, []),
            "last_changed_manifest": link,
        }
        print(f"{src.name}: {src.stat().st_size} -> {dst.stat().st_size} [{version}]")
    (out / "manifest.json").write_text(json.dumps(manifest))
    print("manifest.json written")


if __name__ == "__main__":
    main()
