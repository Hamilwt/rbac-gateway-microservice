import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import require_permissions
from app.core.config import settings

router = APIRouter(prefix="/inventory", tags=["gateway-proxy"])


@router.get("")
async def get_inventory(
    # The guard: Only passes if the token has this permission
    token_payload: dict = Depends(require_permissions(["inventory:read"])),
):
    """
    Proxy GET requests to the Inventory Microservice.
    """
    # We use async context managers so we don't block the server while waiting
    async with httpx.AsyncClient() as client:
        try:
            # We forward traffic to the URL defined in your .env file
            response = await client.get(f"{settings.INVENTORY_API_BASE_URL}/products/")

            # If the downstream service returns an error, we pass it along
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code, detail="Inventory service error"
                )

            return response.json()

        except httpx.RequestError:
            # This is critical for microservices: Handle the case where the other API is completely down
            raise HTTPException(
                status_code=503,
                detail="Inventory microservice is currently unavailable",
            )


@router.post("")
async def create_inventory_item(
    item_data: dict,
    token_payload: dict = Depends(require_permissions(["inventory:write"])),
):
    """
    Proxy POST requests to the Inventory Microservice.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.INVENTORY_API_BASE_URL}/products/", json=item_data
            )
            return response.json()
        except httpx.RequestError:
            raise HTTPException(
                status_code=503,
                detail="Inventory microservice is currently unavailable",
            )
