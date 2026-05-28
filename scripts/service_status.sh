#!/usr/bin/env bash
set -e

SERVICE_NAME="dvbt2-analyzer.service"

sudo systemctl status "${SERVICE_NAME}"
journalctl -u "${SERVICE_NAME}" -n 80 --no-pager
