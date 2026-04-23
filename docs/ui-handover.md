# UI Handover Guide — Starter Kit (Phase 1 PoC)

## Quick Start

### Prerequisites

| Tool | Version |
|---|---|
| Python | ≥ 3.13 |
| Node.js | ≥ 18 |
| npm | ≥ 9 |
| Azure Functions Core Tools | v4 (for production API) |

### Run the Demo (no Azure required)

```powershell
# Clone and set up Python venv
python -m venv .venv
.venv\Scripts\Activate.ps1
uv add fastapi uvicorn          # or: pip install fastapi uvicorn

# Install frontend dependencies
cd app\frontend
npm install
cd ..\..

# Launch both servers
.\scripts\run-demo.ps1
```

- Frontend: `http://localhost:3000`
- Backend (mock): `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`

Press **Enter** in the launcher window to stop both processes.

### Run Production Locally

#### API (Azure Functions)

```bash
cd app/api
pip install -r requirements.txt
```

Configure `local.settings.json`:

```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage": "<connection-string>",
    "AZURE_STORAGE_CONNECTION_STRING": "<connection-string>",
    "AZURE_STORAGE_ACCOUNT_URL": "https://<your-storage-account>.blob.core.windows.net",
    "AZURE_TENANT_ID": "<tenant-id>",
    "AZURE_CLIENT_ID": "<backend-client-id>"
  }
}
```

```bash
func start
```

#### Frontend

```bash
cd app/frontend
npm install
```

Create `.env`:

```env
VITE_API_BASE_URL=http://localhost:7071
VITE_AZURE_CLIENT_ID=<frontend-spa-client-id>
VITE_AZURE_AUTHORITY=https://login.microsoftonline.com/<tenant-id>
VITE_AZURE_REDIRECT_URI=http://localhost:3000
VITE_API_SCOPE=api://<backend-client-id>/access_as_user
```

```bash
npm start          # Vite dev server on port 3000
npm run build      # Production build → app/frontend/build/
```

---

## Repository Layout

```
datahub_ui_poc/
├── app/
│   ├── api/                        ← Azure Functions v2 (production)
│   │   ├── function_app.py         ← Entry: registers 3 blueprints
│   │   ├── host.json
│   │   ├── local.settings.json
│   │   ├── requirements.txt
│   │   ├── upload_initiate/        ← POST /api/upload
│   │   ├── get_status/             ← GET /api/images, GET|DELETE /api/images/{id}
│   │   ├── get_results/            ← GET /api/images/{id}/tags
│   │   └── shared/                 ← auth.py, storage.py, sas.py
│   ├── backend/                    ← Legacy FastAPI (earlier iteration)
│   ├── demo/                       ← Standalone mock server (FastAPI)
│   │   ├── server.py
│   │   └── requirements.txt
│   └── frontend/                   ← React + Vite SPA
│       ├── package.json
│       ├── vite.config.ts
│       ├── tsconfig.json
│       ├── index.html
│       ├── .env.demo
│       └── src/
│           ├── main.tsx            ← Entry: demo vs production mode
│           ├── App.tsx             ← Production root (MSAL gated)
│           ├── DemoApp.tsx         ← Demo root (no auth)
│           ├── types.ts
│           ├── services/
│           │   ├── api.ts          ← Production API client
│           │   ├── demoApi.ts      ← Demo API client
│           │   └── auth.ts         ← MSAL config
│           └── components/
│               ├── Upload/         ← UploadPage, DemoUploadPage
│               ├── ImageGallery/   ← ImageGallery, DemoImageGallery
│               ├── ImageDetail/    ← ImageDetail, DemoImageDetail
│               └── Status/         ← StatusBadge
├── scripts/
│   └── run-demo.ps1                ← Demo launcher (backend + frontend)
├── docs/                           ← This documentation
├── infra/                          ← Infrastructure definitions
├── pyproject.toml                  ← Python ≥ 3.13, uv project
└── README.md
```

---

## Key Concepts

### Two-Step SAS Upload

The frontend never proxies file bytes through the API. Instead:

1. `POST /api/upload` sends **metadata only** (`filename`, `content_type`, `size_bytes`) → returns a 15-minute write SAS URL.
2. The frontend PUTs the raw file directly to Azure Blob Storage using the SAS URL.

This keeps the API stateless and avoids large-payload bottlenecks.

### Agency Isolation

