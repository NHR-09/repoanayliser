# ARCHITECH Frontend

React-based frontend for the ARCHITECH Architectural Recovery Platform.

## Features

- 🔍 **Repository Analysis** - Analyze GitHub repositories
- 🎯 **Pattern Detection** - View detected architectural patterns (Layered, MVC, Hexagonal)
- 📊 **Coupling Analysis** - Visualize coupling metrics and circular dependencies
- 💥 **Impact Analysis** - Predict blast radius of code changes
- 🏗️ **Architecture View** - Multi-level explanations (Macro/Meso/Micro)
- 📈 **Dependency Graph** - Interactive D3.js visualization

## Prerequisites

- Node.js 16+ and npm
- Backend server running on `http://localhost:8000`

## Installation

```bash
cd frontend
npm install
```

## Running the App

```bash
npm start
```

The app will open at `http://localhost:3000`

## Usage

1. **Analyze Tab**: Enter a GitHub repository URL and click "Analyze"
2. **Patterns Tab**: View detected architectural patterns with confidence scores
3. **Coupling Tab**: See high coupling files and circular dependencies
4. **Impact Tab**: Enter a file path to see its blast radius
5. **Architecture Tab**: Read AI-generated architecture explanations
6. **Graph Tab**: Visualize file dependencies interactively

## Tech Stack

- **React 18** - UI framework
- **D3.js** - Graph visualization
- **Axios** - HTTP client
- **Inline CSS** - Minimal styling (no external CSS frameworks)

## API Integration

The frontend connects to the FastAPI backend at `http://localhost:8000`:

- `POST /analyze` - Start repository analysis
- `GET /patterns` - Get detected patterns
- `GET /coupling` - Get coupling metrics
- `POST /impact` - Analyze change impact
- `GET /architecture` - Get architecture explanation
- `GET /debug/files` - Get file list for graph

## Build for Production

```bash
npm run build
```

Creates optimized production build in `build/` folder.

## Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── AnalyzeRepo.js
│   │   ├── PatternDetection.js
│   │   ├── CouplingAnalysis.js
│   │   ├── ImpactAnalysis.js
│   │   ├── ArchitectureView.js
│   │   └── DependencyGraph.js
│   ├── services/
│   │   └── api.js
│   ├── App.js
│   └── index.js
└── package.json
```

## Notes

- Ensure backend is running before starting frontend
- CORS is enabled on backend for `localhost:3000`
- Graph visualization works best with <100 files
- All styling is inline for minimal dependencies

---

**Status**: ✅ Production Ready
