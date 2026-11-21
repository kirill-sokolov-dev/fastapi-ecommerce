from fastapi import APIRouter, HTTPException, status, Depends
from app.db_depends import get_db, get_async_db
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.schemas import Product as ProductSchema, ProductCreate
from app.models import Category as CategoryModel, Product as ProductModel

# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.get("/", response_model=list[ProductSchema], status_code=status.HTTP_200_OK)
async def get_all_products(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех товаров.
    """
    result = await db.scalars(select(ProductModel).where(ProductModel.is_active == True))
    return result.all()


@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(product: ProductCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Создаёт новый товар.
    """
    stmt_category = await db.scalars(select(CategoryModel).where(CategoryModel.id == product.category_id,
                                                CategoryModel.is_active == True))
    category = stmt_category.first()

    if category is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found or inactive")

    db_product = ProductModel(**product.model_dump())
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product


@router.get("/category/{category_id}", response_model=list[ProductSchema], status_code=status.HTTP_200_OK)
async def get_products_by_category(category_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список товаров в указанной категории по её ID.
    """
    stmt_category = await db.scalars(select(CategoryModel).
                               where(CategoryModel.id == category_id, CategoryModel.is_active == True))
    result_category = stmt_category.first()
    if result_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found or inactive")

    stmt_products = await db.scalars(select(ProductModel).
                               where(ProductModel.category_id == category_id,
                               ProductModel.is_active == True))

    result_products = stmt_products.all()
    return result_products


@router.get("/{product_id}", response_model=ProductSchema, status_code=status.HTTP_200_OK)
async def get_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    stmt = await db.scalars(select(ProductModel).
                            where(ProductModel.id == product_id, ProductModel.is_active == True))

    product = stmt.first()

    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")

    stmt_product_category = await db.scalars(select(CategoryModel).where(CategoryModel.is_active == True,
                                                        CategoryModel.id == product.category_id))

    product_category = stmt_product_category.first()
    if product_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found or inactive")

    return product


@router.put("/{product_id}", response_model=ProductSchema, status_code=status.HTTP_200_OK)
async def update_product(product_id: int, in_product: ProductCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Обновляет товар по его ID.
    """
    stmt_product = await db.scalars(select(ProductModel).
                    where(ProductModel.id == product_id, ProductModel.is_active == True))

    db_product = stmt_product.first()
    if db_product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")

    stmt_category = await db.scalars(select(CategoryModel).where(CategoryModel.id == in_product.category_id,
                                                CategoryModel.is_active == True))
    category = stmt_category.first()

    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found or inactive")

    await db.execute(update(ProductModel).where(ProductModel.id == product_id,
                                          ProductModel.is_active == True).
                                          values(**in_product.model_dump()))

    await db.commit()
    await db.refresh(db_product)
    return db_product


@router.delete("/{product_id}", response_model=ProductSchema, status_code=status.HTTP_200_OK)
async def delete_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Удаляет товар по его ID.
    """
    stmt_product = await db.scalars(select(ProductModel).
                                    where(ProductModel.id == product_id, ProductModel.is_active == True))
    db_product = stmt_product.first()
    if db_product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")

    db_product.is_active = False
    await db.commit()
    await db.refresh(db_product)
    return db_product
