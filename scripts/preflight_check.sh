#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"

ERRORS=0

ok() {
  echo "OK    : $1"
}

warn() {
  echo "WARN  : $1"
}

err() {
  echo "ERROR : $1"
  ERRORS=$((ERRORS + 1))
}

get_env_value() {
  local key="$1"
  if [[ ! -f "${ENV_FILE}" ]]; then
    return 0
  fi
  grep -E "^[[:space:]]*${key}=" "${ENV_FILE}" | tail -n 1 | cut -d '=' -f 2- | tr -d '"' | tr -d "'"
}

echo "=== DVB-T2 Analyzer Preflight Check ==="
echo "Repo: ${REPO_ROOT}"
echo ""

if command -v python3 >/dev/null 2>&1; then
  ok "python3 tersedia: $(command -v python3)"
else
  err "python3 tidak ditemukan"
fi

if [[ -f "${ENV_FILE}" ]]; then
  ok ".env ditemukan"
else
  err ".env belum ada. Jalankan: cp .env.example .env && nano .env"
fi

if [[ -f "${REPO_ROOT}/main.py" ]]; then
  ok "main.py ditemukan"
else
  err "main.py tidak ditemukan"
fi

GPS_ENABLED="$(get_env_value GPS_ENABLED)"
GPS_PORT="$(get_env_value GPS_PORT)"
GPS_BAUDRATE="$(get_env_value GPS_BAUDRATE)"

GPS_ENABLED="${GPS_ENABLED:-true}"
GPS_PORT="${GPS_PORT:-/dev/ttyUSB0}"
GPS_BAUDRATE="${GPS_BAUDRATE:-4800}"

echo ""
echo "Config GPS:"
echo "GPS_ENABLED=${GPS_ENABLED}"
echo "GPS_PORT=${GPS_PORT}"
echo "GPS_BAUDRATE=${GPS_BAUDRATE}"

case "$(echo "${GPS_ENABLED}" | tr '[:upper:]' '[:lower:]')" in
  true|1|yes|y|on)
    if [[ -e "${GPS_PORT}" ]]; then
      ok "GPS device ditemukan: ${GPS_PORT}"
      if [[ -r "${GPS_PORT}" && -w "${GPS_PORT}" ]]; then
        ok "GPS device bisa dibaca/ditulis user saat ini"
      else
        warn "GPS device ada, tapi permission mungkin kurang. Jalankan: sudo usermod -aG dialout orangepi lalu sudo reboot"
      fi
    else
      err "GPS_ENABLED=true tetapi device tidak ditemukan: ${GPS_PORT}"
    fi
    ;;
  false|0|no|n|off)
    warn "GPS dinonaktifkan via GPS_ENABLED=${GPS_ENABLED}"
    ;;
  *)
    err "GPS_ENABLED tidak valid: ${GPS_ENABLED}"
    ;;
esac

echo ""
if command -v lsusb >/dev/null 2>&1; then
  if lsusb | grep -qi "0bda:2838"; then
    ok "RTL-SDR USB terdeteksi: 0bda:2838"
  else
    err "RTL-SDR 0bda:2838 tidak terdeteksi oleh lsusb"
  fi
else
  warn "lsusb tidak tersedia; tidak bisa cek RTL-SDR USB"
fi

if command -v rtl_test >/dev/null 2>&1; then
  ok "rtl_test tersedia"
else
  warn "rtl_test tidak tersedia. Install rtl-sdr tools untuk troubleshooting manual."
fi

echo ""
if [[ "${ERRORS}" -eq 0 ]]; then
  echo "Preflight result: OK"
  exit 0
fi

echo "Preflight result: ERROR (${ERRORS})"
exit 1
