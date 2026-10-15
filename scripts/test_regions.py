import ipaddress
import unittest
import json,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from compression import zstd
from build_regions import build, small_window_mrs
from build_regions import coverage, merge, parse_region
from geoip_reader import fields, read_geo


def vi(n):
    result = bytearray()
    while n > 127:
        result.append((n & 127) | 128)
        n >>= 7
    result.append(n)
    return bytes(result)


def message(field, data):
    return vi(field * 8 + 2) + vi(len(data)) + data


def country(code, networks, inverse=False):
    body = message(1, code.encode())
    for cidr in networks:
        net = ipaddress.ip_network(cidr)
        body += message(2, message(1, net.network_address.packed) + b'\x10' + vi(net.prefixlen))
    if inverse:
        body += b'\x18\x01'
    return message(1, body)


class RegionTests(unittest.TestCase):
    def test_recompression_preserves_binary_payload_and_bounds_window(self):
        payload = bytes(range(256)) * 4096
        original = zstd.compress(payload)
        result = small_window_mrs(original)
        self.assertEqual(zstd.decompress(result), payload)
        self.assertFalse(result[4] & 32)
        descriptor = result[5]
        window = (1 << (10 + (descriptor >> 3))) * (8 + (descriptor & 7)) // 8
        self.assertLessEqual(window, 65536)
        self.assertTrue(result[4] & 4)  # Keep an integrity checksum.

    def test_recompression_rejects_corrupt_input(self):
        with self.assertRaises(zstd.ZstdError):
            small_window_mrs(b'not a zstd frame')

    def test_country_data_supports_both_families(self):
        nets = ['192.0.2.0/24', '2001:db8::/32']
        self.assertEqual(read_geo(country('US', nets)), {'us': [ipaddress.ip_network(n) for n in nets]})

    def test_inverse_duplicate_and_truncated_data_fail(self):
        valid = country('US', ['192.0.2.0/24'])
        for data in [valid + valid, valid[:-1], country('US', ['192.0.2.0/24'], True), b'\x00', b'\x0a\xff']:
            with self.subTest(data=data), self.assertRaises((ValueError, KeyError)):
                read_geo(data)

    def test_regional_mapping_rejects_changed_semantics(self):
        self.assertEqual(parse_region('payload:\n - GEOIP,US # comment\n - GEOIP,ca\n'), ['ca', 'us'])
        for text in ['payload:', '- GEOIP,US,no-resolve', '- IP-CIDR,192.0.2.0/24', '- GEOIP,US\n- MATCH']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_region(text)

    def test_duplicate_countries_preserve_union(self):
        self.assertEqual(parse_region('- GEOIP,CM\n- GEOIP,cm'), ['cm'])

    def test_missing_or_empty_country_does_not_replace_published_files(self):
        sources=json.loads((Path(__file__).resolve().parents[1]/'region-sources.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'published';out.mkdir()
            (out/'sentinel.mrs').write_bytes(b'previous verified version')
            (root/'geo.dat').write_bytes(b'fixture')
            (root/'mapping.json').write_text(json.dumps({name:['zz'] for name in sources}))
            args=SimpleNamespace(geoip=root/'geo.dat',mihomo='unused',source_url='https://example.com/public.dat',mapping=root/'mapping.json',output=out)
            for geo in [{}, {'zz':[]}]:
                with self.subTest(geo=geo), patch('build_regions.read_geo',return_value=geo), patch('build_regions.subprocess.check_output',return_value='test'), self.assertRaises(ValueError):
                    build(args)
                self.assertEqual(list(out.iterdir()),[out/'sentinel.mrs'])
                self.assertEqual((out/'sentinel.mrs').read_bytes(),b'previous verified version')

    def test_merging_preserves_exact_union_without_filling_holes(self):
        original = [ipaddress.ip_network(n) for n in ['192.0.2.0/25', '192.0.2.128/25', '192.0.2.0/26', '198.51.100.0/25', '198.51.100.192/26', '2001:db8::/33', '2001:db8:8000::/33']]
        expected = [ipaddress.ip_network(n) for n in ['192.0.2.0/24', '198.51.100.0/25', '198.51.100.192/26', '2001:db8::/32']]
        self.assertEqual(merge(original), expected)
        self.assertEqual(coverage(original), coverage(expected))
        self.assertFalse(any(ipaddress.ip_address('198.51.100.128') in n for n in merge(original)))


if __name__ == '__main__':
    unittest.main()
