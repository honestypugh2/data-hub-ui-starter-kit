# UI Architecture — Starter Kit (Phase 1)

## System Overview

```
┌───────────────────┐     JSON + JWT      ┌────────────────────────┐
│   React SPA       │ ──────────────────▶ │  Azure Functions v2    │
│   (Vite + MSAL)   │ ◀────────────────── │  HTTP Triggers         │
│   Port 3000       │    { sas_url, … }   │  (Python, Blueprints)  │
│                   │                     └────────────┬───────────┘
│                   │                                  │
│                   │──── PUT (SAS URL) ──▶ ┌──────────▼───────────┐
└───────────────────┘                      │  Azure Blob Storage   │
                                           │  bronze / gold /      │
                                           │  ui-metadata          │
                                           └──────────┬────────────┘
                                                      │ blob trigger
                                           ┌──────────▼────────────┐
                                           │  Azure Durable Funcs  │
                                           │  → Azure OpenAI       │
                                           │  (AI image tagging)   │
                                           └───────────────────────┘
```

## Component Stack

| Layer | Technology | Version |
|---|---|---|
| SPA framework | React | 19.1 |
| Language | TypeScript | 5.8 |
| Bundler | Vite | 6.3 |
| Auth library | @azure/msal-browser + @azure/msal-react | 5.x |
| API layer | Azure Functions v2 (Python) | Blueprints model |
| Blob SDK | azure-storage-blob | 12.x |
| JWT validation | python-jose (RS256, OIDC key fetch) | — |
| Infra | ZTA, private endpoints, Bastion VM | — |

## Frontend Architecture

### Entry Point

[app/frontend/src/main.tsx](../app/frontend/src/main.tsx) is the single entry point. It checks `import.meta.env.VITE_DEMO_MODE`:

- **Production** — dynamically imports MSAL, creates a `PublicClientApplication`, wraps `<App />` in `<MsalProvider>`.
- **Demo** — dynamically imports `<DemoApp />`, no MSAL or Azure dependencies.

### Component Tree (Production)

```
<MsalProvider>
  <App>                               # Auth gating (Authenticated / Unauthenticated)
    <UnauthenticatedTemplate>
      Sign-in button (loginPopup)
    </UnauthenticatedTemplate>
    <AuthenticatedTemplate>
      <UploadPage />                  # File picker + client-side validation
      <ImageGallery />                # Agency image list, auto-poll 10 s
        └─ <ImageDetail />            # Preview + tags, auto-poll 5 s
           └─ <StatusBadge />         # Pending / Completed / Failed
    </AuthenticatedTemplate>
  </App>
</MsalProvider>
```

### Service Layer

| File | Responsibility |
|---|---|
| `services/auth.ts` | MSAL configuration (`msalConfig`, `loginRequest`). Reads `VITE_AZURE_CLIENT_ID`, `VITE_AZURE_AUTHORITY`, `VITE_AZURE_REDIRECT_URI`, `VITE_API_SCOPE`. |
| `services/api.ts` | Production API client. Acquires token via `acquireTokenSilent`, calls Azure Functions endpoints. Implements two-step SAS upload. |
| `services/demoApi.ts` | Demo API client — identical interface, no MSAL. Targets `VITE_API_BASE_URL`. |

### Environment Variables (Vite)

All frontend env vars use the `VITE_` prefix (Vite convention).

| Variable | Purpose |
|---|---|
| `VITE_AZURE_CLIENT_ID` | Entra ID SPA app registration client ID |
| `VITE_AZURE_AUTHORITY` | `https://login.microsoftonline.com/{tenant}` |
| `VITE_AZURE_REDIRECT_URI` | OAuth redirect (default `http://localhost:3000`) |
| `VITE_API_SCOPE` | Backend API scope (`api://{client-id}/access_as_user`) |
| `VITE_API_BASE_URL` | API origin (default `http://localhost:8000`) |
| `VITE_DEMO_MODE` | `"true"` to enable demo mode |

