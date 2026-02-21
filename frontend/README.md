# CircuitScout Frontend

Vite + React single-page app for schematic upload → BOM extraction → substitutes. Connects to the CircuitScout backend and is designed to work with **AWS Strands** orchestration.

## Run instructions

```bash
# 1. Install dependencies
cd frontend
npm install

# 2. Configure backend URL (optional; defaults to empty = same-origin)
cp .env.example .env
# Edit .env and set VITE_API_BASE=http://localhost:8000 (or your backend URL)

# 3. Start dev server
npm run dev
```

Open http://localhost:5173. Build for production: `npm run build`; preview build: `npm run preview`.

## Connecting to a local backend

1. Start your backend (e.g. Python FastAPI) on port 8000:
   ```bash
   # From repo root, example for a uvicorn app in backend/
   cd backend && uvicorn app.main:app --reload --port 8000
   ```
2. Set in frontend `.env`: `VITE_API_BASE=http://localhost:8000`
3. Restart the Vite dev server so it picks up the env.

To avoid CORS, you can proxy in `vite.config.js`:
```js
server: {
  proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } },
}
```
Then use `VITE_API_BASE=""` so requests go to the same origin and get proxied.

## AWS Strands integration (backend contract)

- **Extract**: Frontend calls `POST /api/extract` (multipart `file`, optional `?chaos=true`). Backend should create a job and forward it to **AWS Strands** (or simulate locally). Strands runs the vision/BOM pipeline.
- **Callback**: Strands (or your orchestrator) must call back the backend at **`POST /api/strands-callback`** with JSON body:
  ```json
  { "job_id": "<id>", "status": "done" | "failed", "result": <BOM_JSON> }
  ```
  The backend stores this and updates job state so that **`GET /api/job-status/:job_id`** returns `{ status, progress?, result? }`. The frontend polls this until `status === "done"`.
- **Substitutes**: Frontend calls `POST /api/substitutes/:base_key` with body `{ "qty": 1 }`; backend returns `{ substitutes: [ { key, score, reason, price } ] }`. No Strands callback required for this.

Placeholder comments in code: see `src/api.js` (extract) and this README for where Strands is hooked.

## Demo: Chaos Mode

Chaos Mode adds `?chaos=true` to the extract request. Backend can use it to simulate failures or reduced substitute availability; the frontend will reflect the change when you expand a BOM row (e.g. fewer substitutes).

**Steps:**

1. **Run frontend**
   ```bash
   cd frontend && npm run dev
   ```
2. **Start the included mock backend** (Node, no deps):
   ```bash
   node frontend/scripts/mock-backend.js
   ```
   Or use your real backend on port 8000. Ensure `.env` has `VITE_API_BASE=http://localhost:8000` and restart the Vite dev server.
3. **Upload test schematic** → Click **Analyze** → Wait for job to complete → BOM appears.
4. **Toggle Chaos Mode** → Upload again and click **Analyze**. The mock (or your backend) can return fewer substitutes when chaos is enabled; the UI will show the updated substitutes when you expand a row.

## Manual BOM and export

- **Manual BOM**: Paste valid BOM JSON in the "Manual BOM fallback" textarea and click **Use manual BOM** to bypass the vision step. Works even when the backend is down.
- **Export CSV**: Click **Export CSV** to download the current BOM as a client-generated CSV file.

## File layout

- `index.html` — Entry HTML (Vite expects it at project root).
- `src/main.jsx` — App bootstrap.
- `src/App.jsx` — Main UI (Header, UploadCard, JobStatusCard, BOMList, manual BOM, export).
- `src/api.js` — `extractImage`, `getJobStatus`, `getSubstitutes`, `exportBomToCsv`.
- `tailwind.config.cjs` — Tailwind (optional); comments in code where Tailwind is used.
- `scripts/mock-backend.js` — Optional Node mock for demo (no deps).

No secrets or backend keys are embedded; use `VITE_API_BASE` only.
