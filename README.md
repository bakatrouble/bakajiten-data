# Bakajiten data releases

Packed dictionary artifacts (`*.bin.gz` + `manifest.json`), rebuilt
daily from upstream sources with the
[`bakajiten-utils`](https://github.com/bakatrouble/bakajiten) image
(`utils/Dockerfile` in that repo, published to
`ghcr.io/bakatrouble/bakajiten-utils`). The bakajiten apps never pack
data themselves — Qt CI, the AppImage deploy, and the web app all
consume these releases.

## Release layout

Each dated release (`data-YYYYMMDD`) holds:

- `jmdict.bin.gz`, `jmnedict.bin.gz`, `kanji.bin.gz`,
  `templates.bin.gz`, `kokugo.bin.gz` — gzip level 6, mtime 0
- `manifest.json` — `{version: 1, build_date, files: {name: {size,
  gz, version, sha256, sources, last_changed_manifest}}}` with
  raw/gzip byte sizes (what the web app's consent screen reads), the
  build date, per-artifact versions straight from `pack-data --json`
  (`kanjidic2` `database_version`, JMdict header date, KanjiVG
  `version.txt`; unversioned snapshots report their source mtime),
  and the sha256 of the packed bytes. `sources` names the datasets
  that went into each artifact; `last_changed_manifest` links the
  release manifest where that file's content last changed
  (carried forward while its sha256 is unchanged). The release
  skip-check and the web app compare `sha256`: versions are
  provenance only, since some move daily without content changes.

A day with byte-identical output produces no release (the manifest
is compared against the latest release first).

## Sources

- EDRDG JMdict / JMnedict / kanjidic2 / radkfile / kradfile, KanjiVG
  — fetched fresh by `fetch-data` every run
- Kokugo: Kaikki jawiktionary + Japanese WordNet, imported by
  `fetch-data --fetch` (audited, deterministic)
- `jlpt.csv` — vendored JLPT snapshot (tanos.co.uk, CC-BY; the live
  site is gone, so this file is the source)

## Consuming

```sh
gh release download --pattern '*.bin.gz' --dir data --clobber
gunzip -k data/*.bin.gz
```

## Local pack

```sh
docker run --rm -v "$PWD:/work" ghcr.io/bakatrouble/bakajiten-utils \
    fetch-data --out-dir /work/sources
docker run --rm -v "$PWD:/work" ghcr.io/bakatrouble/bakajiten-utils \
    fetch-data --kokugo-out /work/sources/kokugo/kokugo.jsonl --fetch
docker run --rm -v "$PWD:/work" ghcr.io/bakatrouble/bakajiten-utils \
    pack-data --kanjivg /work/sources/kanjivg \
    --templates-out /work/out/templates.bin \
    --kanjidic /work/sources/kanjidic2.xml --kanji-out /work/out/kanji.bin \
    --jmdict /work/sources/JMdict.xml --jmdict-out /work/out/jmdict.bin \
    --jmnedict /work/sources/JMnedict.xml --jmnedict-out /work/out/jmnedict.bin \
    --kokugo /work/sources/kokugo/kokugo.jsonl --kokugo-out /work/out/kokugo.bin \
    --jlpt /work/jlpt.csv
```
