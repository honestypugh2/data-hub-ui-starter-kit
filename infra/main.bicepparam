// ---------------------------------------------------------------------------
// Parameters file for Starter Kit UI — Phase 1
// ---------------------------------------------------------------------------
// Copy this file to main.bicepparam and fill in your values.
// Usage: az deployment group create -g <rg> -f main.bicep -p main.bicepparam
// ---------------------------------------------------------------------------

using 'main.bicep'

// Required — your Entra ID tenant ID
param tenantId = '<YOUR_TENANT_ID>'

// Required — the backend API app registration client ID
param apiClientId = '<YOUR_API_CLIENT_ID>'

// Environment: dev | staging | prod
param environmentName = 'dev'

// Set to true for production zero-trust networking (VNet + private endpoints)
param enableNetworkIsolation = false

// Static Web App tier: Free (dev) or Standard (prod)
param staticWebAppSku = 'Free'

// Azure region (defaults to resource group location)
// param location = 'westus2'

// Optional: override the unique suffix for resource names
// param uniqueSuffix = '<your-unique-suffix>'
