# Changelog

All notable changes to the fastcore package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Future features to be released

## [0.1.0] - 2025-04-22

### Added
- Initial release of the fastcore package
- Factory module for configuring FastAPI applications
- Config module for environment-based settings management
- Logging module with structured logging support
- Cache module with Redis backend and decorator support
- Database module with SQLAlchemy integration and repository pattern
- Error handling module with standardized exception classes
- Security module with JWT authentication
- Schemas module for consistent API responses
- Middleware module with CORS and rate limiting support

### API Stability Notice

This is the initial release, and while we aim for stability, the API might change in future minor versions until we reach 1.0.0. After that, breaking changes will only occur in major version bumps.

## API Version Compatibility

| fastcore version | API version | Breaking changes from previous |
|------------------|-------------|---------------------------------|
| 0.1.0            | v1          | Initial release                 |

## Breaking Changes Guide

### When upgrading to future versions

As the library evolves, this section will document migration paths between versions.

#### 0.1.0 to future 0.2.0
- No breaking changes yet documented

#### future 0.2.0 to future 1.0.0 
- API will be stabilized; any breaking changes will be documented here

## Deprecation Policy

- Features marked as deprecated will remain functional for at least one minor version before removal
- Deprecation warnings will be raised during runtime when using deprecated features
- The changelog will clearly indicate when features are deprecated and when they are removed