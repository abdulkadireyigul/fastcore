# Database Module

Provides asynchronous database integration using SQLAlchemy for FastAPI applications.

## Features

- Async engine and session factory setup via `create_async_engine` and `async_sessionmaker`
- FastAPI lifecycle integration: initialize and dispose the engine on startup/shutdown
- FastAPI dependency `get_db()` for per-request `AsyncSession` with automatic commit/rollback
- Generic `BaseRepository` with CRUD operations and consistent error handling

## Configuration

Configure database settings in your `BaseAppSettings` (in `fastcore.config`):

```ini
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/dbname
DB_ECHO=false
DB_POOL_SIZE=5
```

## Usage

### Application Factory

In your application factory (`configure_app`), `setup_db` is invoked to register startup/shutdown handlers:

```python
from fastapi import FastAPI
from fastcore.factory import configure_app

app = FastAPI()
configure_app(app)
``` 

### Dependency Injection

Use the `get_db` dependency to receive a database session in endpoints:

```python
from fastapi import APIRouter, Depends
from fastcore.db import get_db

router = APIRouter()

@router.get("/items/")
async def list_items(db=Depends(get_db)):
    return await db.execute(...)
```

### Repository Pattern

Extend `BaseRepository` for model-specific logic:

```python
from fastcore.db import BaseRepository, get_db
from app.models import User
from fastapi import Depends

class UserRepository(BaseRepository[User]):
    pass

@router.get("/users/{id}")
async def get_user(id: int, db=Depends(get_db)):
    repo = UserRepository(User, db)
    return await repo.get_by_id(id)
```

This module covers core database concerns; further application-specific repository or migration setup can be done in your project.
