#!/usr/bin/env python
"""Django management entry point."""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from django.core.management import execute_from_command_line


def main():
    """Run Django's command-line utility with this project's settings."""
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
