import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def run(*args, cwd, check=True, env=None):
    return subprocess.run(args, cwd=cwd, check=check, text=True,
                          capture_output=True, env=env)


def transfer(source, destination, archive):
    run('tar', '-czf', str(archive), '-C', str(source), '.', cwd=source)
    destination.mkdir()
    run('tar', '-xzf', str(archive), '-C', str(destination), cwd=source)


class GitFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='jenkins-ci-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.remote = self.base / 'remote.git'
        self.repo = self.base / 'job1'
        run('git', 'init', '--bare', '-b', 'master', str(self.remote), cwd=self.base)
        run('git', 'clone', str(self.remote), str(self.repo), cwd=self.base)
        self.configure(self.repo)
        for source in (ROOT / 'demo').iterdir():
            shutil.copy(source, self.repo / source.name)
        run('git', 'add', '.', cwd=self.repo)
        run('git', 'commit', '-m', 'Initial demo', cwd=self.repo)
        run('git', 'push', '-u', 'origin', 'master', cwd=self.repo)

    def configure(self, repo):
        run('git', 'config', 'user.name', 'Jenkins CI Test', cwd=repo)
        run('git', 'config', 'user.email', 'ci-test@example.com', cwd=repo)

    def delete(self, paths, repo=None, check=True):
        return run('python3', str(ROOT / 'scripts/remove_files.py'),
                   cwd=repo or self.repo, check=check,
                   env={**os.environ, 'DELETE_FILES': json.dumps(paths)})

    def test_checkout_transfer_delete_commit_push_and_repeat(self):
        job2 = self.base / 'job2'
        job3 = self.base / 'job3'
        archive = self.base / 'project.tar.gz'
        transfer(self.repo, job2, archive)
        self.delete(['obsolete.txt', 'legacy.txt'], repo=job2)
        transfer(job2, job3, archive)
        self.configure(job3)
        run('git', 'commit', '-m', '[ci-cleanup] Remove selected files', cwd=job3)
        run('git', 'push', 'origin', 'HEAD:refs/heads/master', cwd=job3)
        files = run('git', 'ls-tree', '--name-only', 'master', cwd=self.remote).stdout.splitlines()
        self.assertEqual(set(files), {'app.py', 'README.md'})
        message = run('git', 'log', '-1', '--format=%s', 'master', cwd=self.remote).stdout.strip()
        self.assertEqual(message, '[ci-cleanup] Remove selected files')
        self.delete(['obsolete.txt', 'legacy.txt'], repo=job3)
        self.assertEqual(run('git', 'diff', '--cached', '--quiet', cwd=job3, check=False).returncode, 0)

    def test_invalid_paths_rejected_before_any_file_is_deleted(self):
        for path in ['../outside', '/tmp/outside', '.git/config', '.', 'nested/../../outside']:
            with self.subTest(path=path):
                result = self.delete(['obsolete.txt', path], check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue((self.repo / 'obsolete.txt').exists())
                self.assertEqual(run('git', 'diff', '--cached', '--quiet', cwd=self.repo, check=False).returncode, 0)

    def test_directories_and_symlinks_rejected(self):
        (self.repo / 'folder').mkdir()
        (self.repo / 'link').symlink_to(self.repo / 'obsolete.txt')
        (self.repo / 'linked-folder').symlink_to(self.repo / 'folder')
        for path in ['folder', 'link', 'linked-folder/file.txt']:
            with self.subTest(path=path):
                self.assertNotEqual(self.delete([path], check=False).returncode, 0)

    def test_wildcards_are_literal(self):
        self.delete(['*.txt'])
        self.assertTrue((self.repo / 'obsolete.txt').exists())
        self.assertTrue((self.repo / 'legacy.txt').exists())
        self.assertEqual(run('git', 'diff', '--cached', '--quiet', cwd=self.repo, check=False).returncode, 0)

    def test_invalid_file_list_rejected(self):
        for paths in [[], ['a', 'b', 'c'], 'obsolete.txt', [None], ['']]:
            with self.subTest(paths=paths):
                self.assertNotEqual(self.delete(paths, check=False).returncode, 0)

    def test_concurrent_master_update_rejects_push(self):
        concurrent = self.base / 'concurrent'
        run('git', 'clone', str(self.remote), str(concurrent), cwd=self.base)
        self.configure(concurrent)
        (concurrent / 'app.py').write_text('print("Concurrent change")\n')
        run('git', 'add', 'app.py', cwd=concurrent)
        run('git', 'commit', '-m', 'User update', cwd=concurrent)
        run('git', 'push', 'origin', 'master', cwd=concurrent)
        self.delete(['obsolete.txt', 'legacy.txt'])
        run('git', 'commit', '-m', '[ci-cleanup] Remove selected files', cwd=self.repo)
        result = run('git', 'push', 'origin', 'HEAD:refs/heads/master', cwd=self.repo, check=False)
        self.assertNotEqual(result.returncode, 0)
        message = run('git', 'log', '-1', '--format=%s', 'master', cwd=self.remote).stdout.strip()
        self.assertEqual(message, 'User update')


if __name__ == '__main__':
    unittest.main()
