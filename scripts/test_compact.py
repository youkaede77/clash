import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from build_compact import build, validate_sources


class CompactTests(unittest.TestCase):
    def test_missing_duplicate_and_empty_region_groups_rejected(self):
        good = {'regions': {'combined': ['a', 'b']}, 'providers': {}}
        validate_sources(good, ['a', 'b'])
        for groups in [{'combined': ['a']}, {'combined': ['a', 'b', 'a']}, {'combined': ['a', 'b'], 'empty': []}]:
            with self.subTest(groups=groups), self.assertRaises(ValueError):
                validate_sources({**good, 'regions': groups}, ['a', 'b'])

    def test_private_urls_and_classical_rules_are_not_published(self):
        spec = {'url': 'https://raw.githubusercontent.com/example/rules/main/test.yaml', 'behavior': 'domain'}
        good = {'regions': {'combined': ['a']}, 'providers': {'public': spec}}
        validate_sources(good, ['a'])
        for change in [{'url': spec['url']+'?token=secret'}, {'url': 'http://localhost/data'},
                       {'behavior': 'classical'}, {'format': 'unknown'}]:
            bad = copy.deepcopy(good)
            bad['providers']['public'].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_sources(bad, ['a'])

    def test_failed_conversion_preserves_previous_published_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); out=root/'output'; out.mkdir()
            saved=out/'old.mrs'; saved.write_bytes(b'previous verified rules')
            args=SimpleNamespace(cache_map=None,output=out,regions=root,mihomo='unused')
            with patch('build_compact.convert',side_effect=ValueError('corrupt upstream input')), self.assertRaises(ValueError):
                build(args)
            self.assertEqual(list(out.iterdir()), [saved])
            self.assertEqual(saved.read_bytes(), b'previous verified rules')


if __name__ == '__main__':
    unittest.main()
