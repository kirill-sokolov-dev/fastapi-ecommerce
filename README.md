Marketplace API

Асинхронный REST API для маркетплейса, разработанный на FastAPI с использованием SQLAlchemy 2.0 и JWT-аутентификации.

Стек технологий

Фреймворк: FastAPI
База данных & ORM:** PostgreSQL, SQLAlchemy (Async)
Миграции: Alembic
Безопасность: PyJWT, pwdlib, OAuth2 Password Bearer

Текущий функционал

Регистрация пользователей с ролями (`buyer`, `seller`).
Аутентификация по стандарту OAuth2 (`/users/token`) с выдачей JWT (Access & Refresh токены).
Защита эндпоинтов и проверка прав доступа (ролевая модель RBAC: проверка `is_active`, а также ролей `seller` и `admin`).
Асинхронное подключение к базе данных.
