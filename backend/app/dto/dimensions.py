"""Modeles SQLModel des tables de dimensions (couche gold).

Chaque classe est a la fois :
- un modele de table (table=True) -> structure de la table DIM_* en base ;
- un schema d'API (validation / serialisation des reponses).

Aucune donnee n'est creee ici : on ne fait que decrire la structure.
"""

from datetime import date as date_type

from sqlmodel import Field, SQLModel


class Plant(SQLModel, table=True):
    """gold.dim_plant - usine."""

    __tablename__ = "dim_plant"
    __table_args__ = {"schema": "gold"}

    plant_id: str = Field(primary_key=True)
    plant_name: str
    country: str


class Line(SQLModel, table=True):
    """gold.dim_line - ligne de production."""

    __tablename__ = "dim_line"
    __table_args__ = {"schema": "gold"}

    production_line_id: str = Field(primary_key=True)
    plant_id: str = Field(index=True)
    line_name: str


class Shift(SQLModel, table=True):
    """gold.dim_shift - equipe / poste de travail."""

    __tablename__ = "dim_shift"
    __table_args__ = {"schema": "gold"}

    shift_id: str = Field(primary_key=True)
    shift_name: str
    start_hour: str
    end_hour: str


class Product(SQLModel, table=True):
    """gold.dim_product - produit fabrique."""

    __tablename__ = "dim_product"
    __table_args__ = {"schema": "gold"}

    product_id: str = Field(primary_key=True)
    product_name: str
    product_family: str


class DateDim(SQLModel, table=True):
    """gold.dim_date - dimension calendaire."""

    __tablename__ = "dim_date"
    __table_args__ = {"schema": "gold"}

    date_id: int = Field(primary_key=True)
    date: date_type
    year: int = Field(index=True)
    month: int = Field(index=True)
    day: int
    week: int = Field(index=True)


class Defect(SQLModel, table=True):
    """gold.dim_defect - typologie de defaut qualite."""

    __tablename__ = "dim_defect"
    __table_args__ = {"schema": "gold"}

    defect_id: str = Field(primary_key=True)
    defect_type: str
    defect_category: str
    defect_severity: str


class Machine(SQLModel, table=True):
    """gold.dim_machine - machine de production."""

    __tablename__ = "dim_machine"
    __table_args__ = {"schema": "gold"}

    machine_id: str = Field(primary_key=True)
    production_line_id: str = Field(index=True)
    machine_type: str
    installation_year: int
