from fastapi import APIRouter, HTTPException, status, Depends
from app.db_depends import get_async_db
from app.schemas import CreateReview, Review as ReviewSchema
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth import get_current_buyer
from app.models import User as UserModel, Review as ReviewModel, Product as ProductModel
from sqlalchemy import select, func



router = APIRouter(prefix="/reviews", tags=["reviews"])

@router.post("/", response_model=ReviewSchema, status_code=status.HTTP_201_CREATED)
async def create_review(review: CreateReview,
                        db: AsyncSession = Depends(get_async_db),
                        current_user: UserModel = Depends(get_current_buyer)):
    """
    Эндпоинт по созданию отзыва на товар
    """
    if current_user.role!= "buyer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    result = await db.scalars(select(UserModel).where(current_user.is_active == True))

    stmt_product = await db.scalars(select(ProductModel).where(ProductModel.id == review.product_id, ProductModel.is_active == True))
    product = stmt_product.first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Продукт не найден")

    user = result.first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    new_review = ReviewModel(**review.model_dump(), user_id = current_user.id)

    db.add(new_review)
    await db.commit()
    await db.refresh(new_review)

    grade_sum = await db.execute(select(func.avg(ReviewModel.grade)).where(ReviewModel.product_id == review.product_id))

    new_rating = grade_sum.scalar()

    product.rating = new_rating

    await db.commit()

    return new_review

@router.get("/",response_model=list[ReviewSchema], status_code=status.HTTP_200_OK)
async def get_all_reviews(db: AsyncSession = Depends(get_async_db)):
    """
    GET запрос для получения всех активных отзывов.
    """
    result = await db.scalars(select(ReviewModel).where(ReviewModel.is_active == True))

    return result.all()

@router.get("/products/{product_id}/", response_model=list[ReviewSchema], status_code=status.HTTP_200_OK)
async def get_reviews_from_product_id(product_id: int, db: AsyncSession = Depends(get_async_db)):
    stmt_product = await db.scalars(select(ProductModel).where(ProductModel.is_active == True, ProductModel.id == product_id))
    product = stmt_product.first()

    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Продукт с ID {product_id} не найден")

    stmt_reviews = await db.scalars(select(ReviewModel).where(ReviewModel.product_id == product_id,
                                                              ReviewModel.is_active == True))

    reviews = stmt_reviews.all()

    if reviews is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отзывов не найдено")

    return reviews