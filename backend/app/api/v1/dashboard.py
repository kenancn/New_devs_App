from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional
from app.services.cache import get_revenue_summary
from app.core.auth import authenticate_request as get_current_user
from app.models.auth import AuthenticatedUser

router = APIRouter()

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    month: Optional[int] = Query(default=None, ge=1, le=12),
    year: Optional[int] = Query(default=None, ge=1, le=9998),
) -> Dict[str, Any]:
    
    tenant_id = current_user.tenant_id
    if not tenant_id or not tenant_id.strip():
        raise HTTPException(status_code=403, detail="Tenant is required")
    if (month is None) != (year is None):
        raise HTTPException(status_code=422, detail="Month and year must be provided together")
    
    revenue_data = await get_revenue_summary(property_id, tenant_id, month=month, year=year)
    
    total_revenue_float = float(revenue_data['total'])
    
    return {
        "property_id": revenue_data['property_id'],
        "total_revenue": total_revenue_float,
        "currency": revenue_data['currency'],
        "reservations_count": revenue_data['count']
    }
