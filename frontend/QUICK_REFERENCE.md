# ARCHITECH Frontend - Quick Reference

## 🚀 Quick Commands

```bash
# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test
```

## 📁 File Locations

| What | Where |
|------|-------|
| Components | `src/components/` |
| API Service | `src/services/api.js` |
| Main App | `src/App.js` |
| Styles | `src/App.css` |
| HTML Template | `public/index.html` |

## 🔌 API Endpoints

```javascript
// Import
import { api } from './services/api';

// Usage
api.analyzeRepo(repoUrl)           // POST /analyze
api.getStatus(jobId)               // GET /status/{job_id}
api.getPatterns()                  // GET /patterns
api.getCoupling()                  // GET /coupling
api.analyzeImpact(filePath)        // POST /impact
api.getArchitecture()              // GET /architecture
api.getDependencies(filePath)      // GET /dependencies/{path}
api.getBlastRadius(filePath)       // GET /blast-radius/{path}
api.debugFiles()                   // GET /debug/files
```

## 🎨 Component Props

### AnalyzeRepo
```javascript
<AnalyzeRepo onAnalysisComplete={() => {}} />
```

### Other Components
```javascript
// No props needed - they fetch their own data
<PatternDetection />
<CouplingAnalysis />
<ImpactAnalysis />
<ArchitectureView />
<DependencyGraph />
```

## 🎯 Common Tasks

### Add New Tab
```javascript
// 1. In App.js, add to tabs array:
{ id: 'newtab', label: 'New Tab' }

// 2. Add component import:
import NewComponent from './components/NewComponent';

// 3. Add to render:
{activeTab === 'newtab' && <NewComponent />}
```

### Add New API Endpoint
```javascript
// In src/services/api.js:
export const api = {
  // ... existing methods
  newEndpoint: (param) => 
    axios.get(`${API_BASE}/new-endpoint/${param}`)
};
```

### Update Styles
```javascript
// Inline (in component):
const styles = {
  container: { padding: '20px', background: '#fff' }
};

// Global (in App.css):
.my-class { color: red; }
```

## 🐛 Debugging

```javascript
// Check API response
console.log('API Response:', data);

// Check component state
console.log('State:', state);

// Check props
console.log('Props:', props);
```

## 🎨 Color Palette

```javascript
const colors = {
  primary: '#667eea',
  secondary: '#764ba2',
  success: '#28a745',
  warning: '#ffc107',
  danger: '#dc3545',
  info: '#007bff',
  light: '#f0f2f5',
  dark: '#333333'
};
```

## 📊 State Management

```javascript
// useState
const [data, setData] = useState(null);

// useEffect
useEffect(() => {
  loadData();
}, []); // Empty array = run once on mount

// useEffect with dependency
useEffect(() => {
  loadData();
}, [refreshKey]); // Run when refreshKey changes
```

## 🔄 Common Patterns

### Fetch Data on Mount
```javascript
useEffect(() => {
  const fetchData = async () => {
    try {
      const { data } = await api.getData();
      setData(data);
    } catch (error) {
      console.error(error);
    }
  };
  fetchData();
}, []);
```

### Handle Form Submit
```javascript
const handleSubmit = async () => {
  setLoading(true);
  try {
    const { data } = await api.submit(formData);
    setResult(data);
  } catch (error) {
    setError(error.message);
  }
  setLoading(false);
};
```

### Conditional Rendering
```javascript
{loading && <div>Loading...</div>}
{error && <div>Error: {error}</div>}
{data && <div>{data.value}</div>}
```

## 🚨 Error Handling

```javascript
try {
  const { data } = await api.call();
  // Success
} catch (error) {
  console.error('Error:', error);
  // Handle error
}
```

## 📱 Responsive Design

```javascript
const styles = {
  container: {
    padding: '20px',
    '@media (max-width: 768px)': {
      padding: '10px'
    }
  }
};
```

## 🔧 Environment Variables

```javascript
// Create .env file:
REACT_APP_API_URL=http://localhost:8000

// Use in code:
const API_BASE = process.env.REACT_APP_API_URL;
```

## 📦 Build & Deploy

```bash
# Build
npm run build

# Serve locally
npx serve -s build

# Deploy to server
# Copy build/ folder to web server
```

## 🎯 Performance Tips

1. Use `React.memo()` for expensive components
2. Debounce API calls
3. Limit graph nodes to <100
4. Use `useCallback` for event handlers
5. Lazy load heavy components

## 📝 Code Style

```javascript
// Component naming: PascalCase
function MyComponent() {}

// Function naming: camelCase
const handleClick = () => {};

// Constants: UPPER_CASE
const API_BASE = 'http://localhost:8000';

// Styles object: camelCase
const styles = { myStyle: {} };
```

## 🔍 Useful Commands

```bash
# Clear cache
rm -rf node_modules package-lock.json
npm install

# Check for updates
npm outdated

# Update packages
npm update

# Audit security
npm audit
```

## 📚 Documentation Links

- [React Docs](https://react.dev)
- [D3.js Docs](https://d3js.org)
- [Axios Docs](https://axios-http.com)
- [Backend API](http://localhost:8000/docs)

---

**Quick Start**: `npm install && npm start`
**Default Port**: 3000
**Backend URL**: http://localhost:8000
