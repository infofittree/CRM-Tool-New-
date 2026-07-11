"""Products router — CRUD for the product catalog."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_db
from api.schemas import ProductCreate, ProductResponse
from database.models import Product

router = APIRouter()


@router.get("", response_model=list[ProductResponse])
def list_products(db: Session = Depends(get_db)):
    """List all active products."""
    products = db.scalars(select(Product).where(Product.is_active.is_(True)).order_by(Product.category, Product.name)).all()
    return products


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(body: ProductCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.get("role") not in ("Admin", "Manager"):
        raise HTTPException(status_code=403, detail="Only Admin or Manager can create products")
    existing = db.scalar(select(Product).where(Product.name == body.name))
    if existing:
        raise HTTPException(status_code=400, detail="A product with this name already exists")
    product = Product(name=body.name, category=body.category)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, body: ProductCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.get("role") not in ("Admin", "Manager"):
        raise HTTPException(status_code=403, detail="Only Admin or Manager can update products")
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.name = body.name
    product.category = body.category
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.get("role") not in ("Admin",):
        raise HTTPException(status_code=403, detail="Only Admin can delete products")
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_active = False
    db.commit()
