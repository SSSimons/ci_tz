#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess


def remove_files(paths):
    if not isinstance(paths, list) or not 1 <= len(paths) <= 2:
        raise ValueError('DELETE_FILES must contain 1 or 2 file paths')
    root = Path.cwd().resolve()
    # Сначала проверяем все пути, затем удаляем: не оставляем частичный результат при ошибке.
    for value in paths:
        if not isinstance(value, str) or not value:
            raise ValueError('Each file path must be a non-empty string')
        path = Path(value)
        if path.is_absolute() or '..' in path.parts or '.git' in path.parts or path == Path('.'):
            raise ValueError(f'Unsafe path: {value}')
        full = root / path
        if full.is_symlink() or any(parent.is_symlink() for parent in full.parents if parent != root):
            raise ValueError(f'Symlinks are not supported: {value}')
        if not full.resolve().is_relative_to(root):
            raise ValueError(f'Path escapes the checkout: {value}')
        if full.is_dir():
            raise ValueError(f'Only files may be deleted: {value}')
    for value in paths:
        subprocess.run(['git', '--literal-pathspecs', 'rm', '--ignore-unmatch', '--', value], check=True)


if __name__ == '__main__':
    remove_files(json.loads(os.environ['DELETE_FILES']))
