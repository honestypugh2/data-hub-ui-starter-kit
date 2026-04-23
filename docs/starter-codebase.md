# Starter Kit UI — Starter Codebase & Deployment Overview

## ⚠️ Important: Blueprint Status

**This starter codebase has NOT been tested in your environment.** It serves as a **functional blueprint** for the starter kit application and requires modification and thorough testing before deployment in a production environment.

### Key Limitations

- **No Target Environment Testing**: This codebase has been developed without access to your actual Azure tenant, Entra ID configuration, network topology, or data environment.
- **Configuration Variability**: All deployment examples assume placeholder values (resource names, region, SKU, network settings) that must be adapted to your environment.
- **Environmental Dependencies**: The application requires specific Azure resources, Entra ID app registrations, and network permissions that may differ from your setup.
- **Testing Responsibility**: You must validate all components, API endpoints, authentication flows, and data pipelines in your environment before production use.

---

## Quick Start: What's Included

This starter codebase includes:

| Component | Location | Purpose |
|-----------|----------|---------|
| **Frontend (React SPA)** | `app/frontend/` | Vite + React 19 + TypeScript SPA with MSAL authentication |
| **Azure Functions API** | `app/api/` | Python v2 Functions with Blueprints model for image upload, listing, and deletion |
| **Legacy Backend** | `app/backend/` | FastAPI implementation (reference; production uses Azure Functions) |
| **Demo Server** | `app/demo/` | Standalone mock server for local development without Azure |
| **Infrastructure (Bicep)** | `infra/` | Complete IaC templates for storage, functions, static web app, monitoring |
| **Documentation** | `docs/` | Architecture, security, handover, and operational guides |

---

## Core Architecture

```
┌──────────────────────────────────────┐
│  React SPA (Vite)                    │
│  - MSAL Authentication               │
│  - Image Upload & Gallery            │
│  - Status Polling & Detail View      │
└────────────────┬─────────────────────┘
                 │ JSON + JWT
    ┌────────────▼─────────────┐
    │  Azure Functions v2      │
    │  (Python Blueprints)     │
    │  - POST /api/upload      │
    │  - GET /api/images       │
    │  - DELETE /api/images    │
    └────────────┬─────────────┘
                 │ SAS URL
    ┌────────────▼──────────────────────┐
    │  Azure Blob Storage                │
    │  - bronze/ (uploads)               │
    │  - gold/ (AI outputs)              │
    │  - ui-metadata/ (tracking)         │
    └────────────┬──────────────────────┘
                 │ Blob Trigger
    ┌────────────▼──────────────────────────┐
    │  Azure Durable Functions (Existing)   │
    │  + Azure OpenAI (AI Image Tagging)   │
    └───────────────────────────────────────┘
```

### Key Technologies

- **Frontend**: React 19, TypeScript, Vite, MSAL (v5), Tailwind CSS
- **API**: Azure Functions v2, Python 3.13, Blueprints
- **Storage**: Azure Blob Storage (containers: bronze, gold, ui-metadata)
- **Authentication**: Microsoft Entra ID (JWT validation, RS256)
- **AI Processing**: Azure OpenAI (image tagging via existing pipeline)
- **Monitoring**: Azure Log Analytics, Application Insights
- **Infrastructure**: Bicep with modular design (optional private endpoints)

---

## Deployment Overview

### Prerequisites

Before deploying, you must have:

1. **Azure Subscription** with appropriate permissions
2. **Entra ID Tenant** with:
   - App registration for the backend API (service principal)
   - App registration for the frontend SPA
   - Agency group structure for user claims
3. **Azure CLI** and **Bicep CLI** installed locally
4. **Node.js** 20+ (for frontend build)
5. **Python** 3.13+ (for local testing)
6. **Appropriate Azure resource quotas** (storage, functions, static web app, app insights)

### High-Level Deployment Steps

#### 1. **Infrastructure Deployment (Bicep)**

```powershell
cd infra/

# Update main.bicepparam with your values:
# - location: your preferred Azure region
# - environmentName: dev, staging, or prod
# - tenantId: your Entra ID tenant ID
# - apiClientId: your backend API app registration client ID
# - enableNetworkIsolation: true/false for private endpoints

# Deploy infrastructure
az deployment group create \
  --resource-group <your-rg> \
  --template-file main.bicep \
  --parameters main.bicepparam
```

