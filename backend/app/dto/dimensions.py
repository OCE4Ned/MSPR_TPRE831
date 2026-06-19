"""Modeles SQLModel des tables de dimensions (couche gold).

Chaque classe est a la fois :
- un modele de table (table=True) -> structure de la table DIM_* en base ;
- un schema d'API (validation / serialisation des reponses).

Aucune donnee n'est creee ici : on ne fait que decrire la structure.
"""

from datetime import date as date_type

from sqlmodel import Field, SQLModel


class Plant(SQLModel, table=True):
    """DIM_PLANT - usine."""

    __tablename__ = "DIM_PLANT"

    plant_id: str = Field(primary_key=True)
    plant_name: str
    country: str


class Line(SQLModel, table=True):
    """DIM_LINE - ligne de production."""

    __tablename__ = "DIM_LINE"

    production_line_id: str = Field(primary_key=True)
    plant_id: str = Field(index=True)
    line_name: str


class Shift(SQLModel, table=True):
    """DIM_SHIFT - equipe / poste de travail."""

    __tablename__ = "DIM_SHIFT"

    shift_id: str = Field(primary_key=True)
    shift_name: str
    start_hour: str
    end_hour: str


class Product(SQLModel, table=True):
    """DIM_PRODUCT - produit fabrique."""

    __tablename__ = "DIM_PRODUCT"

    product_id: str = Field(primary_key=True)
    product_name: str
    product_family: str


class DateDim(SQLModel, table=True):
    """DIM_DATE - dimension calendaire."""

    __tablename__ = "DIM_DATE"

    date_id: int = Field(primary_key=True)
    date: date_type
    year: int = Field(index=True)
    month: int = Field(index=True)
    day: int
    week: int = Field(index=True)


class Defect(SQLModel, table=True):
    """DIM_DEFECT - typologie de defaut qualite."""

    __tablename__ = "DIM_DEFECT"

    defect_id: str = Field(primary_key=True)
    defect_type: str
    defect_category: str
    defect_severity: str


class Machine(SQLModel, table=True):
    """DIM_MACHINE - machine de production."""

    __tablename__ = "DIM_MACHINE"

    machine_id: str = Field(primary_key=True)
    production_line_id: str = Field(index=True)
    machine_type: str
    installation_year: int
