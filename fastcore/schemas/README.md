# Schemas Module

Common Pydantic schemas for FastAPI applications.

## Overview

This module provides standardized schemas for:

- API Responses (see [response/README.md](response/README.md))
  - Base response structure
  - Single object responses (DataResponse)
  - List responses with pagination (ListResponse)
  - Error responses (ErrorResponse)
  
- Metadata
  - Base metadata (timestamp, version)
  - Response-specific metadata (e.g. pagination info)

## Quick Start

```python
from fastapi import FastAPI
from fastcore.schemas import DataResponse, ListResponse

app = FastAPI()

@app.get("/users/{id}")
def get_user(id: int):
    return DataResponse(data={"id": id, "name": "John"})

@app.get("/users")
def list_users(page: int = 1):
    return ListResponse(
        data=[{"id": 1}, {"id": 2}],
        metadata={"total": 10, "page": page}
    )
```

For detailed documentation and examples:
- [Response Schemas](response/README.md)
- Base Metadata: See `metadata.py`