## API Architecture (Azure Functions v2)

### Blueprint Registration

[app/api/function_app.py](../app/api/function_app.py) registers three blueprints:

| Blueprint | Module | Routes |
|---|---|---|
| `upload_bp` | `upload_initiate/` | `POST /api/upload` |
| `status_bp` | `get_status/` | `GET /api/images`, `GET /api/images/{id}`, `DELETE /api/images/{id}` |
| `results_bp` | `get_results/` | `GET /api/images/{id}/tags` |

Each module follows the pattern: `__init__.py` re-exports `bp` from `init.py`.

### Shared Modules

| Module | Responsibility |
|---|---|
| `shared/auth.py` | Fetches OIDC signing keys from Entra ID, validates RS256 JWT, extracts `CurrentUser` (email, name, oid, agency). |
| `shared/storage.py` | Blob CRUD (upload, download, delete, list, exists). Metadata lifecycle (create, get, refresh status, list by agency, delete). Uses `DefaultAzureCredential` or connection string. |
| `shared/sas.py` | SAS URL generation — `generate_read_sas_url()` (30 min, read) and `generate_write_sas_url()` (15 min, write+create). Both use user-delegation keys. |

## Data Flow — Upload Pipeline

```
1. UI: user picks file
   ├─ Client-side validation (type ∈ {jpeg, png}, size ≤ 20 MB)

2. UI → API: POST /api/upload
   ├─ Headers: Authorization: Bearer <JWT>
   ├─ Body: { filename, content_type, size_bytes }

3. API validates:
   ├─ JWT (audience, issuer, signature via OIDC keys)
   ├─ Extension ∈ {jpg, jpeg, png}
   ├─ Content-Type ∈ {image/jpeg, image/png}
   ├─ size_bytes > 0 and ≤ 20 MB
   ├─ Generates upload_id (UUID[:8]) + sanitized blob name
   ├─ Calls generate_write_sas_url(bronze, blob_name) → 15-min SAS
   ├─ Creates metadata record in ui-metadata container
   └─ Returns { sas_url, upload_id, filename, status, blob_name }

4. UI → Blob Storage: PUT <sas_url>
   ├─ Headers: x-ms-blob-type: BlockBlob, Content-Type: <mime>
   └─ Body: raw file bytes

5. Existing Durable Functions pipeline detects blob in bronze
   ├─ Orchestrator → callAoaiMultiModal → Azure OpenAI
   └─ Writes gold/{upload_id}_{basename}-output.json

6. UI polls:
   ├─ Gallery: GET /api/images every 10 s (while any status = pending)
   └─ Detail: GET /api/images/{id} every 5 s (while status = pending)
   └─ API calls refresh_status() → checks gold container → updates metadata
```

## Data Flow — View / Delete

```
GET /api/images
  → list_agency_metadata(agency) → refresh_status each → return list

GET /api/images/{id}
  → get_metadata(agency, id) → refresh_status
  → generate_read_sas_url(bronze, blob_name) → preview_url
  → if completed: download gold output → include tags

GET /api/images/{id}/tags
  → get_metadata → refresh_status → download gold output JSON

DELETE /api/images/{id}
  → delete bronze blob + gold blob + metadata blob
```

## Blob Storage Layout

| Container | Contents | Naming |
|---|---|---|
| `bronze` | Original uploaded images | `{upload_id}_{sanitized_name}.{ext}` |
| `gold` | AI tagging output (JSON) | `{upload_id}_{sanitized_name}-output.json` |
| `ui-metadata` | Upload tracking records (JSON) | `{agency}/{upload_id}.json` |

## Demo Mode

A standalone mock backend (`app/demo/server.py`, FastAPI + uvicorn) provides the same API surface with in-memory sample data and no Azure dependencies. Launched via `scripts/run-demo.ps1`.
