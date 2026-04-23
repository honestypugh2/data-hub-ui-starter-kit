# Infrastructure Deployment Guide — Data Hub UI (Phase 1)

This directory contains [Azure Bicep](https://learn.microsoft.com/azure/azure-resource-manager/bicep/) templates that provision all Azure resources required for the Data Hub UI Phase 1 deployment.

---

## What Gets Deployed

| Resource | Bicep Module | Purpose |
|---|---|---|
| **Storage Account** | `modules/storage.bicep` | Blob containers: `bronze`, `gold`, `ui-metadata`, `prompts`, `images`, `silver` |
| **Function App** (Linux, Python) | `modules/function-app.bicep` | UI API endpoints (`/api/upload`, `/api/images`, `/api/images/{id}/tags`) |
| **App Service Plan** | `modules/function-app.bicep` | Consumption (Y1) or Flex Consumption (FC1 when VNet enabled) |
| **Static Web App** | `modules/static-web-app.bicep` | Hosts the React SPA frontend |
| **Log Analytics Workspace** | `modules/monitoring.bicep` | Centralized log collection |
| **Application Insights** | `modules/monitoring.bicep` | APM telemetry for the Function App |
| **RBAC Assignments** | `modules/security.bicep` | Storage Blob Data Contributor + Blob Delegator for Function App MI |
| **VNet + Private Endpoints** *(optional)* | `modules/networking.bicep` | Zero-trust networking with private DNS zones |

### Architecture Diagram

```
┌──────────────────────┐
│  Static Web App      │  ← React SPA (MSAL auth)
│  (swa-datahub-xxx)   │
└──────────┬───────────┘
           │ HTTPS + JWT
┌──────────▼───────────┐
│  Function App        │  ← UI API (Python v2)
│  (func-datahub-xxx)  │
│  System MI enabled   │
└──────────┬───────────┘
           │ Managed Identity (RBAC)
┌──────────▼───────────┐
│  Storage Account     │  ← bronze / gold / ui-metadata
│  (stdatahubxxx)      │
│  No public access    │
│  No shared keys      │
└──────────────────────┘
           │
┌──────────▼───────────┐
│  Log Analytics +     │
│  Application Insights│
└──────────────────────┘
```

---

## Prerequisites

| Requirement | Details |
|---|---|
| **Azure CLI** | v2.60+ — [Install](https://learn.microsoft.com/cli/azure/install-azure-cli) |
| **Bicep CLI** | Bundled with Azure CLI 2.60+. Verify: `az bicep version` |
| **Azure Subscription** | With Contributor + User Access Administrator roles |
| **Resource Group** | Created ahead of time (or use `az group create`) |
| **Entra ID App Registrations** | Two app registrations (see below) |

### Entra ID App Registrations (Manual — Not Automated by Bicep)

You need **two** app registrations in Microsoft Entra ID:

#### 1. Backend API Registration

| Setting | Value |
|---|---|
| Name | `DataHub UI API` (or your choice) |
| Supported account types | Single tenant |
| Expose an API → Application ID URI | `api://<client-id>` |
| Expose an API → Add scope | `access_as_user` |
| App roles | None required for Phase 1 |

Record the **Application (client) ID** — this is the `apiClientId` parameter.

#### 2. Frontend SPA Registration

| Setting | Value |
|---|---|
| Name | `DataHub UI SPA` (or your choice) |
| Supported account types | Single tenant |
| Platform | Single-page application |
| Redirect URIs | `https://<your-swa-hostname>` (add after deploy) |
| API permissions | Add `api://<backend-client-id>/access_as_user` |

Record the **Application (client) ID** — used in the frontend `.env` as `VITE_AZURE_CLIENT_ID`.

> **Tip:** If your organization enforces MFA via Conditional Access, no additional configuration is needed — it applies automatically to both registrations.

---

## Deployment Steps

### Step 1: Log in to Azure

```powershell
az login
az account set --subscription "<YOUR_SUBSCRIPTION_ID>"
```

### Step 2: Create the Resource Group (if it doesn't exist)

```powershell
az group create --name rg-datahub-ui --location westus2
```

### Step 3: Configure Parameters

Edit `infra/main.bicepparam` with your values:

```bicep
using 'main.bicep'

param tenantId = '<YOUR_ENTRA_TENANT_ID>'
param apiClientId = '<YOUR_BACKEND_API_CLIENT_ID>'
param environmentName = 'dev'
param enableNetworkIsolation = false
param staticWebAppSku = 'Free'
```

| Parameter | Required | Description |
|---|---|---|
| `tenantId` | **Yes** | Your Entra ID tenant ID |
| `apiClientId` | **Yes** | Backend API app registration client ID |
| `environmentName` | No | `dev` (default), `staging`, or `prod` |
| `enableNetworkIsolation` | No | `false` (default). Set `true` for VNet + private endpoints |
| `staticWebAppSku` | No | `Free` (default) or `Standard` |
| `location` | No | Defaults to resource group location |
| `uniqueSuffix` | No | Auto-generated. Override to control resource names |

### Step 4: Preview the Deployment (What-If)

```powershell
az deployment group what-if `
  --resource-group rg-datahub-ui `
  --template-file infra/main.bicep `
  --parameters infra/main.bicepparam
```

Review the output to confirm expected resource creation. No changes are made.

### Step 5: Deploy

```powershell
az deployment group create `
  --resource-group rg-datahub-ui `
  --template-file infra/main.bicep `
  --parameters infra/main.bicepparam `
  --name datahub-phase1-$(Get-Date -Format 'yyyyMMdd-HHmmss')
```

Deployment takes approximately 2–5 minutes.

### Step 6: Capture Outputs

```powershell
az deployment group show `
  --resource-group rg-datahub-ui `
  --name <deployment-name> `
  --query properties.outputs
```

Key outputs:

| Output | Use |
|---|---|
| `storageAccountName` | Verify containers exist |
| `functionAppHostname` | Base URL for API (e.g., `https://func-datahub-ui-xxx.azurewebsites.net`) |
| `staticWebAppHostname` | SPA URL (e.g., `https://xxx.azurestaticapps.net`) |

---

## Post-Deployment Configuration

### 1. Deploy the Function App Code

```powershell
cd app/api
func azure functionapp publish <functionAppName>
```

Replace `<functionAppName>` with the output from Step 6.

### 2. Deploy the Static Web App

Option A — **Azure CLI**:

```powershell
cd app/frontend
npm run build

# Get the deployment token
$token = az staticwebapp secrets list `
  --name <staticWebAppName> `
  --query "properties.apiKey" -o tsv

# Deploy
npx @azure/static-web-apps-cli deploy ./build `
  --deployment-token $token
```

Option B — **GitHub Actions** (recommended for CI/CD): Connect the Static Web App to your GitHub repo via the Azure Portal → Static Web App → Deployment → GitHub.

### 3. Update Frontend Environment Variables

After deployment, create `app/frontend/.env.production`:

```env
VITE_API_BASE_URL=https://<functionAppHostname>
VITE_AZURE_CLIENT_ID=<frontend-spa-client-id>
VITE_AZURE_AUTHORITY=https://login.microsoftonline.com/<tenantId>
VITE_AZURE_REDIRECT_URI=https://<staticWebAppHostname>
VITE_API_SCOPE=api://<apiClientId>/access_as_user
```

Rebuild and redeploy the frontend after updating.

### 4. Update Entra ID Redirect URIs

In the Azure Portal, update the **SPA app registration**:
- Authentication → Redirect URIs → Add `https://<staticWebAppHostname>`

### 5. Configure Function App CORS (if needed)

The Bicep template configures CORS for `*.azurestaticapps.net`. If you need additional origins:

```powershell
az functionapp cors add `
  --resource-group rg-datahub-ui `
  --name <functionAppName> `
  --allowed-origins "https://your-custom-domain.com"
```

---

## Production Hardening (enableNetworkIsolation = true)

For production deployments, set `enableNetworkIsolation = true` in parameters. This enables:

| Feature | Details |
|---|---|
| **VNet** | `10.0.0.0/16` with two subnets |
| **Function App VNet Integration** | Outbound traffic routes through VNet (`snet-functions`) |
| **Storage Private Endpoint** | Blob endpoint accessible only via private IP (`snet-private-endpoints`) |
| **Private DNS Zone** | `privatelink.blob.core.windows.net` resolves to private IP |
| **Storage Firewall** | Default action = Deny (only VNet and Azure services allowed) |
| **Flex Consumption Plan** | Replaces Y1 Consumption (required for VNet integration) |

> **Note:** When network isolation is enabled, you cannot access the storage account from your local machine. Use Azure Bastion or a jump box VM within the VNet for troubleshooting.

---

## Security Controls (Applied by Default)

These security settings are enforced regardless of the `enableNetworkIsolation` parameter:

| Control | Implementation |
|---|---|
| **No public blob access** | `allowBlobPublicAccess: false` |
| **No shared key access** | `allowSharedKeyAccess: false` — forces Entra ID auth |
| **HTTPS only** | `supportsHttpsTrafficOnly: true` (storage), `httpsOnly: true` (Function App) |
| **TLS 1.2 minimum** | Both storage and Function App |
| **FTPS disabled** | `ftpsState: 'Disabled'` |
| **Managed Identity** | System-assigned MI on Function App — no secrets in config |
| **RBAC** | Blob Data Contributor + Blob Delegator (minimum required roles) |
| **Soft delete** | 7-day blob soft delete retention |

---

## Module Reference

```
infra/
├── main.bicep                  # Orchestrator — wires all modules together
├── main.bicepparam             # Parameters file (edit this)
├── README.md                   # This file
└── modules/
    ├── monitoring.bicep        # Log Analytics + Application Insights
    ├── networking.bicep        # VNet, subnets, private DNS (optional)
    ├── storage.bicep           # Storage account + 6 containers + private endpoint
    ├── function-app.bicep      # Function App + ASP + managed identity + app settings
    ├── static-web-app.bicep    # Static Web App for React SPA
    └── security.bicep          # RBAC role assignments
```

---

## Troubleshooting

| Issue | Resolution |
|---|---|
| `AllowSharedKeyAccess is false` errors locally | Use `AZURE_STORAGE_CONNECTION_STRING` only for local dev. Deployed Function App uses managed identity via `AzureWebJobsStorage__accountName`. |
| Function App can't access storage (network isolated) | Verify VNet integration is active: Portal → Function App → Networking → VNet Integration. |
| SAS URLs return 403 | Confirm the Function App MI has **Storage Blob Delegator** role (required for user-delegation SAS). |
| Static Web App returns 401 on API routes | This is expected — `staticwebapp.config.json` requires authenticated users for `/api/*`. Auth is handled by MSAL in the SPA. |
| Deployment fails with quota error | Check regional quota: `az vm list-usage --location <region> -o table`. Try a different region. |

---

## Cost Estimate (Phase 1 Dev)

| Resource | SKU | Estimated Monthly Cost |
|---|---|---|
| Storage Account | Standard LRS | ~$1–5 (low volume) |
| Function App | Consumption (Y1) | Free tier (1M requests/mo) |
| Static Web App | Free | $0 |
| Log Analytics | Per-GB | ~$2–5 (low ingestion) |
| Application Insights | Per-GB | Included with Log Analytics |
| **Total (dev)** | | **~$3–10/month** |

> Production with Flex Consumption + Standard SWA + VNet: ~$30–80/month depending on traffic.

---

## Next Steps

- [ ] Create Entra ID app registrations (backend API + frontend SPA)
- [ ] Run `az deployment group what-if` to preview
- [ ] Deploy infrastructure with `az deployment group create`
- [ ] Publish Function App code (`func azure functionapp publish`)
- [ ] Build and deploy React SPA to Static Web App
- [ ] Update Entra ID redirect URIs with the SWA hostname
- [ ] Verify end-to-end flow: login → upload → poll → view tags
