# Wakes Postgres + Redis, waits for them to be ready, then re-runs
# migrations and seeding. Run this before any demo, since Postgres
# data doesn't persist across a scale-to-zero cycle (deliberate
# trade-off to stay on consumption-only pricing).

$rg = "rbac-portfolio-rg"

Write-Host "Scaling Postgres and Redis up..."
az containerapp update --name postgres --resource-group $rg --min-replicas 1
az containerapp update --name redis --resource-group $rg --min-replicas 1

Write-Host "Waiting 45s for both to come online..."
Start-Sleep -Seconds 45

Write-Host "Running migrations..."
az containerapp exec --name rbac-gateway --resource-group $rg --command "alembic upgrade head"

Write-Host "Seeding roles and admin user..."
az containerapp exec --name rbac-gateway --resource-group $rg --command "python app/scripts/seed_roles.py"

$fqdn = az containerapp show --name rbac-gateway --resource-group $rg --query properties.configuration.ingress.fqdn -o tsv
Write-Host "`nReady. Docs: https://$fqdn/docs"