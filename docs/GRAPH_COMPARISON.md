# Visual Comparison: File Graph vs Function Graph

## File Graph (Existing)
```
┌─────────────┐
│  auth.py    │ (Blue)
└──────┬──────┘
       │ imports
       ▼
┌─────────────┐
│  user.py    │ (Blue)
└──────┬──────┘
       │ imports
       ▼
┌─────────────┐
│  db.py      │ (Blue)
└─────────────┘
```
**Shows**: Which files depend on which other files

## Function Graph (NEW)
```
┌─────────────┐
│  auth.py    │ (Blue - File)
└──────┬──────┘
       │ calls
       ▼
┌─────────────┐
│ validate()  │ (Orange - Function)
└──────┬──────┘
       │ in
       ▼
┌─────────────┐
│  user.py    │ (Blue - File)
└──────┬──────┘
       │ calls
       ▼
┌─────────────┐
│ get_user()  │ (Orange - Function)
└─────────────┘
```
**Shows**: Which files call which functions

## Real Example

### File Graph View
```
routes.py → services.py → models.py → database.py
```
**Interpretation**: "routes.py depends on services.py"

### Function Graph View
```
routes.py → authenticate() → validate_token() → query_db()
   (Blue)      (Orange)         (Orange)          (Orange)
```
**Interpretation**: "routes.py calls authenticate(), which calls validate_token(), which calls query_db()"

## Side-by-Side Comparison

```
FILE GRAPH                    FUNCTION GRAPH
==========                    ==============

[file.py] ──────────>        [file.py] ────────>
   │                             │
   │ imports                     │ calls
   │                             │
   ▼                             ▼
[other.py]                    [function()]
                                 │
                                 │ in
                                 │
                                 ▼
                              [other.py]
```

## When to Use Each

### Use File Graph For:
- 📦 Understanding module structure
- 🔄 Finding circular dependencies
- 🏗️ Architectural patterns
- 📊 High-level coupling

### Use Function Graph For:
- 🔍 Tracing execution paths
- 🎯 Finding function usage
- 🐛 Debugging call chains
- 📝 Understanding code flow

## Combined Power

```
Question: "What happens when I change authenticate()?"

Step 1: Function Graph
→ See which files call authenticate()
→ routes.py, middleware.py, api.py

Step 2: File Graph
→ See what depends on those files
→ Entire application!

Result: High impact change!
```

## Visual Key

```
┌─────────┐
│  Blue   │ = File node
└─────────┘

┌─────────┐
│ Orange  │ = Function node
└─────────┘

────────> = Dependency/Call relationship
```

## Navigation Flow

```
1. Start with File Graph
   ↓
   Understand overall architecture
   ↓
2. Switch to Function Graph
   ↓
   Drill into specific execution paths
   ↓
3. Use dropdown to focus
   ↓
   Trace specific function calls
```

## Example Workflow

```
Developer Task: "Understand authentication flow"

Step 1: Go to Function Graph tab
Step 2: Select "authenticate" from dropdown
Step 3: See visual call chain:
        
        login.py (Blue)
           ↓
        authenticate() (Orange)
           ↓
        validate_token() (Orange)
           ↓
        check_permissions() (Orange)

Step 4: Hover over nodes for file locations
Step 5: Navigate to code to make changes
```

## Graph Density

### File Graph
- **Nodes**: ~50-100 files
- **Edges**: ~100-300 dependencies
- **Density**: Medium

### Function Graph
- **Nodes**: ~200-500 (functions + files)
- **Edges**: ~300-1000 calls
- **Density**: High (use dropdown filter!)

## Pro Tips

1. **File Graph first** - Get the big picture
2. **Function Graph second** - Understand details
3. **Use filters** - Function graph can be dense
4. **Follow colors** - Orange = where the action is
5. **Combine insights** - Use both for complete understanding

## Architecture Levels

```
┌─────────────────────────────────────┐
│         System Level                │
│    (File Graph - Architecture)      │
├─────────────────────────────────────┤
│         Module Level                │
│    (File Graph - Dependencies)      │
├─────────────────────────────────────┤
│        Function Level               │
│   (Function Graph - Execution)      │  ← NEW!
├─────────────────────────────────────┤
│         Code Level                  │
│      (Source Code View)             │
└─────────────────────────────────────┘
```

Now you have visibility at ALL levels! 🎉