The user's agency is extracted from the JWT `department` (or `agency`) claim. All metadata records are stored under `ui-metadata/{agency}/{upload_id}.json`. Listing images scopes to the caller's agency automatically.

### Auto-Polling

- **ImageGallery** polls `GET /api/images` every 10 seconds while any image has `status: "pending"`.
- **ImageDetail** polls `GET /api/images/{id}` every 5 seconds while the viewed image has `status: "pending"`.

Polling stops once all statuses resolve to `completed` or `failed`.

### Status Refresh

The API function `refresh_status()` checks whether a gold-container output blob exists for a pending image. If found, the metadata is updated in-place to `completed`. This is called on every list and detail request.

### Blueprint Pattern

Each API capability is a separate `func.Blueprint()` in its own package:

| Package | Blueprint | Endpoints |
|---|---|---|
| `upload_initiate` | `upload_bp` | `POST /api/upload` |
| `get_status` | `status_bp` | `GET /api/images`, `GET /api/images/{id}`, `DELETE /api/images/{id}` |
| `get_results` | `results_bp` | `GET /api/images/{id}/tags` |

`__init__.py` in each package re-exports `bp` from `init.py`.  
`function_app.py` registers all three into a single `FunctionApp`.

---

## Azure Resources

| Resource | Name | Purpose |
|---|---|---|
| Storage Account | `<your-storage-account>` | bronze, gold, ui-metadata containers |
| Function App (pipeline) | `<your-processing-function-app>` | Durable Functions AI tagging pipeline |
| Resource Group | `<your-resource-group>` | All resources |
| AI Foundry | `<your-ai-foundry-resource>` | Azure OpenAI endpoint |
| App Configuration | `<your-app-configuration>` | Feature flags and settings |

---

## Environment Variables Reference

### API (Azure Functions)

| Variable | Required | Description |
|---|---|---|
| `AZURE_STORAGE_CONNECTION_STRING` | Yes* | Storage connection string (local dev) |
| `AZURE_STORAGE_ACCOUNT_URL` | Yes* | Storage account URL (managed identity) |
| `AZURE_TENANT_ID` | Yes | Entra ID tenant |
| `AZURE_CLIENT_ID` | Yes | Backend app registration client ID |
| `BRONZE_CONTAINER` | No | Default: `bronze` |
| `GOLD_CONTAINER` | No | Default: `gold` |
| `METADATA_CONTAINER` | No | Default: `ui-metadata` |
| `MAX_UPLOAD_SIZE_MB` | No | Default: `20` |
| `ALLOWED_EXTENSIONS` | No | Default: `jpg,jpeg,png` |

\* Provide one of connection string (local) or account URL (deployed with managed identity).

### Frontend (Vite)

| Variable | Required | Description |
|---|---|---|
| `VITE_AZURE_CLIENT_ID` | Yes | SPA app registration client ID |
| `VITE_AZURE_AUTHORITY` | Yes | `https://login.microsoftonline.com/{tenant}` |
| `VITE_AZURE_REDIRECT_URI` | No | Default: `http://localhost:3000` |
| `VITE_API_SCOPE` | Yes | Backend API scope |
| `VITE_API_BASE_URL` | No | Default: `http://localhost:8000` |
| `VITE_DEMO_MODE` | No | Set to `true` for demo mode |

---

## Build & Deploy

### Frontend Build

```bash
cd app/frontend
npm run build         # Output → app/frontend/build/
```

The `build/` directory is a static site suitable for Azure Static Web Apps, Azure Blob static hosting, or any CDN.

### API Deployment

```bash
cd app/api
func azure functionapp publish <function-app-name>
```

Ensure the Function App has:
- `AZURE_STORAGE_ACCOUNT_URL` set to the storage account endpoint.
- A system-assigned managed identity with **Storage Blob Data Contributor** on the storage account.
- `AZURE_TENANT_ID` and `AZURE_CLIENT_ID` configured.

---

## Known Limitations (Phase 1)

- Single image upload only (no batch).
- No full-text search or advanced filtering.
- No admin UI for managing agencies or users.
- Status polling is client-driven; no WebSocket or push notification.
- The `app/backend/` directory contains an earlier FastAPI implementation and is not used in the current architecture.

---

## Phase 2 Considerations

- Gallery UX improvements (thumbnail grid, infinite scroll).
- Admin dashboard with cross-agency visibility.
- WebSocket or Server-Sent Events to replace polling.
- Batch upload support.
- Accessibility audit (WCAG 2.1 AA).
- Enterprise audit logging.
