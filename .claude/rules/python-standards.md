# Python & FastAPI Standards

- **Type Hinting**: All function signatures must have PEP 484 type hints. Use `list[str]` instead of `List[str]` (Python 3.9+ syntax).
- **Async Patterns**: Use `async def` for all route handlers. Use `httpx` for external API calls, never `requests`.
- **Dependency Injection**: Use FastAPI's `Depends()` for database sessions and authentication; do not instantiate global clients.

