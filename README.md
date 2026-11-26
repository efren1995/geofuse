Here is a complete README.md tailored for efren1995/geofuse, covering the Android WebView client (geofuse-debug.apk), the local FastAPI workbench (~/geofuse/server.py and ~/geofuse/web/index.html), the nine research sectors plus Cases, and Termux setup.
# GeoFuse

GeoFuse is a unified multi-sector open-source research platform built for lawful OSINT, visual verification, network analysis, financial tracing, spectrum awareness, and case investigation. It pairs an Android WebView client (`geofuse-debug.apk`) with a local FastAPI backend (`127.0.0.1:8000`) and interactive Leaflet map UI designed to run smoothly on mobile/Termux environments as well as desktop Linux.

> **Responsible & Lawful Use:** Scan only systems, networks, or links you own or are explicitly authorized to assess. Respect platform terms of service, privacy boundaries, and applicable laws.

---

## Research Sectors & Modules

1. **Camera Globe** — MediaMTX path sync & polling (`/api/poller`, `/api/stream`, `/api/stream/sync`), `ffmpeg`/OpenCV frame snapshots (`/api/snapshot`, `/api/snapshot/latest/image`), public camera feed ingestion & bounding-box/class filtering (`/api/cameras`, `/api/cameras/load`, `/api/cameras/inspect`, `/api/cameras/scan-bbox`), and **Ultralytics YOLOv8** object detection (`/api/detect/image`, `/api/detect/path`, `/api/detections`).
2. **Hawk & GeoCLIP** — **GeoCLIP** coordinate prediction (`/api/geolocate/image`, `/api/geolocate/path`, `/api/coordinates`), EXIF metadata extraction (GPS, camera make/model, timestamps), driving-side constraints, and verification status reporting.
3. **Username Research** — Concurrent public profile probes across major platforms (GitHub, GitLab, Reddit, Keybase, HackerNews) via `/api/sector/username/live`.
4. **Crypto Tracing** — Automatic chain detection (Bitcoin, Ethereum/EVM, Solana, Tron, XRP, Cardano) and live balance/transaction queries via `/api/sector/crypto/live` plus fusion event logging (`/api/fuse`).
5. **NetScan** — Authorized host/domain/`.onion` inspection covering DNS resolution, RDAP/GeoIP lookup, TCP port checks, TLS certificate details, HTTP headers, and Certificate Transparency (`crt.sh`) subdomains via `/api/sector/netscan/live`.
6. **Skywave** — Frequency band-plan classification, time-of-day propagation notes, and nearest public **KiwiSDR** receivers ranked by distance via `/api/sector/skywave/live`.
7. **Linkscope** — Authorized redirect analytics (`/r/{slug}`) with click counts, visitor headers, and GeoIP context via `/api/sector/linkscope/create` and `/api/sector/linkscope/stats`.
8. **Catalogue** — Official registry and entity lookups (including Wikidata) alongside curated deep-links and access-status notes via `/api/sector/catalogue/live`.
9. **Watchtower** — Live situational feeds (USGS earthquakes, NASA EONET hazards, and OpenSky aircraft states) with proximity cross-layer correlation via `/api/sector/watchtower/live`.
10. **Cases** — Entity board (`person`, `address`, `account`, `device`, `wallet`), link edges, 2-hop expansion, and a privacy email blacklist (`/api/sector/cases`, `/api/sector/cases/blacklist`).

---

## Open Foundations

* **OpenStreetMap** — Interactive map tiles and geographic markers.
* **NASA Earth Observatory & Worldview** — Satellite imagery and Earth science references.
* **MaxMind GeoIP** — Optional local `.mmdb` IP geolocation (with RDAP fallback).
* **GeoCLIP** — Visual geolocation predictions.
* **Ultralytics YOLOv8** — Local object detection across COCO classes.

---

## Quick Start (Termux / Localhost)

### 1. Start the Backend

```bash
cd ~/geofuse || exit 1
termux-wake-lock 2>/dev/null || true
nohup "$HOME/run_geofuse.sh" > "$HOME/geofuse_stack.log" 2>&1 &

Verify health and open routes:
curl -fsS [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

2. Open the Console
 * Browser / Android WebView (geofuse-debug.apk): http://127.0.0.1:8000/
 * Logs & Snapshots: Written to /sdcard/Download/geofuse_logs/ (with fallback to ~/geofuse_logs/).
Key API Endpoints
| Method & Path | Purpose |
|---|---|
| GET /health & GET /api/status | Service health, uptime, model load state, and counters |
| GET / POST /api/poller & POST /api/stream/sync | MediaMTX background polling and path synchronization |
| GET / POST /api/snapshot | Capture stream snapshots (optionally running YOLOv8 / GeoCLIP) |
| POST /api/detect/image & POST /api/detect/path | Run YOLOv8 object detection on uploaded or local images |
| POST /api/geolocate/image & POST /api/geolocate/path | Run GeoCLIP + EXIF inspection and record coordinates |
| GET / POST /api/cameras, /load, /inspect, /scan-bbox | Manage public camera feeds and run bounding-box YOLOv8 scans |
| POST /api/sector/{username,crypto,netscan,skywave,catalogue,watchtower}/live | Execute live sector queries |
| POST /api/sector/linkscope/create & GET /r/{slug} | Create and resolve authorized tracking links |
| GET / POST /api/sector/cases & /blacklist | Manage case entities, links, and blacklisted emails |
| GET / POST /api/fuse & GET /api/logs | Record fusion events and tail event logs |
Environment Variables
 * GEOFUSE_MEDIAMTX_API (default: http://127.0.0.1:9997)
 * GEOFUSE_MEDIAMTX_RTSP_HOST (default: 127.0.0.1)
 * GEOFUSE_MEDIAMTX_RTSP_PORT (default: 8554)
 * GEOFUSE_POLLER_INTERVAL (default: 5.0)
 * GEOFUSE_POLLER_AUTO_START (default: 1)
 * GEOFUSE_YOLO_MODEL (default: yolov8n.pt)
 * GEOFUSE_MAXMIND_DB (default: ~/geofuse/data/GeoLite2-City.mmdb)
 * WINDY_WEBCAMS_KEY — Optional API key for Windy Webcams v3 loading

<FollowUp label="Want me to write this README.md directly into ~/geofuse/README.md?" query="Write the README.md file directly to ~/geofuse/README.md in Termux."/>

