#!/usr/bin/env bash
set -e

SERVICE_NAME="dvbt2-analyzer.service"
SYSTEMD_PATH="/etc/systemd/system/${SERVICE_NAME}"

if systemctl is-active --quiet "${SERVICE_NAME}"; then
  sudo systemctl stop "${SERVICE_NAME}"
fi

if systemctl is-enabled --quiet "${SERVICE_NAME}" 2>/dev/null; then
  sudo systemctl disable "${SERVICE_NAME}"
fi

if [[ -f "${SYSTEMD_PATH}" ]]; then
  sudo rm "${SYSTEMD_PATH}"
fi

sudo systemctl daemon-reload

echo "Service ${SERVICE_NAME} disabled and removed."
echo "Repo dan .env tidak dihapus."
