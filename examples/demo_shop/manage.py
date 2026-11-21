#!/usr/bin/env python
import os
import sys
from pathlib import Path


def main():
    repo_root = Path(__file__).resolve().parents[2]
    src_dir = repo_root / 'src'
    demo_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(src_dir))
    sys.path.insert(0, str(demo_dir))

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demo_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
