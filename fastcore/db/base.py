from sqlalchemy.orm import declarative_base

# Declarative base for SQLAlchemy models
Base = declarative_base()

# Expose metadata for Alembic autogenerate
metadata = Base.metadata
