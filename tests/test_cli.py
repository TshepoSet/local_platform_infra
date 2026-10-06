import json
from pathlib import Path
import sys

from test_services import ServiceHarness
from test_services import ROOT


class CliTests(ServiceHarness):
    def cli(self, *args, ok=True, env=None):
        return self.run_command(sys.executable, '-m', 'lp', *args, ok=ok, env=env)

    def state(self):
        return json.loads(self.log.with_suffix('.state').read_text())

    def test_help_and_root_selection(self):
        for args in [('help',), ('--help',), ('add', '--help')]:
            self.assertIn('Usage', self.cli(*args).stdout)
        self.assertIn('not found', self.cli('--root', str(self.base / 'missing'), 'status', ok=False).stderr)

    def test_legacy_generator_respects_configured_checkout(self):
        self.run_command(sys.executable, str(ROOT / 'tools/new_service.py'),
                         'configured-root-test', '--image', 'nginx', '--port', '80')
        self.assertTrue((self.infra / 'services/configured-root-test/compose.yml').exists())

    def test_cli_and_make_startup_are_idempotent(self):
        self.cli('add', 'api', '--path', str(self.app), '--port', '8080')
        self.cli('add', 'grafana', '--image', 'grafana/grafana:latest', '--port', '3000')
        self.cli('setup')
        self.cli('setup')
        self.cli('up')
        original = self.state()['containers']
        cert = self.infra / 'core/certs/cert.pem'
        route = self.infra / 'core/traefik/routes/api.yml'
        timestamps = (cert.stat().st_mtime_ns, route.stat().st_mtime_ns)
        self.cli('up')
        self.make('up')
        self.assertEqual(original, self.state()['containers'])
        self.assertEqual(timestamps, (cert.stat().st_mtime_ns, route.stat().st_mtime_ns))
        self.assertEqual(sum(c[1:3] == ['network', 'create'] for c in self.calls()), 1)
        self.assertEqual(sum('-cert-file' in c for c in self.calls()), 1)
        output = self.cli('status').stdout
        for value in ('api', 'grafana', 'traefik', 'running', 'proxy network: ready', 'HTTPS certificate: ready'):
            self.assertIn(value, output)
        self.cli('down', 'api')
        self.assertIn('exited', self.cli('status').stdout)
        self.assertTrue(any(c['State'] == 'running' for c in self.state()['containers']))
        self.make('down')
        self.assertEqual(self.state()['containers'], [])

    def test_rebuild_restarts_only_target_but_make_rebuild_is_build_only(self):
        self.build_app()
        self.build_app('other')
        self.cli('up')
        old = {c['Names'][0]: c['Id'] for c in self.state()['containers']}
        self.cli('rebuild', 'myapp')
        new = {c['Names'][0]: c['Id'] for c in self.state()['containers']}
        self.assertNotEqual(old['myapp'], new['myapp'])
        self.assertEqual(old['other'], new['other'])
        self.assertEqual(old['traefik'], new['traefik'])
        self.make('rebuild', 'svc=myapp')
        self.assertEqual(new, {c['Names'][0]: c['Id'] for c in self.state()['containers']})

    def test_logs_restart_remove_preserve_source_and_other_routes(self):
        self.build_app()
        self.cli('up', 'myapp')
        self.cli('logs', 'myapp')
        self.assertEqual(self.calls()[-1][-2:], ['logs', '-f'])
        self.cli('logs', 'myapp', '--no-follow')
        self.assertEqual(self.calls()[-1][-1], 'logs')
        self.make('restart', 'svc=myapp')
        static = self.infra / 'core/traefik/routes/routes.yml'
        content = static.read_bytes()
        data = self.infra / 'services/myapp/data'
        data.mkdir()
        (data / 'keep.txt').write_text('persistent data')
        self.cli('remove', 'myapp')
        self.assertTrue((self.app / 'Dockerfile').exists())
        self.assertTrue((data / 'keep.txt').exists())
        self.assertFalse((self.infra / 'services/myapp/compose.yml').exists())
        self.assertFalse((self.infra / 'core/traefik/routes/myapp.yml').exists())
        self.assertEqual(static.read_bytes(), content)
        self.assertFalse(any('-v' in c for c in self.calls()))
        self.assertIn('does not exist', self.cli('up', 'myapp', ok=False).stderr)
        self.cli('add', 'myapp', '--path', str(self.app), '--port', '8080')
        self.assertTrue((data / 'keep.txt').exists())

    def test_ambiguous_port_detection_requires_port(self):
        result = self.cli('add', 'nginx', '--image', 'nginx', ok=False,
                          env={**self.env, 'EXPOSED_PORTS': '{"80/tcp": {}, "443/tcp": {}}'})
        self.assertIn('Ambiguous', result.stderr)
        self.assertFalse((self.infra / 'services/nginx').exists())
        self.cli('add', 'nginx', '--image', 'nginx')
        self.assertIn('http://nginx:80', (self.infra / 'services/nginx/route.yml').read_text())

    def test_compose_false_success_is_reported(self):
        self.build_app()
        result = self.cli('up', 'myapp', ok=False, env={**self.env, 'FAKE_START_FAILURE': '1'})
        self.assertIn('Not running after startup', result.stderr)

    def test_missing_and_reserved_services_have_no_side_effects(self):
        for args in [('up', 'missing'), ('down', '../escape'), ('add', 'routes', '--image', 'nginx', '--port', '80'),
                     ('add', 'lp-tls', '--image', 'nginx', '--port', '80')]:
            self.cli(*args, ok=False)
        self.assertEqual(self.calls(), [])