**Output**: Deployed Azure resources including Storage, Function App, Static Web App, App Insights.

#### 2. **API Configuration (Azure Functions)**

```powershell
cd app/api/

# Install dependencies
pip install -r requirements.txt

# Update local.settings.json with:
# - Storage account connection string
# - Entra ID tenant ID
# - Entra ID API client ID
# - OpenAI endpoint (if processing pipeline enabled)

# Test locally
func start
```

**Testing**: POST to `http://localhost:7071/api/upload` with a Bearer token to verify JWT validation.

#### 3. **Frontend Build & Deployment**

```powershell
cd app/frontend/

# Install dependencies
npm install

# Build for production
npm run build

# Output: dist/ folder containing optimized React SPA

# Deploy to Azure Static Web App
az staticwebapp deployment upload-files \
  --resource-group <your-rg> \
  --name <your-static-web-app-name> \
  --deployment-id <deployment-id> \
  --source-dir dist
```

**Configuration**: The frontend expects these environment variables:
- `VITE_API_URL`: Base URL of your Azure Functions API
- `VITE_TENANT_ID`: Your Entra ID tenant ID
- `VITE_CLIENT_ID`: Your frontend SPA app registration client ID
- `VITE_DEMO_MODE`: `true` for demo, `false` for production

#### 4. **Post-Deployment Validation**

After deployment, validate:

- [ ] Static Web App is accessible at your configured domain
- [ ] Frontend loads and displays login prompt
- [ ] Entra ID authentication completes successfully
- [ ] POST `/api/upload` returns a SAS URL
- [ ] SAS URL can be used to upload a test image to blob storage
- [ ] Metadata record is created in `ui-metadata` container
- [ ] AI processing pipeline triggers (if connected)
- [ ] Gallery auto-refreshes and displays uploaded image
- [ ] Image detail view shows tags (once processing completes)

---

## Project Structure Details

### Frontend (`app/frontend/`)

