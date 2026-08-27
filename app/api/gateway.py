import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from app.core.config import settings
from app.api.deps import get_current_user
from app.services.rate_limiter import rate_limit
from app.models.user import User

router = APIRouter(prefix="/gateway/inventory", tags=["gateway"])

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def inventory_gateway(
    path: str,
    request: Request,
    # 1. Run get_current_user and the 'standard' rate limit tier
    current_user: User = Depends(get_current_user),
    limit: None = Depends(rate_limit("standard"))
):
    """
    Reverse-proxies requests to the downstream Inventory API.
    Dynamically maps HTTP methods to RBAC permissions.
    """
    # 2. Map HTTP method -> required permission
    required_perm = "inventory:write" if request.method in ["POST", "PUT", "PATCH", "DELETE"] else "inventory:read"
    
    # Verify the user has the required permission
    user_perms = {perm.name for role in current_user.roles for perm in role.permissions}
    if required_perm not in user_perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=f"Missing required permission: {required_perm}"
        )

    # 3. Construct the downstream URL
    url = f"{settings.INVENTORY_API_BASE_URL}/{path}"
    
    # Extract body if present
    body = await request.body()
    
    # 4. Forward headers and inject X-Authenticated-User-Id
    headers = dict(request.headers)
    headers.pop("host", None)  # Remove original host header to prevent routing issues
    headers["X-Authenticated-User-Id"] = str(current_user.id)
    
    # 5. Use httpx to forward the exact request
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=request.method,
                url=url,
                content=body,
                headers=headers,
                params=request.query_params
            )
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
                detail="Inventory microservice is currently unavailable"
            )
            
    # 6. Return downstream response as-is
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers)
    )