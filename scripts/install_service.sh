#!/usr/bin/env bash
set -e

SERVICE_NAME="dvbt2-analyzer.service"
SYSTEMD_PATH="/etc/systemd/system/${SERVICE_NAME}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SERVICE_TEMPLATE="${REPO_ROOT}/deployment/${SERVICE_NAME}"
ENV_FILE="${REPO_ROOT}/.env"
START_SERVICE=false

if [[ "${1:-}" == "--start" ]]; then
  START_SERVICE=true
elif [[ $# -gt 0 ]]; then
  echo "Usage: ./scripts/install_service.sh [--start]"
  exit 1
fi

if [[ ! -f "${REPO_ROOT}/main.py" || ! -d "${REPO_ROOT}/src" ]]; then
  echo "ERROR: repo root tidak valid: ${REPO_ROOT}"
  echo "Jalankan script ini dari repo capstone-design-repo."
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: file .env belum ada."
  echo "Buat konfigurasi dulu:"
  echo "  cp .env.example .env"
  echo "  nano .env"
  exit 1
fi

if [[ ! -f "${SERVICE_TEMPLATE}" ]]; then
  echo "ERROR: service template tidak ditemukan: ${SERVICE_TEMPLATE}"
  exit 1
fi

echo "Installing ${SERVICE_NAME}..."
sudo cp "${SERVICE_TEMPLATE}" "${SYSTEMD_PATH}"
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"

if [[ "${START_SERVICE}" == "true" ]]; then
  sudo systemctl start "${SERVICE_NAME}"
fi

echo ""
echo "Service installed."
echo "Cek status:"
echo "  sudo systemctl status ${SERVICE_NAME}"
echo "Log live:"
echo "  journalctl -u ${SERVICE_NAME} -f"
