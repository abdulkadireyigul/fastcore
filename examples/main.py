"""
Example FastAPI application using FastCore.

This is a minimal example of how to use FastCore to quickly bootstrap
a new FastAPI application with all components pre-configured.
"""

from fastapi import Depends, FastAPI

from fastcore.app_factory import create_app
from fastcore.config.base import Environment
from fastcore.db.session import Session, get_db

# Create app with all components enabled
app = create_app(
    env=Environment.DEVELOPMENT,
    enable_cors=True,
    enable_database=True,
    enable_error_handlers=True,
    db_echo=True,  # SQL logging for development
)

# Example model (in a real app, this would be in a separate models.py file)
class Item:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name

# Example data access (in a real app, this would use SQLAlchemy models)
def get_items(db: Session):
    # This is just an example - in a real app you'd query your database
    # e.g., return db.query(ItemModel).all()
    return [Item(id=1, name="Item 1"), Item(id=2, name="Item 2")]

# Example routes
@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI powered by FastCore!"}

@app.get("/items/")
def read_items(db: Session = Depends(get_db)):
    # Example of using the database session
    items = get_items(db)
    return [{"id": item.id, "name": item.name} for item in items]

# Error handling example
@app.get("/error")
def trigger_error():
    # This will be caught by the exception handlers
    raise ValueError("Example error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)