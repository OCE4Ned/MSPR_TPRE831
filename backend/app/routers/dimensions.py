"""Routes des tables de dimensions (referentiels)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.dto.dimensions import (
    DateDim,
    Defect,
    Line,
    Machine,
    Plant,
    Product,
    Shift,
)

router = APIRouter(prefix="/dimensions", tags=["dimensions"])


# --- DIM_PLANT --------------------------------------------------------------

@router.get("/plants", response_model=list[Plant])
def list_plants(session: Session = Depends(get_session)):
    """Liste des usines."""
    return session.exec(select(Plant)).all()


@router.get("/plants/{plant_id}", response_model=Plant)
def get_plant(plant_id: str, session: Session = Depends(get_session)):
    """Detail d'une usine."""
    plant = session.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(status_code=404, detail="Usine introuvable")
    return plant


# --- DIM_LINE ---------------------------------------------------------------

@router.get("/lines", response_model=list[Line])
def list_lines(plant_id: str | None = None, session: Session = Depends(get_session)):
    """Liste des lignes de production, filtrable par usine."""
    query = select(Line)
    if plant_id is not None:
        query = query.where(Line.plant_id == plant_id)
    return session.exec(query).all()


@router.get("/lines/{production_line_id}", response_model=Line)
def get_line(production_line_id: str, session: Session = Depends(get_session)):
    """Detail d'une ligne de production."""
    line = session.get(Line, production_line_id)
    if line is None:
        raise HTTPException(status_code=404, detail="Ligne introuvable")
    return line


# --- DIM_MACHINE ------------------------------------------------------------

@router.get("/machines", response_model=list[Machine])
def list_machines(
    production_line_id: str | None = None,
    session: Session = Depends(get_session),
):
    """Liste des machines, filtrable par ligne."""
    query = select(Machine)
    if production_line_id is not None:
        query = query.where(Machine.production_line_id == production_line_id)
    return session.exec(query).all()


@router.get("/machines/{machine_id}", response_model=Machine)
def get_machine(machine_id: str, session: Session = Depends(get_session)):
    """Detail d'une machine."""
    machine = session.get(Machine, machine_id)
    if machine is None:
        raise HTTPException(status_code=404, detail="Machine introuvable")
    return machine


# --- DIM_PRODUCT ------------------------------------------------------------

@router.get("/products", response_model=list[Product])
def list_products(session: Session = Depends(get_session)):
    """Liste des produits."""
    return session.exec(select(Product)).all()


@router.get("/products/{product_id}", response_model=Product)
def get_product(product_id: str, session: Session = Depends(get_session)):
    """Detail d'un produit."""
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return product


# --- DIM_SHIFT --------------------------------------------------------------

@router.get("/shifts", response_model=list[Shift])
def list_shifts(session: Session = Depends(get_session)):
    """Liste des equipes / postes."""
    return session.exec(select(Shift)).all()


@router.get("/shifts/{shift_id}", response_model=Shift)
def get_shift(shift_id: str, session: Session = Depends(get_session)):
    """Detail d'une equipe / poste."""
    shift = session.get(Shift, shift_id)
    if shift is None:
        raise HTTPException(status_code=404, detail="Equipe introuvable")
    return shift


# --- DIM_DEFECT -------------------------------------------------------------

@router.get("/defects", response_model=list[Defect])
def list_defects(session: Session = Depends(get_session)):
    """Liste des typologies de defauts."""
    return session.exec(select(Defect)).all()


@router.get("/defects/{defect_id}", response_model=Defect)
def get_defect(defect_id: str, session: Session = Depends(get_session)):
    """Detail d'une typologie de defaut."""
    defect = session.get(Defect, defect_id)
    if defect is None:
        raise HTTPException(status_code=404, detail="Defaut introuvable")
    return defect


# --- DIM_DATE ---------------------------------------------------------------

@router.get("/dates", response_model=list[DateDim])
def list_dates(
    year: int | None = None,
    month: int | None = None,
    session: Session = Depends(get_session),
):
    """Liste des dates du referentiel calendaire."""
    query = select(DateDim)
    if year is not None:
        query = query.where(DateDim.year == year)
    if month is not None:
        query = query.where(DateDim.month == month)
    return session.exec(query).all()


@router.get("/dates/{date_id}", response_model=DateDim)
def get_date(date_id: int, session: Session = Depends(get_session)):
    """Detail d'une date du referentiel."""
    date_row = session.get(DateDim, date_id)
    if date_row is None:
        raise HTTPException(status_code=404, detail="Date introuvable")
    return date_row
