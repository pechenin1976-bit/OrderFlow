# Локальный тест (Windows)

Три окна **PowerShell**. Пути подставь свои, если Quantilan лежит в другом месте.

```
C:\Users\peche\Documents\GCC\Py\Quantilan\
├── server\      ← терминал A, C
├── OrderFlow\   ← терминал B
└── www\         ← браузер (опционально)
```

## 1. License server (терминал A)

```powershell
cd C:\Users\peche\Documents\GCC\Py\Quantilan\server
Copy-Item .env.local.example .env -ErrorAction SilentlyContinue
uv sync
uv run python scripts/run_api_only.py
```

В `.env` (если файла не было — создай из `.env.local.example`):

```env
SECRET_KEY=local-dev-secret
SERVICE_TOKEN=local-service-token
DB_PATH=trading_local.db
HOST=127.0.0.1
PORT=8000
```

Жди строку: `Uvicorn running on http://127.0.0.1:8000`

## 2. OrderFlow (терминал B)

```powershell
cd C:\Users\peche\Documents\GCC\Py\Quantilan\OrderFlow
Copy-Item .env.example .env -ErrorAction SilentlyContinue
uv sync
```

В `.env` **обязательно** (тот же `SERVICE_TOKEN`, что в server):

```env
ORDERFLOW_LICENSE_SERVER_URL=http://127.0.0.1:8000
ORDERFLOW_LICENSE_SERVICE_TOKEN=local-service-token
ORDERFLOW_LICENSE_VALIDATE=true
ORDERFLOW_API_KEYS=dev-token-change-me
```

```powershell
uv run orderflow_core.py
```

Подожди 15–30 с (WebSocket с бирж). В логе: `API http://127.0.0.1:8080`

## 3. Smoke-тест (терминал C)

```powershell
cd C:\Users\peche\Documents\GCC\Py\Quantilan\server
$env:SECRET_KEY = "local-dev-secret"
$env:SERVICE_TOKEN = "local-service-token"
uv run python scripts/smoke_orderflow_local.py
```

Успех: `=== All checks passed ===` и строка с ключом `pro_orderflow`.

Только license server (OrderFlow ещё не запущен):

```powershell
$env:SMOKE_SKIP_ORDERFLOW = "1"
uv run python scripts/smoke_orderflow_local.py
```

## 4. curl (PowerShell)

Ключ из вывода smoke:

```powershell
$key = "XXXX-XXXX-XXXX-XXXX"
Invoke-RestMethod -Uri "http://127.0.0.1:8080/api/v1/snapshot?symbol=BTC&tf=15m" -Headers @{ Authorization = "Bearer $key" }
```

Или dev-токен без лицензии:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8080/api/v1/snapshot?symbol=BTC&tf=15m" -Headers @{ Authorization = "Bearer dev-token-change-me" }
```

## 5. Сайт в браузере

**Терминал D** (статика www):

```powershell
cd C:\Users\peche\Documents\GCC\Py\Quantilan\www
.\serve-orderflow-local.ps1
```

В браузере (подставь ключ из smoke):

```
http://127.0.0.1:5500/orderflow.html?token=Y6DUGY-PU66J4-EWDE38-LD5FY2
```

Страница сама подставит API `http://127.0.0.1:8080/api/v1` на localhost.

Нужно:
- OrderFlow **перезапущен** после обновления (CORS в `.env`: `ORDERFLOW_CORS=true`)
- License + OrderFlow как в шагах 1–2

Альтернатива: открыть `orderflow.html` двойным кликом (`file://`) — тоже работает, если CORS включён.

## Порядок

1. A — license `:8000`
2. B — orderflow `:8080`
3. C — smoke
4. браузер или `Invoke-RestMethod`

## Частые проблемы

| Симптом | Решение |
|--------|---------|
| OrderFlow 401 | `ORDERFLOW_LICENSE_SERVICE_TOKEN` = `SERVICE_TOKEN` в server `.env` |
| smoke: server not reachable | Сначала терминал A |
| smoke: OrderFlow not running | Сначала терминал B, подожди WS |
| порт занят | смени `PORT` / `ORDERFLOW_API_PORT` или закрой старый процесс |
