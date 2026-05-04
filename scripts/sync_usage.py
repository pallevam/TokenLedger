#!/usr/bin/env python
"""Cron-friendly entrypoint:  python scripts/sync_usage.py [days]"""
from src.usage_puller.sync import cli

if __name__ == "__main__":
    cli()
