#!/bin/bash
# Обёртка — единая точка входа: deploy/setup_vps.sh (как в Server / CrCraft).
exec bash "$(cd "$(dirname "$0")" && pwd)/deploy/setup_vps.sh" "$@"
