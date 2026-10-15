"""Build public regional IP sets only; never reads a Clash client configuration."""
import argparse, hashlib, ipaddress, json, re, shutil, subprocess, tempfile
from pathlib import Path
from geoip_reader import read_geo


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parse_region(text):
    codes=[]
    for raw in text.splitlines():
        line=raw.split('#',1)[0].strip()
        if not line or line=='payload:': continue
        match=re.fullmatch(r'-\s*GEOIP\s*,\s*([A-Za-z]{2})\s*',line)
        if not match: raise ValueError('Unexpected regional rule: '+line)
        code=match[1].lower()
        if code not in codes: codes.append(code)  # Repeated GEOIP rules have the same union.
    if not codes: raise ValueError('Empty region')
    return sorted(codes)


def coverage(nets):
    """Independent interval-union representation for equality checks."""
    spans=sorted((n.version,int(n.network_address),int(n.broadcast_address)) for n in nets)
    result=[]
    for version,start,end in spans:
        if result and result[-1][0]==version and start<=result[-1][2]+1:
            result[-1]=(version,result[-1][1],max(end,result[-1][2]))
        else:result.append((version,start,end))
    return result


def merge(nets):
    result=[n for version in (4,6) for n in ipaddress.collapse_addresses(n for n in nets if n.version==version)]
    if coverage(nets)!=coverage(result):raise ValueError('Coverage changed while merging')
    return result


def download(url, target):
    if not url.startswith('https://'):raise ValueError('HTTPS required')
    subprocess.run(['curl','--fail','--location','--silent','--show-error','--retry','3','--max-time','120',url,'-o',str(target)],check=True)


def build(args):
    root=Path(__file__).resolve().parents[1]
    sources=json.loads((root/'region-sources.json').read_text())
    if len(sources)!=16:raise ValueError('Expected all 16 regions')
    data=Path(args.geoip).read_bytes()
    geo=read_geo(data)
    version=subprocess.check_output([args.mihomo,'-v'],text=True).strip()
    manifest={'geoip_url':args.source_url,'geoip_sha256':sha(data),'converter':version,'regions':{}}
    mapping=json.loads(Path(args.mapping).read_text()) if args.mapping else None
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    # No published outputs are changed until every region and round trip passes.
    with tempfile.TemporaryDirectory(dir=out.parent) as scratch:
        stage=Path(scratch); published=stage/'result';published.mkdir()
        for name,url in sources.items():
            if not re.fullmatch(r'GeoRouting_[A-Za-z_]+_GeoIP',name):raise ValueError('Invalid name')
            if mapping is None:
                raw=stage/(name+'.yaml');download(url,raw)
                codes=parse_region(raw.read_text());mapping_sha=sha(raw.read_bytes())
            else:
                codes=mapping[name];mapping_sha=None
            missing=set(codes)-geo.keys()
            if missing:raise ValueError('Missing country data: '+','.join(sorted(missing)))
            if any(not geo[code] for code in codes):raise ValueError('Empty country data in '+name)
            nets=[n for code in codes for n in geo[code]]
            if not nets:raise ValueError('Empty IP set: '+name)
            merged=merge(nets)
            source=stage/(name+'.txt');source.write_text(''.join(str(n)+'\n' for n in merged))
            mrs=published/(name+'.mrs');roundtrip=stage/(name+'.roundtrip.txt')
            subprocess.run([args.mihomo,'convert-ruleset','ipcidr','text',str(source),str(mrs)],check=True,stdout=subprocess.DEVNULL)
            subprocess.run([args.mihomo,'convert-ruleset','ipcidr','mrs',str(mrs),str(roundtrip)],check=True,stdout=subprocess.DEVNULL)
            restored=[ipaddress.ip_network(line) for line in roundtrip.read_text().splitlines() if line and not line.startswith('#')]
            if coverage(restored)!=coverage(nets):raise ValueError('MRS round trip changed coverage: '+name)
            manifest['regions'][name]={'countries':codes,'mapping_url':url,'mapping_sha256':mapping_sha,'input_prefixes':len(nets),'merged_prefixes':len(merged),'mrs_bytes':mrs.stat().st_size,'mrs_sha256':sha(mrs.read_bytes()),'exact_coverage_verified':True}
            print(name,len(nets),'->',len(merged),'prefixes,',mrs.stat().st_size,'bytes',flush=True)
        (published/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        out.mkdir(exist_ok=True)
        for p in published.iterdir():shutil.copy2(p,out/p.name)
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--geoip',required=True);p.add_argument('--mihomo',required=True)
    p.add_argument('--source-url',required=True);p.add_argument('--output',default='rules/regions')
    p.add_argument('--mapping',help='Offline mapping snapshot, for local verification only')
    build(p.parse_args())
