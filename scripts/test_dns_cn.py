import io
import unittest
import zipfile
from compression import zstd
from build_dns_cn import convert_archive


class DnsCNTests(unittest.TestCase):
    def archive(self, payload):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr('cn.mrs', zstd.compress(payload))
        return stream.getvalue()

    def test_preserves_decoded_bytes_with_bounded_window(self):
        payload = b'MRS\x01\x00' + b'public-domain-data' * 100000
        result, report = convert_archive(self.archive(payload))
        self.assertEqual(zstd.decompress(result), payload)
        descriptor = result[5]
        window = (1 << (10 + (descriptor >> 3))) * (8 + (descriptor & 7)) // 8
        self.assertLessEqual(window, 65536)
        self.assertTrue(report['decoded_bytes_identical'])

    def test_rejects_non_domain_data(self):
        with self.assertRaises(ValueError):
            convert_archive(self.archive(b'MRS\x01\x01' + b'ip-data'))
