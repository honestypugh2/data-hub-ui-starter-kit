// ---------------------------------------------------------------------------
// Starter Kit UI — Phase 1 Infrastructure (Bicep)
// ---------------------------------------------------------------------------
// Deploys: Storage Account, Function App (UI API), Static Web App,
//          Log Analytics + App Insights, optional VNet + private endpoints,
//          and RBAC role assignments.
// ---------------------------------------------------------------------------

targetScope = 'resourceGroup'

// ── Parameters ──────────────────────────────────────────────────────────────

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Short environment label (dev, staging, prod).')
@allowed(['dev', 'staging', 'prod'])
param environmentName string = 'dev'

@description('Unique suffix appended to resource names to avoid global conflicts.')
param uniqueSuffix string = uniqueString(resourceGroup().id)

@description('Entra ID tenant ID for JWT validation.')
param tenantId string

@description('Entra ID client ID for the backend API app registration.')
param apiClientId string

@description('Deploy VNet, private endpoints, and private DNS zones for zero-trust networking.')
param enableNetworkIsolation bool = false

@description('Static Web App SKU. Use "Free" for dev/staging, "Standard" for prod.')
@allowed(['Free', 'Standard'])
param staticWebAppSku string = 'Free'

@description('Function App Python version.')
param pythonVersion string = '3.13'

@description('Tags applied to all resources.')
param tags object = {
  project: 'datahub-ui'
  phase: '1'
  environment: environmentName
}

// ── Naming Convention ───────────────────────────────────────────────────────

var baseName = 'datahub'
var storageAccountName = toLower('st${baseName}${uniqueSuffix}')
var functionAppName = 'func-${baseName}-ui-${uniqueSuffix}'
var appServicePlanName = 'asp-${baseName}-ui-${uniqueSuffix}'
var staticWebAppName = 'swa-${baseName}-${uniqueSuffix}'
var logAnalyticsName = 'log-${baseName}-${uniqueSuffix}'
var appInsightsName = 'appi-${baseName}-${uniqueSuffix}'
var vnetName = 'vnet-${baseName}-${uniqueSuffix}'

// ── Modules ─────────────────────────────────────────────────────────────────

// 1. Monitoring (deployed first — other modules reference the workspace)
module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    logAnalyticsName: logAnalyticsName
    appInsightsName: appInsightsName
    tags: tags
  }
}

// 2. Networking (optional — VNet, subnets, private DNS zones)
module networking 'modules/networking.bicep' = if (enableNetworkIsolation) {
  name: 'networking'
  params: {
    location: location
    vnetName: vnetName
    tags: tags
  }
}

// 3. Storage Account + blob containers
module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    location: location
    storageAccountName: storageAccountName
    enablePrivateEndpoint: enableNetworkIsolation
    privateEndpointSubnetId: enableNetworkIsolation ? networking!.outputs.privateEndpointSubnetId : ''
    privateDnsZoneId: enableNetworkIsolation ? networking!.outputs.blobPrivateDnsZoneId : ''
    tags: tags
  }
}

// 4. Function App (UI API)
module functionApp 'modules/function-app.bicep' = {
  name: 'functionApp'
  params: {
    location: location
    functionAppName: functionAppName
    appServicePlanName: appServicePlanName
    storageAccountName: storage.outputs.storageAccountName
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    appInsightsInstrumentationKey: monitoring.outputs.appInsightsInstrumentationKey
    tenantId: tenantId
    apiClientId: apiClientId
    pythonVersion: pythonVersion
    enableVnetIntegration: enableNetworkIsolation
    vnetIntegrationSubnetId: enableNetworkIsolation ? networking!.outputs.functionAppSubnetId : ''
    tags: tags
  }
}

// 5. Static Web App (React SPA)
module staticWebApp 'modules/static-web-app.bicep' = {
  name: 'staticWebApp'
  params: {
    location: location
    staticWebAppName: staticWebAppName
    sku: staticWebAppSku
    tags: tags
  }
}

// 6. RBAC — grant the Function App managed identity access to Storage
module security 'modules/security.bicep' = {
  name: 'security'
  params: {
    storageAccountName: storage.outputs.storageAccountName
    functionAppPrincipalId: functionApp.outputs.functionAppPrincipalId
  }
}

// ── Outputs ─────────────────────────────────────────────────────────────────

@description('Storage account name.')
output storageAccountName string = storage.outputs.storageAccountName

@description('Storage account blob endpoint.')
output storageAccountBlobEndpoint string = storage.outputs.storageAccountBlobEndpoint

@description('Function App name.')
output functionAppName string = functionApp.outputs.functionAppName

@description('Function App default hostname.')
output functionAppHostname string = functionApp.outputs.functionAppHostname

@description('Static Web App name.')
output staticWebAppName string = staticWebApp.outputs.staticWebAppName

@description('Static Web App default hostname.')
output staticWebAppHostname string = staticWebApp.outputs.staticWebAppHostname

@description('Application Insights name.')
output appInsightsName string = monitoring.outputs.appInsightsName

@description('Log Analytics workspace ID.')
output logAnalyticsWorkspaceId string = monitoring.outputs.logAnalyticsWorkspaceId
