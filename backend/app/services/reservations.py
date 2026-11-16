from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
import logging

from fastapi import HTTPException
from sqlalchemy import text

from app.core.database_pool import db_pool

logger = logging.getLogger(__name__)


async def calculate_total_revenue(
    property_id: str,
    tenant_id: str,
    month: Optional[int] = None,
    year: Optional[int] = None,
) -> Dict[str, Any]:
    """Aggregate revenue for a property and optional local calendar month."""
    params = {"property_id": property_id, "tenant_id": tenant_id}
    date_filter = ""
    if month is not None:
        params["start_date"] = datetime(year, month, 1)
        params["end_date"] = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
        # Convert local month boundaries using the property's timezone.
        date_filter = """
            AND r.check_in_date >= (CAST(:start_date AS timestamp) AT TIME ZONE p.timezone)
            AND r.check_in_date < (CAST(:end_date AS timestamp) AT TIME ZONE p.timezone)
        """

    try:
        async with db_pool.get_session() as session:
            query = text(f"""
                SELECT p.id AS property_id, r.currency,
                    SUM(r.total_amount) AS total_revenue,
                    COUNT(r.id) AS reservation_count
                FROM properties p
                LEFT JOIN reservations r
                    ON r.property_id = p.id AND r.tenant_id = p.tenant_id
                    {date_filter}
                WHERE p.id = :property_id AND p.tenant_id = :tenant_id
                GROUP BY p.id, r.currency
            """)
            result = await session.execute(query, params)
            rows = result.fetchall()

        if not rows:
            raise HTTPException(status_code=404, detail="Property not found")
        if len(rows) != 1 or (rows[0].reservation_count and not (rows[0].currency or "").strip()):
            raise HTTPException(status_code=422, detail="Revenue requires a single currency")

        row = rows[0]
        total_revenue = row.total_revenue if row.total_revenue is not None else Decimal('0.000')
        return {
            "property_id": property_id,
            "tenant_id": tenant_id,
            "total": str(total_revenue),
            "currency": row.currency or "USD",
            "count": row.reservation_count,
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Revenue query failed for %s (tenant: %s)", property_id, tenant_id)
        raise HTTPException(status_code=503, detail="Revenue data is unavailable")
