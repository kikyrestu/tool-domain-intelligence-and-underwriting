"""Export routes — CSV + XLSX download."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.export_service import generate_csv, generate_xlsx

router = APIRouter()


@router.get("/export/csv")
async def export_csv(
    status: str = Query(None),
    niche: str = Query(None),
    label: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    csv_content = await generate_csv(db, status_filter=status, niche_filter=niche, label_filter=label)

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=domain-candidates.csv"},
    )


@router.get("/export/xlsx")
async def export_xlsx(
    status: str = Query(None),
    niche: str = Query(None),
    label: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    xlsx_bytes = await generate_xlsx(db, status_filter=status, niche_filter=niche, label_filter=label)

    return StreamingResponse(
        iter([xlsx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=domain-candidates.xlsx"},
    )
