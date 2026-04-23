// ---------------------------------------------------------------------------
// Module: RBAC Role Assignments for Function App Managed Identity
// ---------------------------------------------------------------------------
// Grants the Function App's system-assigned managed identity the minimum
// roles needed to interact with Azure Blob Storage using Entra ID auth.
// ---------------------------------------------------------------------------

param storageAccountName string
param functionAppPrincipalId string

// ── Role Definition IDs (built-in) ──────────────────────────────────────────

// Storage Blob Data Contributor — read, write, delete blobs and containers
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

// Storage Blob Delegator — generate user-delegation SAS keys
var storageBlobDelegatorRoleId = 'db58b8e5-c6ad-4a2a-8342-4190687cbf4a'

// ── Reference Existing Storage Account ──────────────────────────────────────

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

// ── Storage Blob Data Contributor ───────────────────────────────────────────

resource blobContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, functionAppPrincipalId, storageBlobDataContributorRoleId)
  scope: storageAccount
  properties: {
    principalId: functionAppPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
    principalType: 'ServicePrincipal'
  }
}

// ── Storage Blob Delegator ──────────────────────────────────────────────────

resource blobDelegatorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, functionAppPrincipalId, storageBlobDelegatorRoleId)
  scope: storageAccount
  properties: {
    principalId: functionAppPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDelegatorRoleId)
    principalType: 'ServicePrincipal'
  }
}
