from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from lp import certs


@unittest.skipUnless(shutil.which('openssl'), 'openssl is not installed')
class CertificateTests(unittest.TestCase):
    def test_readiness_checks_expiry_hosts_and_matching_private_key(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'core/certs'
            target.mkdir(parents=True)
            self.assertFalse(certs.ready(root))
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                            '-days', '90', '-subj', '/CN=traefik.localhost',
                            '-addext', 'subjectAltName=DNS:traefik.localhost',
                            '-keyout', str(target / 'key.pem'), '-out', str(target / 'cert.pem')],
                           check=True, capture_output=True)
            self.assertTrue(certs.ready(root))
            route = root / 'services/api/route.yml'
            route.parent.mkdir(parents=True)
            route.write_text('http:\n  routers:\n    api:\n      rule: Host(`api.localhost`)\n')
            self.assertFalse(certs.ready(root))
            route.unlink()
            subprocess.run(['openssl', 'genrsa', '-out', str(target / 'key.pem'), '2048'],
                           check=True, capture_output=True)
            self.assertFalse(certs.ready(root))
