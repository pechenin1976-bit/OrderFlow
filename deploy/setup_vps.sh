#!/bin/bash
# Quantilan OrderFlow — установка и обновление на VPS
#
# Первый деплой:
#   git clone https://github.com/pechenin1976-bit/OrderFlow.git /tmp/OrderFlow
#   cd /tmp/OrderFlow && bash deploy/setup_vps.sh
#
# Повторный запуск = обновление (код в /opt/orderflow, .env и settings/ не трогаем).

set -e

INSTALL_DIR="/opt/orderflow"
TMP_SRC="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_NAME="orderflow"
SERVICE_FILE="deploy/orderflow.service"

_uv_bin() {
    if command -v uv &>/dev/null; then
        command -v uv
        return 0
    fi
    for p in "$HOME/.local/bin/uv" "/root/.local/bin/uv"; do
        if [ -x "$p" ]; then
            echo "$p"
            return 0
        fi
    done
    return 1
}

_ensure_uv() {
    local bin
    bin="$(_uv_bin)" && echo "$bin" && return 0
    echo "→ uv not found, installing..."
    curl -Lsf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    _uv_bin
}

_sync_deps() {
    local uv_bin uv_dir
    uv_bin="$(_ensure_uv)" || return 1
    uv_dir="$(dirname "$uv_bin")"
    echo "→ uv sync ($uv_bin)..."
    if sudo env PATH="$uv_dir:$PATH" bash -c "cd '$INSTALL_DIR' && '$uv_bin' sync"; then
        return 0
    fi
    echo "→ uv sync failed, fallback: pip + pyproject.toml"
    if [ ! -x "$INSTALL_DIR/.venv/bin/python" ]; then
        sudo python3 -m venv "$INSTALL_DIR/.venv"
    fi
    sudo "$INSTALL_DIR/.venv/bin/pip" install -q --upgrade pip
    sudo "$INSTALL_DIR/.venv/bin/pip" install -q aiohttp numpy python-dotenv
}

echo "=== Quantilan OrderFlow — VPS ==="
echo "→ Source: $TMP_SRC"
echo "→ Target: $INSTALL_DIR"

# 1. Копируем в /opt (если запущено не из /opt)
if [ "$TMP_SRC" != "$INSTALL_DIR" ]; then
    echo "→ Sync to $INSTALL_DIR..."
    sudo mkdir -p "$INSTALL_DIR"
    sudo rsync -a --delete \
        --exclude='.env' \
        --exclude='.venv/' \
        --exclude='__pycache__/' \
        --exclude='*.pyc' \
        --exclude='.git/' \
        --exclude='settings/' \
        --exclude='logs/' \
        "$TMP_SRC/" "$INSTALL_DIR/"
    echo "→ Copied."
else
    echo "→ Already in $INSTALL_DIR, skipping rsync."
fi

# 2. Каталоги и версия
sudo mkdir -p "$INSTALL_DIR/logs"
COMMIT=$(git -C "$TMP_SRC" log -1 --format="%h (%ad)" --date=format:"%Y-%m-%d" 2>/dev/null || echo "unknown")
MSG=$(git -C "$TMP_SRC" log -1 --format="%s" 2>/dev/null || echo "")
printf "%s\n%s\n" "$COMMIT" "$MSG" | sudo tee "$INSTALL_DIR/.version" >/dev/null
echo "→ Version: $COMMIT"

# 3. settings/ — копируем только при первом деплое (не перезаписываем)
if [ ! -d "$INSTALL_DIR/settings" ]; then
    echo "→ Copying settings/ (first deploy)..."
    sudo cp -r "$TMP_SRC/settings" "$INSTALL_DIR/settings"
else
    echo "→ settings/ already exists, skipping (edit manually if needed)."
fi

# 4. Зависимости
echo "→ Installing dependencies..."
_sync_deps

# 5. Права для ubuntu (User= в сервисе)
sudo chown -R ubuntu:ubuntu "$INSTALL_DIR"
if [ -f "$INSTALL_DIR/.env" ]; then
    sudo chmod 600 "$INSTALL_DIR/.env"
fi

# 6. .env при первом деплое
if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo ""
    echo "⚠  Нет $INSTALL_DIR/.env — создайте вручную:"
    echo "   sudo nano $INSTALL_DIR/.env"
    echo ""
    echo "   Минимум:"
    echo "   ORDERFLOW_LICENSE_SERVICE_TOKEN=<то же что SERVICE_TOKEN в license server>"
    echo "   ORDERFLOW_LICENSE_SERVER_URL=http://127.0.0.1:8000"
    echo "   ORDERFLOW_API_KEYS=<dev-token или оставить по умолчанию>"
    echo ""
fi

# 7. systemd
echo "→ Installing systemd unit..."
sudo cp "$INSTALL_DIR/$SERVICE_FILE" "/etc/systemd/system/$SERVICE_NAME.service"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME" 2>/dev/null || true

if [ -f "$INSTALL_DIR/.env" ]; then
    echo "→ Restarting $SERVICE_NAME..."
    sudo systemctl restart "$SERVICE_NAME"
    sudo systemctl status "$SERVICE_NAME" --no-pager || true
else
    echo "→ Сервис не перезапущен (нет .env). После настройки:"
    echo "   sudo systemctl start $SERVICE_NAME"
fi

echo ""
echo "=== Готово ==="
echo "  Логи:     sudo journalctl -u $SERVICE_NAME -f"
echo "  Статус:   sudo systemctl status $SERVICE_NAME"
echo ""
echo "=== Следующее обновление ==="
echo "  cd /tmp/OrderFlow && git pull && bash deploy/setup_vps.sh"
echo ""
