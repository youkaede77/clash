import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from build_mobile_rules import filter_asn, build

class MobileRulesTests(unittest.TestCase):
    def test_only_asn_lines_removed_and_other_rules_remain_byte_exact(self):
        text='# source\npayload:\n  - DOMAIN-SUFFIX,example.com\n  - IP-ASN,123\n  - IP-CIDR,1.2.3.0/24\n  - DOMAIN-KEYWORD,ip-asn\n  - PROCESS-NAME,example\n'
        result, removed=filter_asn(text)
        self.assertEqual(result,text.replace('  - IP-ASN,123\n',''))
        self.assertEqual(removed,['  - IP-ASN,123'])
    def test_quoted_rule_comment_and_no_resolve(self):
        result, removed=filter_asn("payload:\n  - 'IP-ASN,123,no-resolve' # comment\n  - DOMAIN,example.com\n")
        self.assertEqual(result,'payload:\n  - DOMAIN,example.com\n')
        self.assertEqual(len(removed),1)
    def test_already_filtered_input_is_valid(self):
        text='payload:\n  - DOMAIN,example.com\n'
        self.assertEqual(filter_asn(text),(text,[]))
    def test_unknown_asn_and_empty_payload_fail_closed(self):
        for text in ['payload:\n  - IP-ASN,not-a-number\n  - DOMAIN,a.com\n','payload:\n  - SRC-IP-ASN,123\n  - DOMAIN,a.com\n','payload:\n  - IP-ASN,123\n']:
            with self.subTest(text=text),self.assertRaises(ValueError):filter_asn(text)
    def test_failed_download_does_not_replace_published_rules(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'out';output.mkdir();saved=output/'existing.yaml';saved.write_text('previous')
            with patch('build_mobile_rules.download',side_effect=ValueError('download failed')),self.assertRaises(ValueError):build(output)
            self.assertEqual(saved.read_text(),'previous');self.assertEqual(list(output.iterdir()),[saved])

if __name__=='__main__':unittest.main()
