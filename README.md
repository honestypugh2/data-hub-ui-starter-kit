# Starter Kit UI (Phase 1 PoC)

A web application starter for uploading images and viewing AI-generated tags. Users sign in with organization-managed credentials (Entra ID), upload JPG/PNG images, and receive AI-generated metadata powered by Azure OpenAI.

## Architecture

```
┌──────────────┐        ┌────────────────────┐       ┌─────────────────────────┐
│  React SPA   │──JWT──▶│  Azure Functions    │──────▶│  Azure Blob Storage     │
│  (Vite +     │◀───────│  HTTP Triggers      │       │  bronze / gold /        │
│   MSAL v5)   │        │  (v2 Blueprints)    │       │  ui-metadata            │
│              │        └────────────────────┘       └──────────┬──────────────┘
│              │──SAS──▶ Azure Blob (direct PUT)                │ blob trigger
└──────────────┘                                     ┌──────────▼──────────────┐
                                                     │  Azure Durable Functions │
                                                     │  (existing pipeline)     │
                                                     │  → Azure OpenAI          │
                                                     └──────────────────────────┘
```

| Component | Tech | Purpose |
|---|---|---|
| Frontend | React 19, TypeScript, Vite, MSAL React v5 | SPA with Entra ID authentication |
| API | Azure Functions v2 (Python, Blueprints) | REST API — upload, list, detail, delete |
| Backend (legacy) | FastAPI (Python) | Earlier direct-upload implementation |
| Storage | Azure Blob Storage | `bronze` (input), `gold` (output), `ui-metadata` (tracking) |
| Processing | Azure Durable Functions + Azure OpenAI | AI image tagging via `callAoaiMultiModal` |
| Auth | Microsoft Entra ID (Azure AD) | JWT validation, agency derived from user claims |
| Infra | Network-isolated (ZTA), private endpoints, Bastion VM | Zero-trust architecture |

## How It Works

1. User signs in via Entra ID (MFA enforced). Their agency is auto-identified from JWT claims.
2. User selects a JPG/PNG image through the UI.
3. The UI sends upload metadata (filename, content type, size) to the API. The API validates the request, generates a unique ID, and returns a **write SAS URL** for the `bronze` blob container.
4. The UI uploads the file **directly** to Azure Blob Storage using the SAS URL (PUT request).
5. A metadata record is created in `ui-metadata` to track processing status.
6. The existing Azure Durable Functions pipeline detects the new blob, processes it through Azure OpenAI (`callAoaiMultiModal`), and writes results to `gold/{name}-output.json`.
7. The gallery auto-polls (10 s) and the detail view auto-polls (5 s). When the output blob is found, status updates from `pending` to `completed`.
8. AI-generated tags (JSON) are displayed in the detail view.

## API Endpoints (Azure Functions)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/upload` | Accept upload metadata, return a write SAS URL |
| `GET` | `/api/images` | List all images for the user's agency |
| `GET` | `/api/images/{upload_id}` | Image detail with preview URL and tags |
| `GET` | `/api/images/{upload_id}/tags` | AI-generated tags only |
| `DELETE` | `/api/images/{upload_id}` | Delete image + output + metadata |

All endpoints require a valid Entra ID Bearer token.

## Project Structure

