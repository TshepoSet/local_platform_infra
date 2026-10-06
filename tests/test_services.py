import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class ServiceHarness(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.infra = self.base / 'infra'
        self.infra.mkdir()
        for directory in ('tools', 'templates', 'lp', 'core'):
            shutil.copytree(ROOT / directory, self.infra / directory, ignore=shutil.ignore_patterns('*.pem', '__pycache__'))
        shutil.copy(ROOT / 'Makefile', self.infra)
        self.app = self.base / 'external app: #1'
        self.app.mkdir()
        (self.app / 'Dockerfile').write_text('FROM scratch\n')
        self.log = self.base / 'commands.jsonl'
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        for name in ('podman', 'podman-compose', 'mkcert', 'openssl'):
            script = self.bin / name
            script.write_text(f'#!{sys.executable}\n' + (ROOT / 'tests/fake_runtime.py').read_text())
            script.chmod(0o755)
        self.env = {**os.environ, 'PATH': f'{self.bin}:{os.environ["PATH"]}',
                    'COMMAND_LOG': str(self.log), 'LP_ROOT': str(self.infra)}

    def run_command(self, *args, ok=True, env=None):
        result = subprocess.run(args, cwd=self.infra, env=env or self.env,
                                text=True, capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def generate(self, name='myapp', *args, ok=True):
        return self.run_command(sys.executable, 'tools/new_service.py', name, *args, ok=ok)

    def make(self, target, *args, ok=True, env=None):
        return self.run_command('make', target, f'PYTHON={sys.executable}', *args, ok=ok, env=env)

    def config(self, name='myapp'):
        return yaml.safe_load((self.infra / 'services' / name / 'compose.yml').read_text())

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def build_app(self, name='myapp'):
        self.generate(name, '--context', str(self.app), '--port', '8080')


class ServiceTests(ServiceHarness):
    def test_external_context_default_dockerfile_no_image(self):
        self.generate('MyApp', '--context', '../external app: #1', '--port', '8080')
        config = self.config()
        app = config['services']['myapp']
        self.assertEqual(app['build'], {'context': str(self.app)})
        self.assertNotIn('image', app)
        self.assertEqual(app['container_name'], 'myapp')
        self.assertEqual(app['networks']['proxy']['aliases'], ['myapp'])
        self.assertTrue(config['networks']['proxy']['external'])
        route = yaml.safe_load((self.infra / 'services/myapp/route.yml').read_text())['http']
        self.assertEqual(route['routers']['myapp']['rule'], 'Host(`myapp.localhost`)')
        self.assertEqual(route['services']['myapp']['loadBalancer']['servers'], [{'url': 'http://myapp:8080'}])
        self.assertEqual(self.calls(), [])

    def test_make_generator_custom_dockerfile_and_tag(self):
        (self.app / 'docker').mkdir()
        (self.app / 'docker/dev.Dockerfile').write_text('FROM scratch\n')
        self.make('new-service', 'name=myapp', f'context={self.app}',
                  'dockerfile=docker/dev.Dockerfile', 'image=localhost/myapp:dev', 'port=8080')
        app = self.config()['services']['myapp']
        self.assertEqual(app['build']['dockerfile'], 'docker/dev.Dockerfile')
        self.assertEqual(app['image'], 'localhost/myapp:dev')
        self.assertEqual(self.calls(), [])

    def test_absolute_dockerfile_outside_context(self):
        dockerfile = self.base / 'Dockerfile.dev'
        dockerfile.write_text('FROM scratch\n')
        self.generate('myapp', '--context', str(self.app), '--dockerfile', str(dockerfile), '--port', '80')
        self.assertEqual(self.config()['services']['myapp']['build']['dockerfile'], str(dockerfile))

    def test_registry_images(self):
        for i, (value, expected) in enumerate([
            ('nginx:alpine', 'docker.io/nginx:alpine'),
            ('ghcr.io/org/app:v1', 'ghcr.io/org/app:v1'),
            ('localhost:5000/app:dev', 'localhost:5000/app:dev'),
            ('localhost/app:dev', 'localhost/app:dev'),
        ]):
            name = f'app{i}'
            self.generate(name, '--image', value, '--port', '80')
            app = self.config(name)['services'][name]
            self.assertEqual(app['image'], expected)
            self.assertNotIn('build', app)
        self.assertEqual(self.calls(), [])

    def test_invalid_inputs_leave_no_service(self):
        for args in [(), ('--dockerfile', 'Dockerfile', '--image', 'nginx'),
                     ('--context', str(self.app)),
                     ('--context', '/does-not-exist', '--port', '80'),
                     ('--context', str(self.app), '--dockerfile', 'missing', '--port', '80'),
                     ('--image', 'nginx', '--port', '65536')]:
            with self.subTest(args=args):
                self.generate('myapp', *args, ok=False)
                self.assertFalse((self.infra / 'services/myapp').exists())
        for name in ('../escape', 'bad_name', '-bad', 'traefik'):
            self.generate(name, '--image', 'nginx', '--port', '80', ok=False)
        self.assertEqual(self.calls(), [])

    def test_duplicate_does_not_overwrite(self):
        self.build_app()
        original = self.config()
        self.generate('myapp', '--image', 'nginx', '--port', '80', ok=False)
        self.assertEqual(self.config(), original)

    def test_targeted_build_rebuild_start_stop(self):
        self.build_app()
        self.build_app('other')
        for target in ('build', 'rebuild', 'start', 'stop'):
            self.make(target, 'svc=myapp')
        compose_calls = [c[1:] for c in self.calls() if Path(c[0]).name == 'podman-compose' and '/services/' in c[2]]
        prefix = ['-f', str(self.infra / 'services/myapp/compose.yml')]
        self.assertEqual(compose_calls, [prefix + ['build', 'myapp'],
                                       prefix + ['build', '--no-cache', 'myapp'],
                                       prefix + ['up', '-d', '--force-recreate'], prefix + ['stop']])
        self.assertEqual((self.infra / 'core/traefik/routes/myapp.yml').read_text(),
                         (self.infra / 'services/myapp/route.yml').read_text())
        cert_call = next(c for c in self.calls() if Path(c[0]).name == 'mkcert' and '-cert-file' in c)
        self.assertIn('myapp.localhost', cert_call)
        self.assertIn('other.localhost', cert_call)

    def test_bulk_build_uses_compose_not_local_dockerfile(self):
        self.build_app()
        self.generate('registry', '--image', 'nginx', '--port', '80')
        (self.infra / 'services/registry/Dockerfile').write_text('FROM scratch\n')
        other = self.infra / 'services/string-build'
        other.mkdir()
        (other / 'compose.yml').write_text(yaml.safe_dump({'services': {'string-build': {'build': str(self.app)}}}))
        self.make('build')
        self.assertEqual([c[-1] for c in self.calls()], ['myapp', 'string-build'])

    def test_errors_do_not_start_or_build_other_services(self):
        self.generate('registry', '--image', 'nginx', '--port', '80')
        for target, args in [('build', ['svc=registry']), ('start', []),
                             ('start', ['svc=missing']), ('stop', ['svc=../escape'])]:
            self.make(target, *args, ok=False)
        self.assertEqual(self.calls(), [])
        self.build_app()
        self.make('build', 'svc=myapp', ok=False, env={**self.env, 'COMMAND_EXIT': '17'})
        self.assertEqual(len(self.calls()), 1)

    @unittest.skipUnless(shutil.which('podman-compose'), 'podman-compose not installed')
    def test_real_podman_compose_dry_run(self):
        self.build_app()
        # The real Compose parser and command builder, with no container operations.
        compose = shutil.which('podman-compose')
        result = self.run_command(compose, '--dry-run', '-f',
                                  str(self.infra / 'services/myapp/compose.yml'),
                                  'build', '--no-cache', 'myapp', env=os.environ.copy())
        self.assertIn(str(self.app / 'Dockerfile'), result.stdout + result.stderr)
        self.assertIn('--no-cache', result.stdout + result.stderr)
        dockerfile = self.app / 'custom.Dockerfile'
        dockerfile.write_text('FROM scratch\n')
        self.generate('custom', '--context', str(self.app), '--dockerfile', 'custom.Dockerfile',
                      '--image', 'localhost/custom:dev', '--port', '8080')
        result = self.run_command(compose, '--dry-run', '-f',
                                  str(self.infra / 'services/custom/compose.yml'),
                                  'build', 'custom', env=os.environ.copy())
        self.assertIn(str(dockerfile), result.stdout + result.stderr)
        self.assertIn('localhost/custom:dev', result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which('podman-compose'), 'podman-compose not installed')
    def test_existing_platform_compose_files_still_parse(self):
        compose = shutil.which('podman-compose')
        for path in [ROOT / 'services' / name / 'compose.yml'
                     for name in ('grafana', 'prometheus', 'redis')] + [ROOT / 'core/traefik/docker-compose.yml']:
            with self.subTest(path=path):
                self.run_command(compose, '--dry-run', '-f', str(path), 'config', env=os.environ.copy())


if __name__ == '__main__':
    unittest.main()
