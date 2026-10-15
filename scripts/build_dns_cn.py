"""Recompress the official Clash Mi CN domain set without changing decoded bytes."""
import argparse
import io
import json
import tempfile
import zipfile
from pathlib import Path
from compression import zstd
from build_regions import download, sha, small_window_mrs

SOURCE = 'https://raw.githubusercontent.com/KaringX/clashmi/main/assets/datas/geosite.zip'


def convert_archive(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        info = archive.getinfo('cn.mrs')
        if info.file_size > 16 * 1024 * 1024:
            raise ValueError('Unexpected CN source size')
        original = archive.read(info)
    decoded = zstd.decompress(original)
    if not decoded.startswith(b'MRS\x01\x00'):
        raise ValueError('Expected domain MRS data')
    result = small_window_mrs(original)
    assert zstd.decompress(result) == decoded
    return result, {'source_url': SOURCE, 'archive_sha256': sha(data),
                    'source_mrs_sha256': sha(original), 'decoded_sha256': sha(decoded),
                    'mrs_sha256': sha(result), 'mrs_bytes': len(result),
                    'decoder_window_bytes': 65536, 'decoded_bytes_identical': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', help='Optional cached official public archive')
    parser.add_argument('--output', default='rules/dns-cn')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(args.archive) if args.archive else Path(tmp) / 'geosite.zip'
        if not args.archive:
            download(SOURCE, archive)
        data, manifest = convert_archive(archive.read_bytes())
        out = Path(args.output)
        out.mkdir(parents=True, exist_ok=True)
        (out / 'cn.mrs').write_bytes(data)
        (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print(json.dumps(manifest))


if __name__ == '__main__':
    main()
