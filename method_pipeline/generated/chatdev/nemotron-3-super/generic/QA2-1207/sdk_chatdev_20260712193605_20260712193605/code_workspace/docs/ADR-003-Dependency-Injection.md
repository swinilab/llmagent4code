# ADR 003: Dependency Injection

## Status
Accepted

## Context
We need to manage dependencies between different layers of the application (e.g., controllers depending on services, services depending on repositories) in a way that is testable, maintainable, and avoids tight coupling.

## Decision
We use FastAPI's built-in dependency injection system with the `Depends` mechanism. Each component (e.g., a service) declares its dependencies (e.g., a repository or database session) as parameters in its constructor or methods, and the framework provides the concrete instances.

## Consequences
### Pros
- **Loose coupling**: Components depend on abstractions (interfaces or base classes) rather than concrete implementations.
- **Ease of testing**: Dependencies can be easily mocked or replaced with test doubles.
- **Centralized configuration**: Dependencies are configured in one place (the route handlers or via dependency providers).
- **Lifecycle management**: FastAPI automatically manages the lifecycle of dependencies (e.g., database sessions are created and closed per request).
- **Integration with OpenAPI**: Dependencies that are Pydantic models are automatically included in the generated API documentation.

### Cons
- **Learning curve**: Developers unfamiliar with FastAPI's dependency injection may need time to adapt.
- **Implicit dependencies**: The dependency resolution is implicit, which can make it harder to trace the flow of control without running the application.

## Alternatives Considered
1. **Manual dependency injection (constructor injection)**: We considered having each class explicitly instantiate its dependencies or receive them via constructor parameters without a framework. However, this leads to boilerplate and makes it harder to change implementations.
2. **Service Locator pattern**: We considered using a global registry to look up dependencies. This was rejected because it hides dependencies and makes testing difficult (a known anti-pattern).
3. **Third-party DI containers (e.g., Dependency Injector, Spring Python)**: We evaluated using a dedicated dependency injection framework but decided that FastAPI's built-in system is sufficient for our needs and avoids adding extra dependencies.

## Implications
- All services and repositories must be designed to be instantiated via dependency injection.
- Database sessions are scoped to individual HTTP requests, ensuring that each request gets its own transaction.
- When testing, we can override dependencies using `app.dependency_overrides` to inject mocks or test doubles.