#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_SCRIPT="$ROOT_DIR/start_server.sh"
CLIENT_SCRIPT="$ROOT_DIR/start_client.sh"

if [[ "$OSTYPE" != "darwin"* ]]; then
  echo "Этот скрипт предназначен для macOS (darwin)."
  exit 1
fi

for script in "$SERVER_SCRIPT" "$CLIENT_SCRIPT"; do
  if [[ ! -x "$script" ]]; then
    chmod +x "$script"
  fi
done

echo "========================================"
echo "Запуск сервера и клиента в отдельных окнах Terminal"
echo "Корень проекта: $ROOT_DIR"
echo "========================================"

osascript <<APPLESCRIPT
tell application "Terminal"
  activate
  do script "cd '$ROOT_DIR'; ./start_server.sh"
  delay 3
  do script "cd '$ROOT_DIR'; ./start_client.sh"
end tell
APPLESCRIPT

echo "Сервер: http://localhost:5001"
echo "Клиент: http://localhost:3000"
echo "Оба процесса запущены в отдельных окнах Terminal."

