$rg = "rbac-portfolio-rg"
Write-Host "Putting Postgres and Redis to sleep (Scale to 0)..."
az containerapp update --name postgres --resource-group $rg --min-replicas 0
az containerapp update --name redis --resource-group $rg --min-replicas 0
Write-Host "Done. Cloud cost is now 0/hr." 