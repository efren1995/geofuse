import io
import json
import os
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Set

import httpx
import numpy as np
from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
MMDB_PATH = DATA_DIR / "GeoLite2-City.mmdb"

yolo_model = None
geoclip_model = None
geoip_reader = None
connected_clients: Set[WebSocket] = set()

SENSOR_LOCATIONS: Dict[str, Dict[str, Any]] = {
    "cam_01": {"lat": 22.1565, "lon": -100.9855, "label": "Camera 01 (cam_01)"},
    "cam_02": {"lat": 22.1833, "lon": -100.9333, "label": "Camera 02 (cam_02)"},
    "cam_03": {"lat": 22.1400, "lon": -101.0100, "label": "Camera 03 (cam_03)"},
    "cam_04": {"lat": 22.1710, "lon": -100.9620, "label": "Camera 04 (cam_04)"},
    "cam_05": {"lat": 22.1320, "lon": -100.9510, "label": "Camera 05 (cam_05)"},
    "cam_06": {"lat": 22.1920, "lon": -100.9950, "label": "Camera 06 (cam_06)"},
}


async def broadcast_event(event_type: str, payload: Dict[str, Any]) -> None:
    if not connected_clients:
        return
    message = json.dumps({
        "type": event_type,
        "ts": int(time.time() * 1000),
        "data": payload,
    })
    dead: List[WebSocket] = []
    for ws in list(connected_clients):
        try:
            await ws.send_text(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connected_clients.discard(ws)


def load_models() -> Dict[str, bool]:
    global yolo_model, geoclip_model, geoip_reader
    status = {"yolo": False, "geoclip": False, "maxmind": False}

    try:
        from ultralytics import YOLO
        weights = DATA_DIR / "yolov8n.pt"
        yolo_model = YOLO(str(weights if weights.exists() else "yolov8n.pt"))
        status["yolo"] = True
    except Exception as exc:
        print(f"[WARN] YOLOv8 init skipped: {exc}")

    try:
        import torch
        from geoclip import GeoCLIP
        device = "cuda" if torch.cuda.is_available() else "cpu"
        geoclip_model = GeoCLIP().eval().to(device)
        status["geoclip"] = True
    except Exception as exc:
        print(f"[WARN] GeoCLIP init skipped: {exc}")

    try:
        import geoip2.database
        if MMDB_PATH.exists():
            geoip_reader = geoip2.database.Reader(str(MMDB_PATH))
            status["maxmind"] = True
    except Exception as exc:
        print(f"[WARN] MaxMind MMDB init skipped: {exc}")

    return status


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_status = load_models()
    await broadcast_event("SYSTEM_STATUS", {"models": model_status})
    yield
    if geoip_reader is not None:
        try:
            geoip_reader.close()
        except Exception:
            pass


app = FastAPI(title="GeoFuse Unified Termux Hub", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    ui_file = STATIC_DIR / "index.html"
    if ui_file.exists():
        return FileResponse(str(ui_file))
    return HTMLResponse("<h2>GeoFuse Unified Hub Online</h2>")


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "yolo_loaded": yolo_model is not None,
        "geoclip_loaded": geoclip_model is not None,
        "maxmind_loaded": geoip_reader is not None,
        "clients": len(connected_clients),
    }


@app.post("/api/detect")
async def detect_objects(
    frame: UploadFile = File(...),
    sensor_id: str = Form("cam_01"),
    conf: float = Form(0.35),
    imgsz: int = Form(416),
):
    if yolo_model is None:
        return {"error": "YOLOv8 model not loaded", "detections": []}

    raw = await frame.read()
    try:
        pil_img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        return {"error": "Invalid image frame", "detections": []}

    img = np.array(pil_img)
    t0 = time.perf_counter()
    results = yolo_model.predict(img, imgsz=imgsz, conf=conf, verbose=False)[0]
    infer_ms = round((time.perf_counter() - t0) * 1000, 1)

    detections = []
    for box in results.boxes:
        cls_id = int(box.cls[0])
        detections.append({
            "label": yolo_model.names[cls_id],
            "conf": round(float(box.conf[0]), 3),
            "bbox": [round(float(x), 1) for x in box.xyxy[0].tolist()],
        })

    loc = SENSOR_LOCATIONS.get(sensor_id, {"lat": 0.0, "lon": 0.0, "label": sensor_id})
    payload = {
        "sensor_id": sensor_id,
        "lat": loc["lat"],
        "lon": loc["lon"],
        "infer_ms": infer_ms,
        "count": len(detections),
        "detections": detections,
    }
    if detections:
        await broadcast_event("YOLO_DETECTION", payload)

    return payload


@app.post("/api/geoclip")
async def geolocate_image(image: UploadFile = File(...), top_k: int = Form(5)):
    if geoclip_model is None:
        return {"error": "GeoCLIP model not loaded", "predictions": []}

    suffix = Path(image.filename or "frame.jpg").suffix or ".jpg"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await image.read())
            tmp_path = tmp.name

        top_pred_gps, top_pred_prob = geoclip_model.predict(tmp_path, top_k=top_k)
        predictions = []
        for i in range(len(top_pred_gps)):
            lat = float(top_pred_gps[i][0].item())
            lon = float(top_pred_gps[i][1].item())
            prob = float(top_pred_prob[i].item())
            predictions.append({
                "rank": i + 1,
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "probability": round(prob, 6),
            })

        result = {"predictions": predictions}
        if predictions:
            await broadcast_event("GEOCLIP_PREDICTION", {
                "top": predictions[0],
                "all": predictions,
            })
        return result
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.get("/api/geoip")
async def lookup_geoip(ip: str):
    if geoip_reader is not None:
        try:
            resp = geoip_reader.city(ip)
            data = {
                "source": "maxmind_mmdb",
                "ip": ip,
                "country": resp.country.name,
                "region": resp.subdivisions.most_specific.name,
                "city": resp.city.name,
                "lat": resp.location.latitude,
                "lon": resp.location.longitude,
                "accuracy_radius_km": resp.location.accuracy_radius,
            }
            await broadcast_event("GEOIP_LOOKUP", data)
            return data
        except Exception as exc:
            return {"error": f"MMDB lookup failed: {exc}", "ip": ip}

    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"https://ipapi.co/{ip}/json/")
        raw = r.json()
        data = {
            "source": "ipapi_fallback",
            "ip": ip,
            "country": raw.get("country_name"),
            "region": raw.get("region"),
            "city": raw.get("city"),
            "lat": raw.get("latitude"),
            "lon": raw.get("longitude"),
            "org": raw.get("org"),
        }
        await broadcast_event("GEOIP_LOOKUP", data)
        return data


@app.get("/api/nasa/eonet")
async def nasa_eonet(days: int = 7, limit: int = 25):
    url = f"https://eonet.gsfc.nasa.gov/api/v3/events?days={days}&limit={limit}&status=open"
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        payload = r.json()
    await broadcast_event("NASA_EONET_SYNC", {"count": len(payload.get("events", []))})
    return payload


@app.get("/api/osm/search")
async def osm_search(q: str, limit: int = 5):
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "GeoFuse-Termux-Client/1.0"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url, params={"q": q, "format": "json", "limit": limit}, headers=headers)
        r.raise_for_status()
        return r.json()


@app.websocket("/ws/telemetry")
async def telemetry_ws(ws: WebSocket):
    await ws.accept()
    connected_clients.add(ws)
    await ws.send_text(json.dumps({
        "type": "CONNECTED",
        "ts": int(time.time() * 1000),
        "data": {"clients": len(connected_clients)},
    }))
    try:
        while True:
            msg = await ws.receive_text()
            if msg == "PING":
                await ws.send_text(json.dumps({"type": "PONG", "ts": int(time.time() * 1000)}))
    except WebSocketDisconnect:
        connected_clients.discard(ws)
