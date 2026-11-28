from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.params import Query

from app.db_depends import get_db, get_async_db
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.schemas import Product as ProductSchema, ProductCreate, ProductList
from app.models import Category as CategoryModel, Product as ProductModel
from app.models import User as UserModel
from app.auth import get_current_seller

# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.get("/", response_model=ProductList, status_code=status.HTTP_200_OK)
async def get_all_products(page: int = Query(1, ge=1),
                           page_size: int = Query(20, ge=1, le=100),
                           category_id: int | None = Query(None, description="ID категории для фильтрации"),
                           min_price: float | None = Query(None, ge=0, description="Минимальная цена товара"),
                           max_price: float | None = Query(None, ge=0, description="Максимальная цена товара"),
                           in_stock: bool | None = Query(None, description="true — только товары в наличии, false — только без остатка"),
                           seller_id: int | None = Query(None, description="ID продавца для фильтрации"),
                           db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех товаров с поддержкой фильтров.
    """
    # Проверка логики min_price <= max_price
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_price не может быть больше max_price",
        )

    filters = [ProductModel.is_active == True]

    if category_id is not None:
        filters.append(ProductModel.category_id == category_id)
    if min_price is not None:
        filters.append(ProductModel.price >= min_price)
    if max_price is not None:
        filters.append(ProductModel.price <= max_price)
    if in_stock is not None:
        filters.append(ProductModel.stock > 0 if in_stock else ProductModel.stock == 0)
    if seller_id is not None:
        filters.append(ProductModel.seller_id == seller_id)

    total_stmt = select(func.count(ProductModel.id)).where(*filters)
    total = await db.scalar(total_stmt) or 0

    products_stmt = (select(ProductModel)
                     .where(*filters)
                     .order_by(ProductModel.id)
                     .offset((page - 1) * page_size)
                     .limit(page_size))

    items = (await db.scalars(products_stmt)).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(product: ProductCreate,
                         db: AsyncSession = Depends(get_async_db),
                         current_user: UserModel = Depends(get_current_seller)):
    """
    Создаёт новый товар.
    """
    stmt_category = await db.scalars(select(CategoryModel).where(CategoryModel.id == product.category_id,
                                                CategoryModel.is_active == True))
    category = stmt_category.first()

    if category is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found or inactive")

    db_product = ProductModel(**product.model_dump(), seller_id = current_user.id)
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
async def update_product(product_id: int, in_product: ProductCreate,
                         db: AsyncSession = Depends(get_async_db),
                         current_user: UserModel = Depends(get_current_seller)):
    """
    Обновляет товар по его ID.
    """
    stmt_product = await db.scalars(select(ProductModel).
                    where(ProductModel.id == product_id, ProductModel.is_active == True))

    db_product = stmt_product.first()
    if db_product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")

    if db_product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own products")

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
async def delete_product(product_id: int,
                         db: AsyncSession = Depends(get_async_db),
                         current_user: UserModel = Depends(get_current_seller)):
    """
    Удаляет товар по его ID.
    """
    stmt_product = await db.scalars(select(ProductModel).
                                    where(ProductModel.id == product_id, ProductModel.is_active == True))
    db_product = stmt_product.first()
    if db_product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")
    if db_product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own products")
    db_product.is_active = False
    await db.commit()
    await db.refresh(db_product)
    return db_product
