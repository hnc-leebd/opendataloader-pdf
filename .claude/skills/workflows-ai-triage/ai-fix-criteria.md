# AI Fix Criteria

## Suitable for AI Auto-Fix

| Criteria | Description |
|----------|-------------|
| **Clear scope** | Single file or few related files |
| **Predictable changes** | Bug fixes, type errors, lint errors |
| **Test verifiable** | Can confirm fix by running tests |
| **Low security risk** | Not related to auth, permissions, encryption |
| **Existing patterns** | Similar implementation exists in codebase |

## Not Suitable for AI Auto-Fix

| Criteria | Description |
|----------|-------------|
| **Architecture changes** | Requires design decisions |
| **Domain knowledge** | Requires business logic understanding |
| **Human judgment** | UX decisions, trade-off choices |
| **Wide impact** | Affects many files or systems |
| **External dependencies** | API changes, infrastructure config |
