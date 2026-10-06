import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class StartupFailureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='jenkins-startup-test-')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.secrets = self.work / 'secrets'
        self.secrets.mkdir()
        for name in ['admin_password', 'git_key', 'known_hosts']:
            (self.secrets / name).write_text('TEST_PLACEHOLDER\n')
        self.bin = self.work / 'bin'
        self.bin.mkdir()
        self.env = {**os.environ, 'PATH': f'{self.bin}:' + os.environ['PATH'],
                    'JENKINS_HOME': str(self.work / 'home')}

    def mock_command(self, name, body):
        command = self.bin / name
        command.write_text('#!/usr/bin/env bash\n' + body)
        command.chmod(0o755)

    def test_deploy_stops_when_compose_configuration_fails(self):
        shutil.copy(ROOT / 'deploy.sh', self.work / 'deploy.sh')
        (self.work / '.env').write_text('REPO_URL=git@github.com:example/test.git\n')
        marker = self.work / 'up-was-called'
        self.mock_command('docker', f'''
if [[ "$*" == "compose version" ]]; then exit 0; fi
if [[ "$*" == "compose config --quiet" ]]; then exit 42; fi
touch '{marker}'
exit 0
''')
        result = subprocess.run(['bash', str(self.work / 'deploy.sh')],
                                env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 42)
        self.assertFalse(marker.exists())
        self.assertNotIn('Jenkins: http://', result.stdout)

    def test_bootstrap_stops_when_secret_copy_fails(self):
        script = self.work / 'bootstrap.sh'
        script.write_text((ROOT / 'bootstrap.sh').read_text().replace(
            '/run/ci-secrets', str(self.secrets)))
        marker = self.work / 'jenkins-was-started'
        self.mock_command('install', 'exit 13\n')
        self.mock_command('gosu', f"touch '{marker}'\nexit 0\n")
        result = subprocess.run(['bash', str(script)], env=self.env,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 13)
        self.assertFalse(marker.exists())


if __name__ == '__main__':
    unittest.main()
