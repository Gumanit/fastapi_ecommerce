
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy import select, update
from starlette import status

from app.models import Review
from app.schemas import Review as ReviewSchema, ReviewCreate
from app.models.products import Product as ProductModel
from app.models.categories import Category as CategoryModel

from sqlalchemy.ext.asyncio import AsyncSession
from app.db_depends import get_async_db

from app.models.users import User as UserModel
from app.auth import get_current_seller, get_current_buyer, get_current_admin

router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
)

@router.get("/", response_model=List[ReviewSchema])
async def get_reviews(db: AsyncSession = Depends(get_async_db)):
    reviews = await db.scalars(select(Review).where(Review.is_active == True))
    result = reviews.all()
    return result

@router.get("/products/{product_id}", response_model=List[ReviewSchema])
async def get_product_reviews(product_id: int, db: AsyncSession = Depends(get_async_db)):
    reviews = await db.scalars(select(Review).where(Review.product_id == product_id))
    result = reviews.all()
    return result

@router.post("/", response_model=ReviewSchema, status_code=status.HTTP_201_CREATED)
async def create_review(input_data: ReviewCreate,db: AsyncSession = Depends(get_async_db), current_user: UserModel = Depends(get_current_buyer)):
    res = await db.scalars(select(ProductModel).where(ProductModel.id == input_data.product_id, ProductModel.is_active == True))
    product = res.first()
    if not product:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product not found")

    old_review_res = await db.scalars(select(Review).where(Review.user_id == current_user.id, Review.is_active == True))
    old_review = old_review_res.first()
    if old_review is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User's review already exist")
    review = Review(**input_data.model_dump(), user_id=current_user.id)
    db.add(review)
    await db.commit()
    await db.refresh(review)
    await update_product_rating(db, product.id)
    return review

from sqlalchemy.sql import func

async def update_product_rating(db: AsyncSession, product_id: int):
    result = await db.execute(
        select(func.avg(Review.grade)).where(
            Review.product_id == product_id,
            Review.is_active == True
        )
    )
    avg_rating = result.scalar() or 0.0
    product = await db.get(ProductModel, product_id)
    product.rating = avg_rating
    await db.commit()

@router.delete("/{review_id}", status_code=status.HTTP_200_OK)
async def delete_review(review_id: int, current_user: UserModel = Depends(get_current_admin), db: AsyncSession = Depends(get_async_db)):
    res = await db.scalars(select(Review).where(Review.id == review_id, Review.is_active == True))
    review = res.first()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    product_res = await db.scalars(select(ProductModel).where(ProductModel.id == review.product_id, ProductModel.is_active == True))
    product = product_res.first()
    await db.execute(update(Review).where(Review.id == review_id).values(is_active=False))
    await db.commit()
    await update_product_rating(db, product.id)
    return {"status": "success", "message": "Review marked as inactive"}