# Function Graph Quick Reference

## 🎯 Quick Access

**Frontend Tab**: "Function Graph" (between "File Graph" and "Compare")

**API Endpoints**:
- `/graph/functions` - All function relationships
- `/graph/function/{name}` - Specific function call chain
- `/functions` - List all functions

## 🎨 Visual Legend

| Color | Type | Size | Meaning |
|-------|------|------|---------|
| 🟠 Orange | Function | Large (r=10) | Callable function |
| 🔵 Blue | File | Small (r=8) | File that calls function |

**Arrows**: Point from caller → callee

## ⌨️ Keyboard/Mouse Controls

- **Drag**: Move nodes
- **Scroll**: Zoom in/out
- **Click + Drag (background)**: Pan view
- **Hover**: Show tooltip (file path, line number)

## 📋 Dropdown Options

- **"All Functions"**: Show complete call graph
- **Specific function**: Show only that function's call chain

## 🔍 Use Cases

| Scenario | Action |
|----------|--------|
| Find who calls a function | Select function from dropdown |
| See all function relationships | Select "All Functions" |
| Trace execution path | Follow arrows from caller to callee |
| Find function location | Hover over orange node |

## 💡 Tips

1. **Start with specific function** if graph is too large
2. **Drag nodes apart** to see relationships clearly
3. **Zoom out** to see overall structure
4. **Hover for details** - shows file path and line number
5. **Orange = important** - these are the actual functions

## 🆚 When to Use Which Graph

| Use File Graph When... | Use Function Graph When... |
|----------------------|--------------------------|
| Understanding architecture | Tracing execution flow |
| Finding module dependencies | Finding function callers |
| Detecting circular imports | Understanding call chains |
| High-level overview | Detailed code flow |

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| No nodes showing | Analyze a repository first |
| Graph too crowded | Select specific function |
| Can't see labels | Zoom in |
| Nodes overlapping | Drag them apart |

## 📊 Example Interpretation

```
FileA.py (blue) → calculate() (orange)
```
**Meaning**: FileA.py calls the function calculate()

```
FileB.py (blue) → process() (orange)
FileC.py (blue) → process() (orange)
```
**Meaning**: Both FileB.py and FileC.py call process() (shared function)

## 🚀 Quick Test

```bash
# Backend
curl http://localhost:8000/graph/functions

# Should return:
{
  "nodes": [...],  # Functions + Files
  "edges": [...]   # Call relationships
}
```

## 📞 Related Features

- **Functions Tab**: List view of all functions
- **File Graph Tab**: File-level dependencies
- **Impact Analysis**: See what breaks if you change a function
