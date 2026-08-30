#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m pip install -q -r requirements.txt
exec python3 -m uvicorn ztpay.server:app --app-dir src --host 127.0.0.1 --port "${PORT:-8512}"
