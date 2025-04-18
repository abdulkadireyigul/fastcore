"""
Database models for security-related entities.

These models provide persistence for security-related data such as roles and permissions.
"""

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship

from fastcore.models import Base, metadata

# Many-to-many relationship between roles and permissions
role_permissions = Table(
    "role_permissions",
    metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)


class Permission(Base):
    """
    Database model for storing permissions.

    Each permission represents a specific action on a resource.
    """

    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    resource = Column(String, nullable=False)
    action = Column(String, nullable=False)
    name = Column(String, nullable=False, unique=True)  # Format: "resource:action"
    description = Column(String, nullable=True)

    # Relationship with roles
    roles = relationship(
        "Role", secondary=role_permissions, back_populates="permissions"
    )

    def __repr__(self):
        return f"Permission(resource={self.resource}, action={self.action})"


class Role(Base):
    """
    Database model for storing roles.

    Each role can have multiple permissions.
    """

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)

    # Relationship with permissions
    permissions = relationship(
        "Permission", secondary=role_permissions, back_populates="roles"
    )

    def __repr__(self):
        return f"Role(name={self.name})"
