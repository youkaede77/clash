"""Compile public rule sources; never reads a client config or node subscription."""
import argparse
import ipaddress
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from build_regions import coverage, download, merge, sha, small_window_mrs


def validate_sources(sources, region_names):
    if set(sources) != {'regions', 'providers'}:
        raise ValueError('Unexpected source sections')
    if any(not names for names in sources['regions'].values()):
        raise ValueError('Empty region group')
    flattened = [n for names in sources['regions'].values() for n in names]
    if len(flattened) != len(set(flattened)) or set(flattened) != set(region_names):
        raise ValueError('Region grouping must contain every region exactly once')
    for name in [*sources['regions'], *sources['providers']]:
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name):
            raise ValueError('Unsafe output name')
    if set(sources['regions']) & set(sources['providers']):
        raise ValueError('Duplicate output name')
    for source in sources['providers'].values():
        u = urlsplit(source['url'])
        if u.scheme != 'https' or u.hostname not in {'cdn.jsdelivr.net', 'raw.githubusercontent.com', 'www.cloudflare.com'} or u.query or u.username or u.password:
            raise ValueError('Only explicit public HTTPS rule sources are allowed')
        if source['behavior'] not in {'domain', 'ipcidr'} or source.get('format', 'yaml') not in {'yaml', 'text'}:
            raise ValueError('Unsupported rule semantics')


def convert(core, behavior, fmt, src, dst):
    subprocess.run([core, 'convert-ruleset', behavior, fmt, str(src), str(dst)],
                   check=True, stdout=subprocess.DEVNULL)


def cidrs(path):
    return [ipaddress.ip_network(x) for x in path.read_text().splitlines()
            if x and not x.startswith('#')]


def compile_public(core, behavior, fmt, src, output, stage):
    # The same Mihomo parser compiles domain YAML/text and loads it at runtime.
    # Verify a canonical text round trip too, before changing compression.
    convert(core, behavior, fmt, src, output)
    text = stage / (output.stem + '.roundtrip.txt')
    check = stage / (output.stem + '.check.mrs')
    second = stage / (output.stem + '.second.txt')
    convert(core, behavior, 'mrs', output, text)
    convert(core, behavior, 'text', text, check)
    convert(core, behavior, 'mrs', check, second)
    if text.read_bytes() != second.read_bytes():
        raise ValueError('Canonical rule round trip changed semantics')
    if not any(x and not x.startswith('#') for x in text.read_text().splitlines()):
        raise ValueError('Refusing empty compiled provider')
    output.write_bytes(small_window_mrs(output.read_bytes()))
    return text


def build(args):
    root = Path(__file__).resolve().parents[1]
    sources = json.loads((root / 'compact-sources.json').read_text())
    region_names = json.loads((root / 'region-sources.json').read_text())
    validate_sources(sources, region_names)
    cache = json.loads(Path(args.cache_map).read_text()) if args.cache_map else None
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    manifest = {'zstd_window_bytes': 65536, 'regions': {}, 'providers': {}}
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        stage = Path(tmp)
        published = stage / 'result'
        published.mkdir()
        for name, names in sources['regions'].items():
            nets = []
            hashes = {}
            for original in names:
                source = Path(args.regions) / (original + '.mrs')
                text = stage / (original + '.source.txt')
                convert(args.mihomo, 'ipcidr', 'mrs', source, text)
                nets.extend(cidrs(text))
                hashes[original] = sha(source.read_bytes())
            source = stage / (name + '.merged.txt')
            source.write_text(''.join(str(n) + '\n' for n in merge(nets)))
            output = published / (name + '.mrs')
            roundtrip = compile_public(args.mihomo, 'ipcidr', 'text', source, output, stage)
            if coverage(cidrs(roundtrip)) != coverage(nets):
                raise ValueError('Merged region coverage changed')
            manifest['regions'][name] = {'source_regions': hashes, 'exact_coverage_verified': True,
                                        'mrs_bytes': output.stat().st_size, 'mrs_sha256': sha(output.read_bytes())}
        for name, spec in sources['providers'].items():
            source = stage / (name + '.input')
            if cache:
                shutil.copy2(cache[name], source)
            else:
                download(spec['url'], source)
            output = published / (name + '.mrs')
            compile_public(args.mihomo, spec['behavior'], spec.get('format', 'yaml'), source, output, stage)
            manifest['providers'][name] = {**spec, 'source_sha256': sha(source.read_bytes()),
                                          'mrs_bytes': output.stat().st_size, 'mrs_sha256': sha(output.read_bytes()),
                                          'canonical_roundtrip_verified': True}
        (published / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        # A failed build never touches the previously published output directory.
        out.mkdir(exist_ok=True)
        for p in published.iterdir():
            shutil.copy2(p, out / p.name)
    print('Verified', len(manifest['regions']), 'regional groups and', len(manifest['providers']), 'public providers')
    return manifest


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--mihomo', required=True)
    p.add_argument('--regions', default='rules/regions')
    p.add_argument('--output', default='rules/compact')
    p.add_argument('--cache-map', help='Offline public-rule cache for local verification only')
    build(p.parse_args())
