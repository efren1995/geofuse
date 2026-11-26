#!/data/data/com.termux/files/usr/bin/bash
set -e
cd ~/geofuse

cleanup() {
  echo ""
  echo "[GeoFuse] Stopping services..."
  kill "$MTX_PID" "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "[GeoFuse] Starting MediaMTX (WebRTC on :8889)..."
mediamtx ~/geofuse/mediamtx.yml > ~/geofuse/data/mediamtx.log 2>&1 &
MTX_PID=$!

sleep 1

echo "[GeoFuse] Starting FastAPI + YOLOv8 + GeoCLIP + Telemetry Bus on :8000..."
python -m uvicorn app:app --host 127.0.0.1 --port 8000 &
API_PID=$!

echo "[GeoFuse] Open http://127.0.0.1:8000 in your browser."
wait "$API_PID"
