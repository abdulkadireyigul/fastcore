# Database Module

SQL database integration for FastAPI applications using SQLAlchemy, with async support and repository pattern.

## Features

- Async SQLAlchemy integration using asyncpg
- Automatic connection lifecycle management
- Repository pattern for clean data access
- FastAPI dependency for session injection
- Declarative base class for models
- Transaction support

## Installation

Install the required dependencies:

```bash
pip install sqlalchemy>=2.0.0 asyncpg>=0.27.0
```

## Configuration

Configure the database connection through environment variables or settings:

```python
from fastcore.config import BaseAppSettings

class AppSettings(BaseAppSettings):
    # Database settings
    DB_URL: str = "postgresql+asyncpg://user:password@localhost/dbname"
    DB_ECHO: bool = False  # Set to True for SQL logging
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
```

Common environment variables:
- `DB_URL`: Database connection URL (SQLAlchemy format)
- `DB_ECHO`: Enable SQL query logging
- `DB_POOL_SIZE`: Connection pool size
- `DB_MAX_OVERFLOW`: Maximum overflow connections
- `DB_POOL_TIMEOUT`: Connection pool timeout in seconds

## Usage

### Creating Models

Define your database models using the provided Base class:

```python
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from fastcore.db import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    
    items = relationship("Item", back_populates="owner")

class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True)
    title = Column(String, index=True)
    description = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    
    owner = relationship("User", back_populates="items")
```

### Repository Pattern

Create repositories for your models:

```python
from fastcore.db import BaseRepository
from .models import User

class UserRepository(BaseRepository[User]):
    model = User
    
    async def find_by_username(self, username: str) -> User:
        query = self.select().where(self.model.username == username)
        return await self.execute_scalar(query)
```

### Using in API Routes

Use the database session in your API routes:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastcore.db import get_db
from .repository import UserRepository

router = APIRouter()

@router.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

### Transactions

Use transactions to ensure data consistency:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastcore.db import get_db
from .repository import UserRepository, ItemRepository

router = APIRouter()

@router.post("/users/{user_id}/items")
async def create_item_for_user(
    user_id: int, 
    item_data: dict,
    db: AsyncSession = Depends(get_db)
):
    # Start a transaction
    async with db.begin():
        user_repo = UserRepository(db)
        item_repo = ItemRepository(db)
        
        # Operations within this block are part of the same transaction
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        item = await item_repo.create(
            {"owner_id": user_id, **item_data}
        )
    
    # Transaction is automatically committed if no exceptions are raised
    # or rolled back if an exception occurs
    return item
```

## Integration with Factory

Database connections are automatically set up when using the application factory:

```python
from fastapi import FastAPI
from fastcore.factory import configure_app

app = FastAPI()
configure_app(app)  # Sets up database based on app settings
```
