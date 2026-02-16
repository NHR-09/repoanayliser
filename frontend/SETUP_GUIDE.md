# ARCHITECH Frontend - Complete Setup Guide

## 🎯 Overview

The ARCHITECH frontend is a React-based web application that provides an intuitive interface for architectural recovery and analysis.

## 📋 Prerequisites

Before starting, ensure you have:

- **Node.js 16+** - [Download](https://nodejs.org/)
- **npm** (comes with Node.js)
- **Backend server running** on `http://localhost:8000`
- **Neo4j database** running on `http://localhost:7474`

## 🚀 Quick Start

### Option 1: Automated Start (Windows)

```bash
# From project root
start_frontend.bat
```

### Option 2: Manual Start

```bash
cd frontend
npm install
npm start
```

The app will automatically open at `http://localhost:3000`

## 📁 Project Structure

```
frontend/
├── public/
│   └── index.html              # HTML template
├── src/
│   ├── components/
│   │   ├── AnalyzeRepo.js      # Repository analysis form
│   │   ├── PatternDetection.js # Pattern visualization
│   │   ├── CouplingAnalysis.js # Coupling metrics display
│   │   ├── ImpactAnalysis.js   # Blast radius analyzer
│   │   ├── ArchitectureView.js # Multi-level explanations
│   │   └── DependencyGraph.js  # D3.js graph visualization
│   ├── services/
│   │   └── api.js              # Backend API client
│   ├── App.js                  # Main application component
│   ├── App.css                 # Global styles
│   └── index.js                # React entry point
├── package.json                # Dependencies
└── README.md                   # Documentation
```

## 🎨 Features

### 1. Repository Analysis
- Enter GitHub repository URL
- Real-time analysis status tracking
- Background job processing

### 2. Pattern Detection Dashboard
- Visual display of detected patterns
- Confidence scores
- Pattern-specific metrics (layers, controllers, models, views)

### 3. Coupling Analysis
- High coupling file identification
- Fan-in/Fan-out metrics
- Circular dependency detection
- Overall coupling statistics

### 4. Impact Analysis
- File path input
- Blast radius calculation
- Risk level classification (High/Medium/Low)
- Affected files list
- AI-generated impact explanation

### 5. Architecture Explanation
- Macro level (system overview)
- Meso level (module responsibilities)
- Micro level (file/function details)
- Evidence citations

### 6. Dependency Graph
- Interactive D3.js force-directed graph
- Drag-and-drop nodes
- File relationship visualization
- Real-time updates

## 🔧 Configuration

### API Endpoint

The frontend connects to the backend at `http://localhost:8000` by default.

To change this, edit `src/services/api.js`:

```javascript
const API_BASE = 'http://your-backend-url:port';
```

### Port Configuration

To run on a different port, set the PORT environment variable:

```bash
# Windows
set PORT=3001 && npm start

# Linux/Mac
PORT=3001 npm start
```

## 🧪 Testing the Frontend

1. **Start Backend** (if not running):
   ```bash
   cd backend
   python main.py
   ```

2. **Start Frontend**:
   ```bash
   cd frontend
   npm start
   ```

3. **Test Workflow**:
   - Navigate to Analyze tab
   - Enter: `https://github.com/pallets/flask`
   - Click "Analyze"
   - Wait for completion
   - Explore other tabs (Patterns, Coupling, etc.)

## 📦 Dependencies

### Core Dependencies
- **react** (^18.2.0) - UI framework
- **react-dom** (^18.2.0) - React DOM rendering
- **react-scripts** (5.0.1) - Build tooling
- **axios** (^1.6.0) - HTTP client
- **d3** (^7.8.5) - Graph visualization

### Development Dependencies
All handled by `react-scripts`

## 🏗️ Building for Production

```bash
npm run build
```

This creates an optimized production build in the `build/` folder.

### Serving Production Build

```bash
# Install serve globally
npm install -g serve

# Serve the build
serve -s build -l 3000
```

## 🐛 Troubleshooting

### Issue: "npm: command not found"
**Solution**: Install Node.js from https://nodejs.org/

### Issue: "Port 3000 already in use"
**Solution**: 
```bash
# Kill process on port 3000 (Windows)
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Or use different port
set PORT=3001 && npm start
```

### Issue: "Failed to fetch from backend"
**Solution**: 
- Ensure backend is running on `http://localhost:8000`
- Check CORS settings in backend `main.py`
- Verify network connectivity

### Issue: "Module not found"
**Solution**:
```bash
rm -rf node_modules package-lock.json
npm install
```

### Issue: Graph not rendering
**Solution**:
- Ensure D3.js is installed: `npm install d3`
- Check browser console for errors
- Verify files exist in backend

## 🎯 Usage Tips

1. **Always analyze a repository first** before exploring other tabs
2. **Use small repositories** (<100 files) for best graph performance
3. **Check backend logs** if analysis fails
4. **Refresh data** by switching tabs after new analysis
5. **Use Neo4j Browser** for advanced graph queries

## 🔗 Related Links

- [Backend API Documentation](../docs/API.md)
- [Main README](../README.md)
- [Implementation Status](../docs/IMPLEMENTATION_STATUS.md)

## 📝 Development Notes

### Adding New Components

1. Create component in `src/components/`
2. Import in `App.js`
3. Add to tabs array
4. Add route in main render

### Styling Guidelines

- Use inline styles for component-specific styling
- Use `App.css` for global styles
- Follow existing color scheme (purple gradient)
- Maintain responsive design principles

### API Integration

All API calls go through `src/services/api.js`:

```javascript
import { api } from '../services/api';

// Example usage
const { data } = await api.getPatterns();
```

## 🚀 Performance Optimization

- Components use React.memo where appropriate
- API calls are debounced
- Graph rendering is optimized for <100 nodes
- Lazy loading for heavy components (future enhancement)

## 📊 Browser Support

- Chrome (recommended)
- Firefox
- Edge
- Safari

## 🤝 Contributing

When adding features:
1. Follow existing code structure
2. Use functional components with hooks
3. Keep components small and focused
4. Add error handling
5. Update this documentation

---

**Status**: ✅ Production Ready

**Last Updated**: 2024

**Maintainer**: ARCHITECH Team
