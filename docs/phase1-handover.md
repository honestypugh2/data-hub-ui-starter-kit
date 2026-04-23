# Technical Handover Document

## Starter Kit UI — Phase 1

### Generic Organization — GenAI Image Processor

---

| Field | Value |
|---|---|
| **Organization** | Target organization |
| **Project** | Starter Kit UI — Phase 1 (PoC) |
| **Document Version** | v1.0 |
| **Document Status** | Final — Technical Handover |
| **Reference Repository** | https://github.com/Azure/ai-document-processor |
| **Azure Portal** | https://portal.azure.com |
| **Resource Group** | `<your-resource-group>` |

> **CONFIDENTIAL:** This document is confidential and intended solely for the receiving technical team. It contains system architecture details, Azure resource names, and deployment procedures. Please handle it accordingly.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Project Overview](#2-project-overview)
3. [System Architecture](#3-system-architecture)
4. [Operational Guide](#4-operational-guide)
5. [Troubleshooting & Debugging](#5-troubleshooting--debugging)
6. [Deployment & Redeployment](#6-deployment--redeployment)
7. [Infrastructure as Code (Bicep)](#7-infrastructure-as-code-bicep)
8. [Security Considerations](#8-security-considerations)
9. [Known Limitations & Phase 2 Considerations](#9-known-limitations--phase-2-considerations)
10. [Support & Contacts](#10-support--contacts)

---

## 1. Introduction

This document provides a comprehensive technical handover for the **Starter Kit UI — Phase 1** web application. It is designed to equip the receiving technical team with all necessary context, architecture details, operational procedures, and troubleshooting guidance required to take full ownership and continue development of the solution.

The handover covers the following key areas:

- Solution purpose, scope, and business objectives
- System architecture and Azure resource topology
- Step-by-step operational walkthrough (upload → process → retrieve)
- Debugging and log monitoring procedures
- Deployment and redeployment instructions
- Infrastructure-as-code (Bicep) deployment guide
- Security model and threat mitigations
- Known limitations and recommended next steps

> **IMPORTANT:** This solution is a Proof of Concept (PoC). It is not production-hardened and is intended to validate feasibility and guide design decisions for a production-grade implementation.

---

## 2. Project Overview

### 2.1 Business Objective

The target organization required a **web-based user interface** that allows department staff to:

1. Sign in securely with organization credentials (Microsoft Entra ID with MFA).
2. Upload images (JPG/PNG) through a browser-based UI.
3. Have those images automatically processed by the existing Azure OpenAI pipeline for AI tagging.
4. View the AI-generated tags (JSON output) for each uploaded image.
5. Manage their uploads (list, view, delete) scoped to their agency.

This UI layer extends the existing GenAI Image Processor PoC (which previously required manual blob uploads through the Azure Portal or VM) into a self-service experience for agency staff.

### 2.2 Scope

The Phase 1 PoC delivers the following capabilities:

| Capability | Description | Status |
|---|---|---|
| **Entra ID Authentication** | Sign-in via Microsoft Entra ID with MFA enforcement, agency auto-identified from JWT claims | Delivered |
| **Image Upload** | Single image upload (JPG/PNG), client-side and server-side validation, max 20 MB | Delivered |
| **SAS-Based Direct Upload** | Two-step upload — API returns a write SAS URL, UI uploads directly to Blob Storage | Delivered |
| **AI Processing Integration** | Upload to `bronze` container triggers the existing Azure Durable Functions → Azure OpenAI pipeline | Delivered |
| **Image Gallery** | List all images for the user's agency with auto-polling status updates (10 s interval) | Delivered |
| **Image Detail View** | Preview uploaded image, view AI tags (JSON), auto-poll for completion (5 s interval) | Delivered |
| **Image Deletion** | Delete image, output, and metadata through the UI | Delivered |
| **Agency Isolation** | All data operations scoped to the caller's agency (derived from JWT `department` claim) | Delivered |
| **Demo Mode** | Standalone mock server with sample data — full UI exploration without Azure dependencies | Delivered |
| **Infrastructure as Code** | Bicep templates for all Phase 1 Azure resources | Delivered |

### 2.3 Out of Scope (Phase 1)

- Gallery UX improvements (thumbnail grid, infinite scroll)
- Admin dashboard with cross-agency visibility
- Full-text search or advanced filtering
- Batch/multi-image upload
- WebSocket or push notifications (polling only)
- Enterprise audit logging
- Accessibility hardening (WCAG 2.1 AA)
- Centralized workflow management

### 2.4 Key Technical Constraints

- Input formats supported: `.jpg`, `.jpeg`, and `.png` only
- Maximum file size: 20 MB per image
- Output format: `.json` (AI-generated tags)
- Processing triggered by blob upload event (not real-time)
- Single output file generated per input image
- Client-driven polling for status updates (no server push)

---

## 3. System Architecture

### 3.1 Architecture Overview

The solution adds a **React SPA frontend** and an **Azure Functions v2 HTTP API layer** on top of the existing GenAI Image Processor pipeline. The frontend communicates with the API via JWT-authenticated requests. File uploads bypass the API entirely — the UI uploads directly to Azure Blob Storage using time-limited SAS URLs.

```
┌───────────────────────┐     JSON + JWT      ┌─────────────────────────┐
│   React SPA           │ ──────────────────▶ │  Azure Functions v2     │
│   (Vite + MSAL v5)    │ ◀────────────────── │  HTTP Triggers          │
│   Static Web App      │   { sas_url, … }    │  (Python, Blueprints)   │
│                       │                     └───────────┬─────────────┘
│                       │                                 │ Managed Identity
│                       │──── PUT (SAS URL) ──▶ ┌─────────▼─────────────┐
└───────────────────────┘                      │  Azure Blob Storage    │
                                               │  bronze / gold /       │
                                               │  ui-metadata           │
                                               └─────────┬─────────────┘
                                                         │ blob trigger
                                               ┌─────────▼─────────────┐
│  Log Analytics + App Insights  │◀────────────│  Azure Durable Funcs   │
│  (monitoring & telemetry)      │             │  → Azure OpenAI        │
└────────────────────────────────┘             │  (AI image tagging)    │
                                               └────────────────────────┘
```

### 3.2 Component Stack

| Layer | Technology | Version |
|---|---|---|
| SPA Framework | React | 19.1 |
| Language (Frontend) | TypeScript | 5.8 |
| Bundler | Vite | 6.3 |
| Auth Library (Frontend) | `@azure/msal-browser` + `@azure/msal-react` | v5.x |
| Frontend Hosting | Azure Static Web App | Free or Standard SKU |
| API Layer | Azure Functions v2 (Python) | Blueprints model |
| Language (API) | Python | 3.13 |
| Blob SDK | `azure-storage-blob` | 12.x |
| Identity SDK | `azure-identity` | 1.x |
| JWT Validation | `python-jose` (RS256, OIDC key fetch) | — |
| HTTP Client | `httpx` | 0.28 |
| Monitoring | Application Insights + Log Analytics | — |
| Infrastructure | Bicep (Azure Resource Manager) | — |
| Network | ZTA, private endpoints, Bastion VM (production) | — |

### 3.3 Azure Resource Inventory

All resources are deployed within the resource group `rg-rg-datahub-genai`.

**Existing Resources (GenAI Image Processor PoC):**

| Resource Type | Resource Name | Purpose |
|---|---|---|
| Resource Group | `rg-rg-datahub-genai` | Container for all project resources |
| Storage Account | `st43mspjkjywpoqdata` | Blob storage for images and metadata |
| Function App (Pipeline) | `func-processing-43mspjkjywpoq` | Azure Durable Functions — AI image tagging |
| AI Foundry | `aif-43mspjkjywpoq` | Azure OpenAI models and endpoints |
| App Configuration | `appconfig-43mspjkjywpoq` | Feature flags and settings |
| Virtual Machine | `vm-43mspjkjywpo` | Bastion jump box (network-isolated access) |

**New Resources (Phase 1 UI — deployed via `infra/` Bicep):**

| Resource Type | Resource Name Pattern | Purpose |
|---|---|---|
| Function App (UI API) | `func-datahub-ui-{suffix}` | HTTP API endpoints for the UI |
| App Service Plan | `asp-datahub-ui-{suffix}` | Consumption (Y1) or Flex Consumption (FC1) |
| Static Web App | `swa-datahub-{suffix}` | Hosts the React SPA frontend |
| Log Analytics Workspace | `log-datahub-{suffix}` | Centralized log collection |
| Application Insights | `appi-datahub-{suffix}` | APM telemetry for the Function App |
| RBAC Role Assignments | — | Storage Blob Data Contributor + Blob Delegator |
| VNet + Private Endpoints | `vnet-datahub-{suffix}` | Optional — zero-trust networking |

**Blob Containers:**

| Container | Purpose |
|---|---|
| `bronze` | Input landing zone — raw uploaded images |
| `gold` | Output zone — AI-processed `.json` results |
| `ui-metadata` | Per-agency upload tracking metadata (JSON) |
| `prompts` | AI prompt templates |
| `images` | Image assets |
| `silver` | Intermediate processing data |

### 3.4 Processing Pipeline (End-to-End)

The end-to-end pipeline from UI upload to AI tags operates as follows:

```
1. User signs in via Entra ID (MSAL popup, Authorization Code + PKCE)
   └─ JWT access token stored in sessionStorage

2. User selects a JPG/PNG image in the UI
   └─ Client-side validation: type ∈ {jpeg, png}, size ≤ 20 MB

3. UI → API: POST /api/upload
   ├─ Headers: Authorization: Bearer <JWT>
   ├─ Body: { filename, content_type, size_bytes }
   └─ API validates JWT, file type, size; returns { sas_url, upload_id }

4. UI → Blob Storage: PUT <sas_url>
   ├─ Headers: x-ms-blob-type: BlockBlob, Content-Type: <mime>
   └─ Body: raw file bytes (direct to bronze container)

5. Existing Durable Functions pipeline detects blob in bronze
   ├─ start_orchestrator_on_blob (Blob Trigger)
   ├─ process_blob (Orchestrator) → detects image
   ├─ callAoaiMultiModal → Azure OpenAI (base64 image + prompt)
   └─ writeToBlob → gold/{upload_id}_{basename}-output.json

6. UI auto-polls for status updates
   ├─ Gallery: GET /api/images every 10 s (while any status = pending)
   └─ Detail: GET /api/images/{id} every 5 s (while status = pending)
   └─ API checks gold container → updates metadata to "completed"

7. User views AI-generated tags in the detail view
   └─ GET /api/images/{id}/tags returns the full JSON output
```

> **NOTE:** Processing typically completes within 1–3 minutes of upload, depending on image size and Azure OpenAI service latency. Monitor the Function App log stream if processing appears delayed.

### 3.5 API Endpoints

The UI API (Azure Functions v2) exposes the following HTTP endpoints via three Blueprints:

| Blueprint | Module | Method | Route | Description |
|---|---|---|---|---|
| `upload_bp` | `upload_initiate/` | `POST` | `/api/upload` | Accept upload metadata, validate, return write SAS URL |
| `status_bp` | `get_status/` | `GET` | `/api/images` | List all images for the caller's agency |
| `status_bp` | `get_status/` | `GET` | `/api/images/{upload_id}` | Image detail with preview URL and tags |
| `status_bp` | `get_status/` | `DELETE` | `/api/images/{upload_id}` | Delete image, output, and metadata |
| `results_bp` | `get_results/` | `GET` | `/api/images/{upload_id}/tags` | AI-generated tags (JSON) only |

All endpoints require a valid Entra ID Bearer token in the `Authorization` header. Unauthorized requests return HTTP 401.

### 3.6 Frontend Component Tree

```
<MsalProvider>                          # MSAL auth context
  <App>                                 # Auth gating
    <UnauthenticatedTemplate>
      Sign-in button (loginPopup)
    </UnauthenticatedTemplate>
    <AuthenticatedTemplate>
      <UploadPage />                    # File picker + client-side validation
      <ImageGallery />                  # Agency image list, auto-poll 10 s
        └─ <ImageDetail />              # Preview + tags, auto-poll 5 s
           └─ <StatusBadge />           # Pending / Completed / Failed
    </AuthenticatedTemplate>
  </App>
</MsalProvider>
```

The entry point (`main.tsx`) checks `VITE_DEMO_MODE`:
- **Production** — dynamically imports MSAL, creates a `PublicClientApplication`, wraps `<App />` in `<MsalProvider>`.
- **Demo** — dynamically imports `<DemoApp />`, no MSAL or Azure dependencies.

---

## 4. Operational Guide

### 4.1 Running the Demo (No Azure Required)

The demo mode provides a fully functional UI with mock data. No Azure subscription, Entra ID, or storage account is needed.

**Prerequisites:**

| Tool | Version |
|---|---|
| Python | ≥ 3.13 |
| Node.js | ≥ 18 |
| npm | ≥ 9 |

**Steps:**

```powershell
# 1. Clone the repository and set up Python venv
git clone <repo-url>
cd datahub_ui_poc
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Install Python dependencies
uv add fastapi uvicorn          # or: pip install fastapi uvicorn

# 3. Install frontend dependencies
cd app\frontend
npm install
cd ..\..

# 4. Launch both servers
.\scripts\run-demo.ps1
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend (mock API) | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |

Press **Enter** in the launcher window to stop both processes.

The demo mode uses sample data from the existing image processing results. No authentication is required — the user is auto-signed-in as `demo.user@example.org` with department "Sample Department".

### 4.2 Running Production Locally

#### API (Azure Functions)

```powershell
cd app\api
pip install -r requirements.txt
```

Configure `local.settings.json`:

```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage": "<storage-connection-string>",
    "AZURE_STORAGE_CONNECTION_STRING": "<storage-connection-string>",
    "AZURE_STORAGE_ACCOUNT_URL": "https://<your-storage-account>.blob.core.windows.net",
    "AZURE_TENANT_ID": "<your-tenant-id>",
    "AZURE_CLIENT_ID": "<backend-api-client-id>",
    "BRONZE_CONTAINER": "bronze",
    "GOLD_CONTAINER": "gold",
    "METADATA_CONTAINER": "ui-metadata",
    "MAX_UPLOAD_SIZE_MB": "20",
    "ALLOWED_EXTENSIONS": "jpg,jpeg,png"
  },
  "Host": {
    "CORS": "http://localhost:3000",
    "CORSCredentials": true
  }
}
```

Start the Function host:

```powershell
func start
```

The API will be available at `http://localhost:7071`.

#### Frontend

```powershell
cd app\frontend
npm install
```

Create a `.env` file:

```env
VITE_API_BASE_URL=http://localhost:7071
VITE_AZURE_CLIENT_ID=<frontend-spa-client-id>
VITE_AZURE_AUTHORITY=https://login.microsoftonline.com/<tenant-id>
VITE_AZURE_REDIRECT_URI=http://localhost:3000
VITE_API_SCOPE=api://<backend-client-id>/access_as_user
```

```powershell
npm start          # Vite dev server on port 3000
npm run build      # Production build → app/frontend/build/
```

### 4.3 Uploading Images (Production)

1. Navigate to the Static Web App URL (or `http://localhost:3000` for local dev).
2. Click **"Sign in with Microsoft"** — you will be prompted for your organization credentials.
3. After signing in, you will see the Upload section and Image Gallery.
4. Click the file picker and select a `.jpg` or `.png` image (max 20 MB).
5. The UI sends metadata to the API, receives a SAS URL, and uploads the file directly to Blob Storage.
6. The image appears in the gallery with status **"Pending"**.
7. The existing Durable Functions pipeline detects the blob and processes it via Azure OpenAI.
8. After 1–3 minutes, the status updates to **"Completed"** and AI tags are viewable in the detail panel.

### 4.4 Viewing AI-Generated Tags

1. In the Image Gallery, click on an image with status **"Completed"**.
2. The detail view shows:
   - A preview of the uploaded image (via read SAS URL, 30-minute expiry).
   - The AI-generated tags (JSON output from Azure OpenAI).
   - Upload metadata (filename, upload time, agency, status).

### 4.5 Deleting Images

1. In the Image Detail view, click **"Delete"**.
2. This removes:
   - The original image from the `bronze` container.
   - The AI output from the `gold` container.
   - The metadata record from `ui-metadata`.

---

## 5. Troubleshooting & Debugging

### 5.1 Monitoring Function App Logs

The UI API Function App is the primary processing engine for HTTP requests. When an issue occurs, the log stream is the first place to investigate.

1. In the Azure Portal, navigate to the **Resource Group** → select the **Function App** (UI API).
2. In the left navigation, click **Log stream**.
3. The log stream displays real-time output from all function executions.
4. Look for `ERROR` or `Exception` entries.

For the existing processing pipeline, monitor `func-processing-43mspjkjywpoq` separately.

### 5.2 Key Functions to Monitor

**UI API Function App:**

| Function Name | Role | Trigger Type |
|---|---|---|
| `upload_initiate` | Validate upload request, generate write SAS URL, create metadata | HTTP (`POST /api/upload`) |
| `list_images` | List all images for the caller's agency | HTTP (`GET /api/images`) |
| `get_image_detail` | Get image detail with preview URL and tags | HTTP (`GET /api/images/{id}`) |
| `delete_image` | Delete image, output, and metadata | HTTP (`DELETE /api/images/{id}`) |
| `get_image_tags` | Return AI-generated tags (JSON) | HTTP (`GET /api/images/{id}/tags`) |

**Existing Processing Pipeline (`func-processing-43mspjkjywpoq`):**

| Function Name | Role | Trigger Type |
|---|---|---|
| `start_orchestrator_on_blob` | Entry point — initiates Durable Functions orchestration when blob uploaded | Blob Trigger |
| `process_blob` | Routes the file to the appropriate processing function | Orchestrator Activity |
| `callAoaiMultiModal` | Calls Azure OpenAI for image processing with prompt | Orchestrator Activity |
| `writeToBlob` | Writes JSON output to the `gold` container | Orchestrator Activity |

### 5.3 Common Issues & Resolutions

| Symptom | Likely Cause | Resolution |
|---|---|---|
| **Sign-in popup fails or closes** | Entra ID app registration misconfigured, redirect URI mismatch | Verify `VITE_AZURE_CLIENT_ID`, `VITE_AZURE_AUTHORITY`, and redirect URIs in the SPA app registration. |
| **401 Unauthorized on API calls** | JWT validation failing — expired token, wrong audience, or wrong issuer | Check `AZURE_TENANT_ID` and `AZURE_CLIENT_ID` in Function App settings. Verify the API scope matches the backend app registration. |
| **Upload succeeds but image stays "Pending"** | Durable Functions pipeline not triggered, or processing failed | Check the processing Function App (`func-processing-43mspjkjywpoq`) log stream for errors. Verify `AOAI_MULTI_MODAL` is set to `true` in App Configuration. |
| **No output in gold after 15+ minutes** | Processing pipeline failed or timed out | Check `callAoaiMultiModal` logs. Verify Azure OpenAI endpoint and API key in app settings. Check quota limits. |
| **SAS URL returns 403 Forbidden** | Managed identity missing Storage Blob Delegator role | Confirm the Function App MI has both **Storage Blob Data Contributor** and **Storage Blob Delegator** roles on the storage account. |
| **CORS error in browser console** | Function App CORS not configured for the SPA origin | Add the SWA hostname to Function App CORS allowed origins (Portal → Function App → CORS). |
| **Images load but tags show empty** | Gold container output blob missing or malformed JSON | Navigate to the `gold` container in Azure Portal and verify the output blob exists and contains valid JSON. |
| **Function App can't access storage (network isolated)** | VNet integration not active or private endpoint misconfigured | Portal → Function App → Networking → verify VNet Integration is active. |
| **Azure OpenAI quota exceeded** | TPM/RPM limits reached | Check Azure OpenAI resource quotas in the portal; request a limit increase if needed. |
| **Demo mode not working** | Python dependencies not installed or wrong port | Run `pip install fastapi uvicorn` and ensure ports 3000 and 8000 are free. |

### 5.4 Important Environment Variables

**UI API Function App:**

| Variable | Purpose | Default |
|---|---|---|
| `AZURE_TENANT_ID` | Entra ID tenant for JWT validation | — (required) |
| `AZURE_CLIENT_ID` | Backend API app registration client ID | — (required) |
| `AZURE_STORAGE_ACCOUNT_URL` | Storage account blob endpoint (managed identity) | — (required for deployed) |
| `AZURE_STORAGE_CONNECTION_STRING` | Storage connection string (local dev only) | — (optional) |
| `BRONZE_CONTAINER` | Input image container | `bronze` |
| `GOLD_CONTAINER` | AI output container | `gold` |
| `METADATA_CONTAINER` | Upload tracking metadata container | `ui-metadata` |
| `MAX_UPLOAD_SIZE_MB` | Maximum upload file size | `20` |
| `ALLOWED_EXTENSIONS` | Comma-separated allowed file extensions | `jpg,jpeg,png` |

**Existing Processing Pipeline (App Configuration: `appconfig-43mspjkjywpoq`):**

| Variable | Purpose | Default |
|---|---|---|
| `AOAI_MULTI_MODAL` | Enable multimodal image processing (must be `true` for images) | `false` |
| `AI_SERVICES_ENDPOINT` | Azure OpenAI / AI Services endpoint | — (hidden) |

**Frontend (Vite):**

| Variable | Purpose |
|---|---|
| `VITE_AZURE_CLIENT_ID` | SPA app registration client ID |
| `VITE_AZURE_AUTHORITY` | `https://login.microsoftonline.com/{tenant}` |
| `VITE_AZURE_REDIRECT_URI` | OAuth redirect URI |
| `VITE_API_SCOPE` | Backend API scope (`api://{client-id}/access_as_user`) |
| `VITE_API_BASE_URL` | API origin URL |
| `VITE_DEMO_MODE` | Set to `"true"` for demo mode |

---

## 6. Deployment & Redeployment

### 6.1 Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| PowerShell | 7.x (pwsh) | Required shell for running commands |
| Azure CLI (az) | Latest | Azure resource management and Bicep deployment |
| Azure Functions Core Tools | v4 | Function App local dev and publishing |
| Node.js | ≥ 18 | Frontend build toolchain |
| npm | ≥ 9 | Package management |
| Python | ≥ 3.13 | Function App runtime |
| Git | Latest | Version control |

### 6.2 Authentication

Before performing any deployment, authenticate with Azure:

```powershell
az login
az account set --subscription "<YOUR_SUBSCRIPTION_ID>"
```

> **NOTE:** Ensure your account has **Contributor** + **User Access Administrator** roles on the target resource group.

### 6.3 Deploying Infrastructure (Bicep)

See [Section 7: Infrastructure as Code](#7-infrastructure-as-code-bicep) for detailed instructions.

```powershell
# Preview changes
az deployment group what-if `
  --resource-group rg-datahub-ui `
  --template-file infra/main.bicep `
  --parameters infra/main.bicepparam

# Deploy
az deployment group create `
  --resource-group rg-datahub-ui `
  --template-file infra/main.bicep `
  --parameters infra/main.bicepparam
```

### 6.4 Deploying the Function App (UI API)

After infrastructure is provisioned, publish the Function App code:

```powershell
cd app\api
func azure functionapp publish <functionAppName>
```

Replace `<functionAppName>` with the output from the Bicep deployment (e.g., `func-datahub-ui-abc123`).

Ensure the Function App has:
- `AZURE_STORAGE_ACCOUNT_URL` set to the storage account endpoint.
- A system-assigned managed identity with **Storage Blob Data Contributor** and **Storage Blob Delegator** roles.
- `AZURE_TENANT_ID` and `AZURE_CLIENT_ID` configured.

### 6.5 Deploying the Frontend (Static Web App)

**Option A — Azure CLI:**

```powershell
cd app\frontend
npm run build

# Get the deployment token
$token = az staticwebapp secrets list `
  --name <staticWebAppName> `
  --query "properties.apiKey" -o tsv

# Deploy
npx @azure/static-web-apps-cli deploy ./build `
  --deployment-token $token
```

**Option B — GitHub Actions (recommended for CI/CD):**

Connect the Static Web App to your GitHub repository via the Azure Portal → Static Web App → Deployment → GitHub. This creates a GitHub Actions workflow that auto-deploys on push.

### 6.6 Post-Deployment Checklist

After deploying infrastructure and code:

- [ ] Verify Function App is running: visit `https://<functionAppHostname>/api/images` (should return 401 — confirming the endpoint is live and auth is enforced).
- [ ] Verify Static Web App is serving: visit `https://<staticWebAppHostname>` (should show the sign-in page).
- [ ] Update the **Frontend SPA app registration** in Entra ID:
  - Add `https://<staticWebAppHostname>` as a Redirect URI.
- [ ] Create `app/frontend/.env.production` with deployed URLs:
  ```env
  VITE_API_BASE_URL=https://<functionAppHostname>
  VITE_AZURE_CLIENT_ID=<frontend-spa-client-id>
  VITE_AZURE_AUTHORITY=https://login.microsoftonline.com/<tenantId>
  VITE_AZURE_REDIRECT_URI=https://<staticWebAppHostname>
  VITE_API_SCOPE=api://<apiClientId>/access_as_user
  ```
- [ ] Rebuild and redeploy the frontend after updating environment variables.
- [ ] Update Function App CORS if needed (Bicep defaults to `*.azurestaticapps.net`).
- [ ] Set `AOAI_MULTI_MODAL` to `true` in App Configuration (`appconfig-43mspjkjywpoq`) to enable image processing.
- [ ] Test end-to-end: sign in → upload image → wait for processing → view AI tags.

> **CAUTION:** Always test changes in a development resource group before deploying to the production `rg-rg-datahub-genai` group.

---

## 7. Infrastructure as Code (Bicep)

### 7.1 Overview

The `infra/` directory contains Azure Bicep templates that provision all Azure resources required for the Phase 1 UI deployment. The templates are modular, parameterized, and follow Azure best practices.

### 7.2 Module Structure

```
infra/
├── main.bicep              # Orchestrator — wires all modules together
├── main.bicepparam         # Parameters file (edit with your values)
├── README.md               # Detailed infrastructure deployment guide
└── modules/
    ├── monitoring.bicep    # Log Analytics Workspace + Application Insights
    ├── networking.bicep    # VNet, subnets, private DNS zones (optional)
    ├── storage.bicep       # Storage account + 6 blob containers + private endpoint
    ├── function-app.bicep  # Function App + App Service Plan + managed identity
    ├── static-web-app.bicep # Azure Static Web App for React SPA
    └── security.bicep      # RBAC role assignments (Blob Contributor + Delegator)
```

### 7.3 What Gets Deployed

| Resource | Bicep Module | Purpose |
|---|---|---|
| Storage Account (Standard LRS) | `modules/storage.bicep` | `bronze`, `gold`, `ui-metadata`, `prompts`, `images`, `silver` containers |
| Function App (Linux, Python) | `modules/function-app.bicep` | UI API with system-assigned managed identity |
| App Service Plan | `modules/function-app.bicep` | Consumption (Y1) or Flex Consumption (FC1 with VNet) |
| Static Web App | `modules/static-web-app.bicep` | Hosts the React SPA |
| Log Analytics Workspace | `modules/monitoring.bicep` | Centralized log collection |
| Application Insights | `modules/monitoring.bicep` | APM telemetry for Function App |
| RBAC Assignments | `modules/security.bicep` | Storage Blob Data Contributor + Blob Delegator for Function App MI |
| VNet + Private Endpoints *(optional)* | `modules/networking.bicep` | Zero-trust networking with private DNS |

### 7.4 Parameters

Edit `infra/main.bicepparam` before deploying:

| Parameter | Required | Description |
|---|---|---|
| `tenantId` | **Yes** | Your Entra ID tenant ID |
| `apiClientId` | **Yes** | Backend API app registration client ID |
| `environmentName` | No | `dev` (default), `staging`, or `prod` |
| `enableNetworkIsolation` | No | `false` (default). Set `true` for VNet + private endpoints |
| `staticWebAppSku` | No | `Free` (default) or `Standard` |
| `location` | No | Defaults to resource group location |
| `uniqueSuffix` | No | Auto-generated. Override to control resource names |

### 7.5 Deployment Commands

```powershell
# Preview (dry run — no changes)
az deployment group what-if `
  --resource-group rg-datahub-ui `
  --template-file infra/main.bicep `
  --parameters infra/main.bicepparam

# Deploy
az deployment group create `
  --resource-group rg-datahub-ui `
  --template-file infra/main.bicep `
  --parameters infra/main.bicepparam `
  --name datahub-phase1-$(Get-Date -Format 'yyyyMMdd-HHmmss')
```

### 7.6 Security Controls (Applied by Default)

| Control | Implementation |
|---|---|
| No public blob access | `allowBlobPublicAccess: false` |
| No shared key access | `allowSharedKeyAccess: false` — forces Entra ID auth |
| HTTPS only | `supportsHttpsTrafficOnly: true` (storage), `httpsOnly: true` (Function App) |
| TLS 1.2 minimum | Both storage and Function App |
| FTPS disabled | `ftpsState: 'Disabled'` |
| Managed Identity | System-assigned MI on Function App — no secrets in config |
| RBAC | Blob Data Contributor + Blob Delegator (minimum required roles) |
| Soft delete | 7-day blob soft delete retention |

### 7.7 Production Hardening (enableNetworkIsolation = true)

For production, set `enableNetworkIsolation = true`. This enables:

| Feature | Details |
|---|---|
| VNet | `10.0.0.0/16` with two subnets |
| Function App VNet Integration | Outbound traffic routes through VNet |
| Storage Private Endpoint | Blob endpoint accessible only via private IP |
| Private DNS Zone | `privatelink.blob.{suffix}` resolves to private IP |
| Storage Firewall | Default action = Deny (only VNet and Azure services) |
| Flex Consumption Plan | Replaces Y1 Consumption (required for VNet integration) |

> See `infra/README.md` for complete deployment guide, Entra ID app registration instructions, cost estimates, and troubleshooting.

---

## 8. Security Considerations

### 8.1 Authentication & Authorization

**Frontend (MSAL):**

| Property | Value |
|---|---|
| Library | `@azure/msal-browser` v5, `@azure/msal-react` v5 |
| Flow | Authorization Code with PKCE (popup) |
| Token storage | `sessionStorage` (cleared on tab close) |
| MFA | Enforced by tenant Conditional Access policy |
| Scopes | `api://{backend-client-id}/access_as_user` |

**API (JWT Validation):**

| Property | Value |
|---|---|
| Library | `python-jose` |
| Algorithm | RS256 |
| Key source | OIDC discovery (`/.well-known/openid-configuration` → `jwks_uri`) |
| Validated claims | `aud` (backend client ID), `iss` (authority/v2.0) |
| Key caching | JWKS response cached in-process after first fetch |

Every API endpoint calls `validate_token(req)` before any business logic. Failure returns `401` or `503`.

### 8.2 Agency Isolation

The user's agency is derived from the JWT `department` claim (fallback: `agency` claim, default: `"default"`). All data operations scope to the caller's agency:

- Metadata path: `ui-metadata/{agency}/{upload_id}.json`
- List endpoint returns only records under the caller's agency prefix.
- This prevents cross-agency data access without explicit RBAC roles.

### 8.3 SAS Token Security

| SAS Type | Permissions | Scope | Expiry | Key Type |
|---|---|---|---|---|
| Write (upload) | `write`, `create` | Single blob in `bronze` | 15 minutes | User delegation |
| Read (preview) | `read` | Single blob | 30 minutes | User delegation |

- SAS URLs are **blob-scoped** — they cannot list or access other blobs.
- **User delegation keys** are used instead of storage account keys, enabling revocation via Entra ID.
- The API never exposes storage account keys or connection strings to the client.

### 8.4 Input Validation (Defense in Depth)

**Client-side (UploadPage.tsx):**

| Check | Rule |
|---|---|
| File type | `image/jpeg` or `image/png` only |
| File size | ≤ 20 MB |

**Server-side (upload_initiate/init.py):**

| Check | Rule | Response |
|---|---|---|
| JWT present and valid | RS256 signature, audience, issuer | 401 |
| Filename | Non-empty string | 400 |
| Extension | `{jpg, jpeg, png}` | 400 |
| Content-Type | `{image/jpeg, image/png}` | 400 |
| Size | Integer, > 0, ≤ 20 MB | 400 |
| Filename sanitization | `re.sub(r"[^a-zA-Z0-9_\-]", "_", name)` — strips path traversal, special chars | — |

The server **never trusts the client** — all validations are repeated server-side.

### 8.5 Transport Security

| Path | Protection |
|---|---|
| Browser → Azure Functions API | HTTPS (TLS 1.2+) |
| Browser → Azure Blob Storage (SAS upload) | HTTPS (TLS 1.2+) |
| Azure Functions → Blob Storage | Private endpoint (ZTA) or HTTPS with managed identity |
| Azure Functions → Entra ID (OIDC keys) | HTTPS |

### 8.6 Credentials and Secrets

- All Azure service keys and connection strings are stored as **Application Settings** in the Function App, not hardcoded in source code.
- **Never commit** `.env` files, `local.settings.json`, or any file containing credentials to version control.
- The storage account has **shared key access disabled** (`allowSharedKeyAccess: false`). All access uses Entra ID / managed identity.
- The deployed Function App uses `DefaultAzureCredential` → system-assigned managed identity. No secrets in configuration.

### 8.7 Network & Access Control (Production)

| Control | Implementation |
|---|---|
| Network isolation | Private endpoints for storage and Function App |
| No public blob access | Storage account `publicNetworkAccess: Disabled` |
| Admin access | Azure Bastion VM — no direct SSH/RDP exposure |
| Private DNS | Azure Private DNS zones for `*.blob.core.windows.net` |

---

## 9. Known Limitations & Phase 2 Considerations

### 9.1 Known Limitations (Phase 1)

- **Single image upload only** — no batch or multi-file upload support.
- **No full-text search** or advanced filtering of images/tags.
- **No admin UI** for managing agencies, users, or cross-agency views.
- **Client-driven polling** for status updates — no WebSocket or server push notifications.
- **No enterprise audit logging** — individual user actions are logged in Application Insights but not to a formal audit trail.
- The `app/backend/` directory contains an earlier FastAPI implementation and is **not used** in the current architecture. It is retained for reference only.

### 9.2 Phase 2 Considerations

| Feature | Description |
|---|---|
| Gallery UX | Thumbnail grid, infinite scroll, improved layout |
| Admin Dashboard | Cross-agency visibility, user management |
| WebSocket / SSE | Replace polling with real-time status updates |
| Batch Upload | Multi-file upload with progress tracking |
| Search & Filtering | Full-text search across image metadata and tags |
| Accessibility | WCAG 2.1 AA audit and remediation |
| Enterprise Audit | Centralized audit logging for all user actions |
| Custom Prompts | Allow agencies to customize AI processing prompts |
| CI/CD Pipeline | GitHub Actions for automated build, test, and deploy |

---

## 10. Support & Contacts

For issues with the deployed solution, refer to the following resources:

| Contact / Resource | Purpose | Details |
|---|---|---|
| Azure Support | Infrastructure and service issues | Raise a support ticket via portal.azure.com |
| Reference Repository | Framework-level bugs or questions | https://github.com/Azure/ai-document-processor/issues |
| Azure OpenAI Documentation | API reference and model capabilities | https://learn.microsoft.com/azure/ai-services/openai/ |
| Azure Functions Documentation | Functions runtime and triggers | https://learn.microsoft.com/azure/azure-functions/ |
| Azure Static Web Apps Documentation | SWA hosting and configuration | https://learn.microsoft.com/azure/static-web-apps/ |
| MSAL Documentation | Authentication library reference | https://learn.microsoft.com/entra/msal/ |

---

## Repository Structure

```
datahub_ui_poc/
├── app/
│   ├── api/                            ← Azure Functions v2 (UI API — production)
│   │   ├── function_app.py             ← Entry point: registers 3 blueprints
│   │   ├── host.json                   ← Functions host configuration
│   │   ├── local.settings.json         ← Local dev settings (DO NOT COMMIT)
│   │   ├── requirements.txt            ← Python dependencies
│   │   ├── upload_initiate/            ← POST /api/upload
│   │   │   ├── __init__.py
│   │   │   └── init.py
│   │   ├── get_status/                 ← GET /api/images, GET|DELETE /api/images/{id}
│   │   │   ├── __init__.py
│   │   │   └── init.py
│   │   ├── get_results/                ← GET /api/images/{id}/tags
│   │   │   ├── __init__.py
│   │   │   └── init.py
│   │   └── shared/                     ← Shared modules
│   │       ├── __init__.py
│   │       ├── auth.py                 ← Entra ID JWT validation (OIDC, RS256)
│   │       ├── sas.py                  ← SAS URL generation (user delegation keys)
│   │       └── storage.py              ← Blob Storage CRUD + metadata lifecycle
│   ├── backend/                        ← Legacy FastAPI (earlier iteration, not used)
│   ├── demo/                           ← Standalone mock server (no Azure required)
│   │   ├── server.py                   ← FastAPI mock API with sample data
│   │   └── requirements.txt
│   └── frontend/                       ← React + Vite SPA
│       ├── package.json
│       ├── tsconfig.json
│       ├── vite.config.ts
│       ├── index.html
│       ├── build/                      ← Production build output
│       │   ├── index.html
│       │   ├── staticwebapp.config.json
│       │   └── assets/
│       ├── public/
│       │   └── staticwebapp.config.json
│       └── src/
│           ├── main.tsx                ← Entry: demo vs production mode switch
│           ├── App.tsx                 ← Production root (MSAL gated)
│           ├── DemoApp.tsx             ← Demo root (no auth)
│           ├── App.css
│           ├── types.ts               ← TypeScript interfaces
│           ├── services/
│           │   ├── api.ts             ← Production API client (MSAL tokens)
│           │   ├── demoApi.ts         ← Demo API client (no auth)
│           │   └── auth.ts            ← MSAL / Entra ID configuration
│           └── components/
│               ├── Upload/
│               │   ├── UploadPage.tsx
│               │   └── DemoUploadPage.tsx
│               ├── ImageGallery/
│               │   ├── ImageGallery.tsx
│               │   └── DemoImageGallery.tsx
│               ├── ImageDetail/
│               │   ├── ImageDetail.tsx
│               │   └── DemoImageDetail.tsx
│               └── Status/
│                   └── StatusBadge.tsx
├── infra/                              ← Infrastructure as Code (Bicep)
│   ├── main.bicep                      ← Orchestrator
│   ├── main.bicepparam                 ← Parameters (edit with your values)
│   ├── README.md                       ← Detailed infra deployment guide
│   └── modules/
│       ├── monitoring.bicep
│       ├── networking.bicep
│       ├── storage.bicep
│       ├── function-app.bicep
│       ├── static-web-app.bicep
│       └── security.bicep
├── docs/                               ← Architecture & security documentation
│   ├── architecture-ui.md
│   ├── security.md
│   └── ui-handover.md
├── scripts/
│   └── run-demo.ps1                    ← Demo launcher (backend + frontend)
├── pyproject.toml                      ← Python ≥ 3.13, uv project
└── README.md                           ← Project README
```

---

**END OF DOCUMENT**