- **src/main.tsx**: Entry point; switches between demo and production modes
- **src/App.tsx**: Production root component (MSAL authentication)
- **src/DemoApp.tsx**: Demo root component (no Azure dependencies)
- **src/components/**: Reusable React components (Upload, Gallery, ImageDetail, Status)
- **src/services/**: API client (auth, demo, and production API calls)
- **vite.config.ts**: Vite bundler configuration
- **public/staticwebapp.config.json**: Azure Static Web App routing configuration

### API (`app/api/`)

- **function_app.py**: Flask app entry; registers Blueprints
- **upload_initiate/init.py**: `POST /api/upload` — initiates upload, returns SAS URL
- **get_status/init.py**: `GET /api/images` and `GET /DELETE /api/images/{id}`
- **get_results/init.py**: `GET /api/images/{id}/tags` — retrieves AI tags
- **shared/auth.py**: Entra ID JWT validation (RS256, OIDC key fetch)
- **shared/sas.py**: SAS URL generation for blob containers
- **shared/storage.py**: Blob storage CRUD operations and metadata tracking

### Infrastructure (`infra/`)

- **main.bicep**: Root template; orchestrates module deployments
- **main.bicepparam**: Parameter file (customize for your environment)
- **modules/monitoring.bicep**: Log Analytics + App Insights
- **modules/networking.bicep**: VNet, private endpoints, private DNS (optional)
- **modules/storage.bicep**: Storage Account with blob containers
- **modules/function-app.bicep**: Function App, App Service Plan, app settings
- **modules/static-web-app.bicep**: Static Web App resource
- **modules/security.bicep**: RBAC role assignments

---

## Configuration & Customization

### Frontend Configuration

Edit `app/frontend/.env` (or `.env.production` for production builds):

```env
VITE_API_URL=https://your-function-app.azurewebsites.net/api
VITE_TENANT_ID=your-tenant-id
VITE_CLIENT_ID=your-spa-app-client-id
VITE_DEMO_MODE=false
```

### API Configuration

Edit `app/api/local.settings.json` (local development) or update Function App settings in Azure Portal:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "DefaultEndpointsProtocol=https;AccountName=...",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "TENANT_ID": "your-tenant-id",
    "API_CLIENT_ID": "your-backend-api-app-client-id",
    "STORAGE_ACCOUNT_NAME": "your-storage-account",
    "STORAGE_ACCOUNT_KEY": "your-storage-key"
  }
}
```

### Infrastructure Customization

Edit `infra/main.bicepparam`:

```bicep
param location = 'eastus'
param environmentName = 'dev'
param tenantId = 'your-tenant-id'
param apiClientId = 'your-api-client-id'
param enableNetworkIsolation = false  // Set to true for private endpoints
param staticWebAppSku = 'Free'         // Use 'Standard' for prod
```

---

## Local Development & Testing

### Demo Mode (No Azure Required)

```powershell
# Run the demo server
cd app/demo/
pip install -r requirements.txt
python server.py

# In another terminal, start the frontend
cd app/frontend/
npm install
npm run dev
```

Visit `http://localhost:3000` — the app will use mock data without Azure dependencies.

### Full Local Development (With Azure Emulator)

```powershell
# Install Azure Storage Emulator or use Azurite
# https://github.com/Azure/Azurite

# Start Azure Functions locally
cd app/api/
func start

# In another terminal, start the frontend
cd app/frontend/
npm run dev
```

---

## Common Modifications Needed in Your Environment

Based on typical enterprise deployments, you will likely need to modify:

### 1. **Entra ID Integration**

- Update tenant ID and app registration IDs to match your environment
- Configure agency group claims extraction (currently assumes specific claim structure)
- Customize login scopes and permissions

### 2. **Blob Storage**

- Adjust container names (bronze, gold, ui-metadata) to match your data lake structure
- Configure data lifecycle policies and access tiers
- Update SAS token permissions and expiration windows

### 3. **Function App Runtime**

- Update Python version if your environment requires 3.11 or 3.12
- Adjust timeout settings for long-running AI processing
- Configure CORS policies to match your frontend domain

### 4. **Networking**

- Enable private endpoints if your environment requires Zero-Trust Architecture
- Update NSG rules and firewall settings
- Configure DNS resolution for private endpoints

### 5. **AI Processing Pipeline**

- Update Azure OpenAI model names and deployment IDs
- Customize image tagging prompts and processing logic
- Adjust processing trigger conditions (e.g., file size limits, format restrictions)

### 6. **Monitoring & Logging**

- Customize Application Insights sampling rates and retention
- Update alert thresholds and notification rules
- Configure custom metrics for your specific KPIs

### 7. **Frontend Customization**

- Rebrand UI components (colors, logos, agency-specific branding)
- Adjust upload file size limits and supported formats
- Customize error messages and validation rules
- Add additional metadata fields for your data model

---

## Testing Checklist

Before deploying to production, validate the following:

### Infrastructure Tests
- [ ] All resources deployed successfully in Azure Portal
- [ ] Storage account contains `bronze`, `gold`, `ui-metadata` containers
- [ ] Function App configured with correct environment variables
- [ ] Static Web App deployment successful
- [ ] Log Analytics and App Insights receiving telemetry

### Authentication Tests
- [ ] Entra ID login flow completes successfully
- [ ] JWT token is correctly decoded and validated
- [ ] User agency is correctly extracted from claims
- [ ] Unauthorized requests are rejected

### API Tests
- [ ] POST `/api/upload` returns 200 with SAS URL
- [ ] SAS URL can be used to upload file via PUT to blob storage
- [ ] GET `/api/images` returns list of user's images
- [ ] GET `/api/images/{id}` returns image detail with metadata
- [ ] DELETE `/api/images/{id}` removes image and metadata
- [ ] Concurrent uploads are handled correctly

### Frontend Tests
- [ ] Pages load without JavaScript errors
- [ ] Image upload triggers and completes
- [ ] Gallery updates with new images (auto-polling)
- [ ] Status badge displays correctly (pending → completed)
- [ ] Image detail view loads preview
- [ ] AI tags display once available
- [ ] Responsive design works on mobile/tablet

### AI Processing Tests
- [ ] Images uploaded to `bronze/` trigger processing
- [ ] Output JSON written to `gold/{name}-output.json`
- [ ] Metadata updated with status = `completed`
- [ ] Frontend retrieves tags successfully

### Performance & Load Tests
- [ ] Frontend bundle size optimized (< 500 KB)
- [ ] API response times acceptable (< 1 second)
- [ ] SAS URL generation performant
- [ ] Concurrent users can upload simultaneously
- [ ] Database/metadata queries are efficient

---

## Troubleshooting Guide

### Frontend Issues

**Problem**: "Cannot find module '@azure/msal-react'"
- **Solution**: Ensure `npm install` completed successfully; check `app/frontend/package.json`

**Problem**: "CORS error when calling API"
- **Solution**: Verify Function App CORS settings allow your Static Web App domain

**Problem**: "Login redirects but user not authenticated"
- **Solution**: Check Entra ID app registration has correct redirect URI matching your Static Web App domain

### API Issues

**Problem**: "JWT validation failed: invalid token"
- **Solution**: Verify tenant ID and API client ID match your Entra ID configuration

**Problem**: "SAS URL returns 403 Forbidden when uploading"
- **Solution**: Check storage account connection string and SAS token permissions

**Problem**: "Function App timeout on large file upload"
- **Solution**: Increase Function App timeout in host.json; consider chunked upload

### Storage Issues

**Problem**: "Images not appearing in gallery"
- **Solution**: Check blob containers exist (bronze, gold, ui-metadata); verify permissions

**Problem**: "Processing pipeline not triggering"
- **Solution**: Verify blob trigger function is enabled; check durable functions connection

---

## Monitoring — Key Functions

When debugging in the Azure Portal, monitor these functions via **Log stream** on each Function App:

**UI API Function App:**

| Function Name | Role | Trigger Type |
|---|---|---|
| `upload_initiate` | Validate upload request, generate write SAS URL, create metadata | HTTP (`POST /api/upload`) |
| `list_images` | List all images for the caller's agency | HTTP (`GET /api/images`) |
| `get_image_detail` | Get image detail with preview URL and tags | HTTP (`GET /api/images/{id}`) |
| `delete_image` | Delete image, output, and metadata | HTTP (`DELETE /api/images/{id}`) |
| `get_image_tags` | Return AI-generated tags (JSON) | HTTP (`GET /api/images/{id}/tags`) |

**Existing Processing Pipeline (`<your-processing-function-app>`):**

| Function Name | Role | Trigger Type |
|---|---|---|
| `start_orchestrator_on_blob` | Entry point — initiates Durable Functions orchestration when blob uploaded | Blob Trigger |
| `process_blob` | Routes the file to the appropriate processing function | Orchestrator Activity |
| `callAoaiMultiModal` | Calls Azure OpenAI for image processing with prompt | Orchestrator Activity |
| `writeToBlob` | Writes JSON output to the `gold` container | Orchestrator Activity |

---

## Out of Scope (Phase 1)

The following were intentionally excluded from Phase 1 and are candidates for future work:

- Gallery UX improvements (thumbnail grid, infinite scroll)
- Admin dashboard with cross-agency visibility
- Full-text search or advanced filtering
- Batch/multi-image upload
- WebSocket or push notifications (polling only)
- Enterprise audit logging
- Accessibility hardening (WCAG 2.1 AA)
- Centralized workflow management
- Custom AI processing prompts per agency

---

## Support & Next Steps

### Documentation References
- **Getting Started**: See [getting-started.md](getting-started.md)
- **Architecture Details**: See [architecture-ui.md](architecture-ui.md)
- **Security Considerations**: See [security.md](security.md)
- **Infrastructure Deployment**: See [infra/README.md](../infra/README.md)

### Recommended Next Steps

1. **Review & Customize**: Adapt configurations for your specific environment
2. **Set Up Dev Environment**: Deploy to dev resource group first
3. **Comprehensive Testing**: Follow the testing checklist above
4. **Security Review**: Engage security team for zero-trust and compliance validation
5. **User Testing**: Conduct UAT with actual end-users from your agencies
6. **Production Deployment**: After validation, promote to staging/prod

### Support Resources

- Azure Functions Documentation: https://learn.microsoft.com/en-us/azure/azure-functions/
- Static Web App Documentation: https://learn.microsoft.com/en-us/azure/static-web-apps/
- MSAL React Documentation: https://github.com/AzureAD/microsoft-authentication-library-for-js
- Bicep Documentation: https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/

---

**Version**: 1.0  
**Last Updated**: April 22, 2026  
**Status**: Starter Codebase — Blueprint for Customization
