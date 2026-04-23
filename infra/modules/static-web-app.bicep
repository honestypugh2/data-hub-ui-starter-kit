// ---------------------------------------------------------------------------
// Module: Azure Static Web App (React SPA Frontend)
// ---------------------------------------------------------------------------

param location string
param staticWebAppName string
param tags object

@allowed(['Free', 'Standard'])
param sku string = 'Free'

// ── Static Web App ──────────────────────────────────────────────────────────

resource staticWebApp 'Microsoft.Web/staticSites@2024-04-01' = {
  name: staticWebAppName
  location: location
  tags: union(tags, { 'azd-service-name': 'frontend' })
  sku: {
    name: sku
    tier: sku
  }
  properties: {
    stagingEnvironmentPolicy: 'Enabled'
    allowConfigFileUpdates: true
    buildProperties: {
      appLocation: 'app/frontend'
      outputLocation: 'build'
    }
  }
}

// ── Outputs ─────────────────────────────────────────────────────────────────

output staticWebAppName string = staticWebApp.name
output staticWebAppHostname string = staticWebApp.properties.defaultHostname
output staticWebAppId string = staticWebApp.id
