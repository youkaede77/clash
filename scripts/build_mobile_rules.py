"""Filter only ASN-wide matches from three explicit public mobile rule sources."""
import argparse
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path
from build_regions import download

SOURCES = {
    'Facebook_Do_Resolve': 'https://cdn.jsdelivr.net/gh/blackmatrix7/ios_rule_script@latest/rule/Clash/Facebook/Facebook.yaml',
    'OpenAI_Do_Resolve': 'https://cdn.jsdelivr.net/gh/blackmatrix7/ios_rule_script@latest/rule/Clash/OpenAI/OpenAI.yaml',
    'Telegram_Do_Resolve': 'https://cdn.jsdelivr.net/gh/blackmatrix7/ios_rule_script@latest/rule/Clash/Telegram/Telegram.yaml',
}
ASN = re.compile(r'''^\s*-\s*(?P<quote>['"]?)IP-ASN\s*,\s*\d+(?:\s*,\s*no-resolve)?(?P=quote)\s*(?:\#.*)?$''', re.I)
ACTIVE_ASN = re.compile(r'''^\s*-\s*['"]?(?:SRC-)?IP-ASN\s*,''', re.I)

def filter_asn(text):
    if not re.search(r'^payload:\s*(?:#.*)?$', text, re.M):
        raise ValueError('Expected block-style public rule payload')
    kept, removed = [], []
    for line in text.splitlines(keepends=True):
        if ASN.fullmatch(line.rstrip('\r\n')):
            removed.append(line.rstrip('\r\n'))
        elif ACTIVE_ASN.match(line):
            raise ValueError('Unrecognized ASN rule syntax; refusing unsafe output')
        else:
            kept.append(line)
    output = ''.join(kept)
    if not re.search(r'^\s*-\s*\S', output, re.M):
        raise ValueError('Refusing an empty rule set')
    return output, removed

def build(output, cache=None):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = {'filter': 'remove IP-ASN only; preserve all other lines and ordering', 'providers': {}}
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        stage = Path(temp)
        for name, url in SOURCES.items():
            path = stage / (name + '.source.yaml')
            if cache:
                shutil.copyfile(Path(cache) / (name + '.upstream.yaml'), path)
            else:
                download(url, path)
            original = path.read_bytes()
            cleaned, removed = filter_asn(original.decode('utf-8'))
            content = cleaned.encode('utf-8')
            (stage / (name + '.yaml')).write_bytes(content)
            manifest['providers'][name] = {'source_url': url, 'source_sha256': hashlib.sha256(original).hexdigest(), 'removed_asn_rules': removed, 'sha256': hashlib.sha256(content).hexdigest()}
        (stage / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        output.mkdir(exist_ok=True)
        for name in [*(n + '.yaml' for n in SOURCES), 'manifest.json']:
            shutil.copyfile(stage / name, output / name)
    return manifest

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='rules/mobile')
    parser.add_argument('--cache', help='Local public source snapshots for offline validation')
    args = parser.parse_args()
    build(args.output, args.cache)
