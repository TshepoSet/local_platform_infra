"""Stateful test double for subprocess integration tests; never used by lp."""
import json
import os
from pathlib import Path
import sys
import yaml

program, args = Path(sys.argv[0]).name, sys.argv[1:]
log = Path(os.environ['COMMAND_LOG'])
with log.open('a') as handle:
    handle.write(json.dumps(sys.argv) + '\n')
if os.environ.get('COMMAND_EXIT'):
    sys.exit(int(os.environ['COMMAND_EXIT']))
state_path = log.with_suffix('.state')
state = json.loads(state_path.read_text()) if state_path.exists() else {'network': False, 'containers': [], 'next_id': 1}

if program == 'podman':
    if args[:2] == ['network', 'exists']:
        sys.exit(0 if state['network'] else 1)
    if args[:2] == ['network', 'create']:
        state['network'] = True
    elif args[0] == 'ps':
        print(json.dumps(state['containers']))
    elif args[0] == 'inspect':
        print(json.dumps([{'Config': {'ExposedPorts': json.loads(os.environ.get('EXPOSED_PORTS', '{"80/tcp": {}}'))}}]))
elif program == 'mkcert':
    if '-cert-file' in args:
        Path(args[args.index('-cert-file') + 1]).write_text('test certificate')
        Path(args[args.index('-key-file') + 1]).write_text('test key')
elif program == 'openssl':
    if '-pubkey' in args or '-pubout' in args:
        print('fake public key')
elif program == 'podman-compose':
    path = Path(args[1])
    command = args[2]
    config = yaml.safe_load(path.read_text())
    project = config.get('name', path.parent.name)
    if command == 'up' and not os.environ.get('FAKE_START_FAILURE'):
        for name, service in config['services'].items():
            old = next((c for c in state['containers'] if c['Labels']['io.podman.compose.project'] == project
                        and c['Labels']['com.docker.compose.service'] == name), None)
            if old and '--force-recreate' not in args:
                old['State'] = 'running'
                continue
            if old:
                state['containers'].remove(old)
            state['containers'].append({'Id': str(state['next_id']), 'State': 'running',
                'Names': [service.get('container_name', f'{project}_{name}_1')],
                'Labels': {'io.podman.compose.project': project, 'com.docker.compose.service': name}})
            state['next_id'] += 1
    elif command in ('down', 'stop'):
        if command == 'down':
            state['containers'] = [c for c in state['containers'] if c['Labels']['io.podman.compose.project'] != project]
        else:
            for c in state['containers']:
                if c['Labels']['io.podman.compose.project'] == project:
                    c['State'] = 'exited'
state_path.write_text(json.dumps(state))
