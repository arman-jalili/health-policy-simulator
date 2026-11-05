# [Module Name] Architecture

<!--
Canonical Reference: .pi/architecture/modules/[module-name].md
Blueprint Source: Guardian Framework v1.2
Generated: NEVER (this is the source)
-->

## Overview

[Brief description of the module's purpose and scope within the system]

## DDD Layers

This module follows Clean Architecture with 4 DDD layers:

| Layer | Purpose | Tech |
|-------|---------|------|
| `domain/` | Pure business logic, types, errors | Zero framework imports |
| `application/` | State management, use cases, actions | Stores, Server Actions |
| `infrastructure/` | External adapters, API clients, SDKs | Fetch, tRPC, GraphQL |
| `interfaces/` | UI components, pages, layouts | React, Next.js |

**Dependency rule:** `domain → application → infrastructure → interfaces` (inward)

## Components by Layer

### Domain Layer (`domain/`)
| Component | Description | Framework? |
|-----------|-------------|------------|
| [Name] | [Purpose] | ❌ No |

### Application Layer (`application/`)
| Component | Description | Type |
|-----------|-------------|------|
| [Name] | [Purpose] | Store / Action / Query |

### Infrastructure Layer (`infrastructure/`)
| Component | Description | Connects to |
|-----------|-------------|-------------|
| [Name] | [Purpose] | [API / SDK] |

### Interfaces Layer (`interfaces/`)
| Component | Description | 'use client'? |
|-----------|-------------|---------------|
| [Name] | [Purpose] | Yes / No |

---

## Component Details

### [Component Name]

**Purpose:** [What this component does]

**DDL Layer:** `[domain/application/infrastructure/interfaces]`

**Implementation File:** `src/[module]/[layer]/[file].ts`

**Canonical Reference:** `.pi/architecture/modules/[module-name].md#[component-section]`

**States:**
- **Loading:** [What the user sees during load]
- **Empty:** [What the user sees when there's no data]
- **Populated:** [Normal state]
- **Error:** [What the user sees on failure]

**Dependencies:**
- [Dependency 1]
- [Dependency 2]

---

## Data Flow

```
User Intent
     │
     ▼
Component (interfaces/) → user action
     │
     ▼
Store/Server Action (application/) → optimistic update
     │
     ▼
API Client (infrastructure/) → fetch
     │
     ▼
Response → commit or rollback → UI update
```

**Flow Description:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

---

## User Intents

| Intent | Triggered By | Handled By | Domain Event (backend) |
|--------|-------------|------------|----------------------|
| UserClickedThread | Click on thread title | ThreadPanel | ThreadSelected |
| UserSubmittedComment | Click Submit button | CommentInput | CommentCreated |

---

## Design Principles

- This module is **optimistic**: UI updates before API responds
- This module is **resilient**: failure doesn't crash other modules
- This module is **stateless**: state lives in stores, not server

---

## Degradation Strategy

| Feature | When Unavailable | User Sees |
|---------|-----------------|-----------|
| [Feature] | API is down | [Degraded state] |

---

## Acceptance Criteria

Each component in this module has specific acceptance criteria that must be verified
before the implementation issue can be closed. These ACs flow into the generated issues.

| # | Component | Criterion | Verify In |
|---|-----------|-----------|-----------|
| 1 | [ComponentName] | [Specific, testable criterion for this component] | [unit test / integration test / manual] |
| 2 | [ComponentName] | [Another criterion] | [verification method] |

---

## Wiring Contract

A module is not done when its tests pass. It is done when it is reachable from `create_app` and every
collaborator it injects actually runs. Delete a row and you have described a module that green CI cannot
distinguish from a working one.

| # | Wiring point | Requirement | Proof |
|---|---|---|---|
| W1 | Router | `app.include_router(...)` in `src/shared/app.py` | boot test asserting every documented route is in the app |
| W2 | Composition | `build_container(settings)` selects adapters by config; memory is never the silent default outside tests | boot test with the production config |
| W3 | Persistence | migrations own every table the repositories query | `alembic upgrade head` on an empty DB, then restart round-trip |
| W4 | Events | drained events leave through `shared_event_outbox` in the aggregate's transaction | outbox row present after a command |
| W5 | Published language | cross-context reads go through a port, never another context's tables | architecture test on imports |
| W6 | Fail closed | a missing upstream dependency refuses, never degrades to permissive | negative test with the dependency unbound |
| W7 | Boot | registration + adapter selection asserted by a boot test | deleting a router registration turns CI red |
| W8 | Reachability | every injected collaborator is invoked from a named entry point and its effect is observable from outside | a call site outside `composition.py`/tests **and** a test driving the public entry point; a unit test of the collaborator is never proof; adapters implementing one port are proven equal |
| W9 | Atomic allocation | monotonic counters/sequences/ordinals are allocated by the store, not `max + 1` in application code | concurrency test: N writers → `1..N`, no loss, no `IntegrityError` |
| W10 | Liveness | each background task started by lifespan reports health and degrades `/readyz` when dead | kill-the-task test |

### Collaborator reachability (W8)

| Collaborator | Invoked from | Observable effect | Fails when |
|---|---|---|---|
| [Policy object / guard / parser / resolver] | [application service or route] | [API field, persisted row, emitted event, metric] | [what a dead injection looks like] |

A collaborator with no row is a defect in this document, not a detail of implementation. The recurring
failure in this codebase is a class that is constructed, injected, unit-tested and never called — proofing
checks shapes and cannot see the missing call site.

## Dependencies

### Depends On
- **[Module Name]**: [Why/what it provides]

### Used By
- **[Module Name]**: [Why/what it uses]

---

## Security Considerations

| Concern | Mitigation |
|---------|------------|
| [Concern 1] | [Mitigation] |

---

## Testing Requirements

| Layer | Test Type | Coverage Target |
|-------|-----------|-----------------|
| Domain | Unit | [X]% |
| Application | Unit | [X]% |
| Infrastructure | Integration | [X]% |
| Interfaces | Component | [X]% |

**Key Test Scenarios:**
- [Scenario 1]
- [Scenario 2]
- [Scenario 3]

---

## Error Handling

**Domain errors (domain/):**

TypeScript:
```typescript
class [ErrorType] extends Error {
  constructor(code: string, message: string, retriable?: boolean) {
    super(message);
    this.name = '[ErrorType]';
  }
}
```

Java:
```java
// domain/error/DomainException.java — abstract base
public abstract class DomainException extends RuntimeException {
  private final ErrorCode code;
  protected DomainException(ErrorCode code, String message) {
    super(message); this.code = code;
  }
  public ErrorCode getCode() { return code; }
}

// domain/error/DomainError.java — concrete error
public class DomainError extends DomainException {
  public DomainError(ErrorCode code, String message) { super(code, message); }
}
```

Python:
```python
class DomainError(Exception):
    """Base domain error."""
    def __init__(self, message: str, code: str = "VALIDATION"):
        super().__init__(message)
        self.code = code
```

Go:
```go
var (
    ErrNotFound    = errors.New("resource not found")
    ErrInvalidState = errors.New("invalid state")
)
```

Rust:
```rust
#[derive(Debug, thiserror::Error)]
pub enum DomainError {
    #[error("Resource {0} not found")]
    NotFound(String),
    #[error("Invalid state: {0}")]
    InvalidState(String),
}
```

**Recovery:**
- [Error 1]: [Recovery strategy]
- [Error 2]: [Recovery strategy]

---

## Performance Considerations

| Metric | Target | Strategy |
|--------|--------|----------|
| [Metric] | [Target] | [Strategy] |

---

*Last updated: [date]*
*Module version: [version]*
