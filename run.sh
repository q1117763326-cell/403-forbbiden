#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/403-forbbiden-qiusiqian"

exec python3 -m streamlit run 首页.py --server.address 0.0.0.0 --server.port 8501 --server.headless true --server.enableCORS false --server.enableWebsocketCompression false