```
app/
├── api/                            # Azure Functions v2 (production API)
│   ├── function_app.py             # Entry point – registers blueprints
│   ├── host.json
│   ├── local.settings.json
│   ├── requirements.txt
│   ├── upload_initiate/
│   │   ├── __init__.py             # Re-export: from .init import bp
│   │   └── init.py                 # POST /api/upload (SAS URL flow)
│   ├── get_status/
│   │   ├── __init__.py
│   │   └── init.py                 # GET /api/images, GET/DELETE /api/images/{id}
│   ├── get_results/
│   │   ├── __init__.py
│   │   └── init.py                 # GET /api/images/{id}/tags
│   └── shared/
│       ├── __init__.py
│       ├── auth.py                 # Entra ID JWT validation
│       ├── sas.py                  # SAS URL generation (read + write)
│       └── storage.py              # Blob Storage CRUD + metadata
├── backend/                        # Legacy FastAPI implementation
│   ├── main.py
│   ├── config.py
│   ├── auth.py
│   ├── requirements.txt
│   ├── routes/
│   │   ├── upload.py
│   │   └── images.py
│   └── services/
│       ├── blob_service.py
│       └── metadata_service.py
├── demo/                           # Standalone demo (no Azure required)
│   ├── server.py                   # FastAPI mock server with sample data
│   └── requirements.txt
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts              # Vite config (port 3000)
    ├── index.html                  # App shell (Vite entry)
    ├── .env.demo                   # Demo mode environment vars
    └── src/
        ├── main.tsx                # Entry – switches demo / production
        ├── App.tsx                 # Production root (MSAL auth flow)
        ├── DemoApp.tsx             # Demo root (no auth)
        ├── App.css
        ├── types.ts
        ├── react-app-env.d.ts      # Vite ImportMetaEnv types
        ├── services/
        │   ├── api.ts              # Production API client (MSAL tokens)
        │   ├── demoApi.ts          # Demo API client (no auth)
        │   └── auth.ts             # MSAL / Entra ID configuration
        └── components/
            ├── Upload/
            │   ├── UploadPage.tsx
            │   └── DemoUploadPage.tsx
            ├── ImageGallery/
            │   ├── ImageGallery.tsx
            │   └── DemoImageGallery.tsx
            ├── ImageDetail/
            │   ├── ImageDetail.tsx
            │   └── DemoImageDetail.tsx
            └── Status/
                └── StatusBadge.tsx
scripts/
└── run-demo.ps1                    # Launch demo backend + frontend
```

## Prerequisites

- Python 3.13+
- Node.js 18+
- An Azure subscription with:
  - A storage account with `bronze`, `gold`, and `ui-metadata` containers
  - Entra ID app registration for both frontend (SPA) and backend (API)
  - An existing Durable Functions pipeline for image processing

## Getting Started

### Quick Demo (no Azure required)

The demo mode runs a standalone mock server with sample data so the full UI can be explored without any Azure resources.

```powershell
# One-time setup
python -m venv .venv
.venv\Scripts\Activate.ps1
uv add fastapi uvicorn
cd app\frontend && npm install && cd ..\..

# Launch both servers
.\scripts\run-demo.ps1
```

This starts the FastAPI mock backend on `http://localhost:8000` and the Vite frontend on `http://localhost:3000`. Press **Enter** in the launcher window to stop both.

### Production – Azure Functions API

```bash
cd app/api
python -m venv .venv
.venv/Scripts/Activate.ps1        # Windows
pip install -r requirements.txt
```

Configure `local.settings.json` with your Azure credentials, then start the Function host:

```bash
func start
```

### Production – Frontend

```bash
cd app/frontend
npm install
```

Create a `.env` file with your Entra ID and API settings:

```env
VITE_API_BASE_URL=http://localhost:7071
VITE_AZURE_CLIENT_ID=<your-frontend-client-id>
VITE_AZURE_AUTHORITY=https://login.microsoftonline.com/<your-tenant-id>
VITE_AZURE_REDIRECT_URI=http://localhost:3000
VITE_API_SCOPE=api://<your-backend-client-id>/access_as_user
```

Start the dev server:

```bash
npm start
```

The app opens at `http://localhost:3000`.

## Key Azure Resources

| Resource | Example |
|---|---|
| Storage Account | `<your-storage-account>` |
| Function App | `<your-processing-function-app>` |
| Resource Group | `<your-resource-group>` |
| AI Foundry | `<your-ai-foundry-resource>` |
| App Configuration | `<your-app-configuration-resource>` |

## Phase 1 Scope

**In scope:** Entra ID auth with MFA, single image upload (JPG/PNG), file validation, AI tagging via existing pipeline, list/detail/delete by agency, auto-polling for status updates, SAS-based direct upload, demo mode.

**Out of scope:** Admin controls, search, centralized workflows, enterprise audit, accessibility hardening.