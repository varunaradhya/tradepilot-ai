from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get("/")
def get_users(db: Session = Depends(get_db)):
    return {"message": "User endpoint is working"}
