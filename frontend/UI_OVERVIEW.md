# ARCHITECH Frontend - Visual Overview

## 🎨 User Interface

### Main Layout

```
┌─────────────────────────────────────────────────────┐
│  🏗️ ARCHITECH                                       │
│  Architectural Recovery & Semantic Synthesis        │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│ [Analyze] [Patterns] [Coupling] [Impact] [Arch] [Graph] │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│                                                     │
│              CONTENT AREA                           │
│         (Tab-specific components)                   │
│                                                     │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  Backend: localhost:8000 | Neo4j: localhost:7474   │
└─────────────────────────────────────────────────────┘
```

## 📱 Tab Components

### 1. Analyze Tab
```
┌──────────────────────────────────────┐
│  Analyze Repository                  │
├──────────────────────────────────────┤
│  [Enter GitHub repository URL...   ] │
│  [Analyze Button]                    │
│                                      │
│  Job ID: abc-123-def                 │
│  Status: processing...               │
└──────────────────────────────────────┘
```

**Features:**
- Repository URL input
- Real-time status updates
- Job ID tracking
- Auto-refresh on completion

### 2. Patterns Tab
```
┌──────────────────────────────────────┐
│  Detected Patterns                   │
├──────────────────────────────────────┤
│  LAYERED                             │
│  ✓ Detected | Confidence: 85%       │
│  Layers: presentation, business, data│
├──────────────────────────────────────┤
│  MVC                                 │
│  ✓ Detected | Confidence: 90%       │
│  Controllers: 12 | Models: 8         │
├──────────────────────────────────────┤
│  HEXAGONAL                           │
│  Not detected                        │
└──────────────────────────────────────┘
```

**Features:**
- Pattern detection status
- Confidence scores
- Pattern-specific metrics
- Color-coded indicators

### 3. Coupling Tab
```
┌──────────────────────────────────────┐
│  Coupling Analysis                   │
├──────────────────────────────────────┤
│  Metrics                             │
│  Total Files: 50                     │
│  Average Coupling: 2.4               │
├──────────────────────────────────────┤
│  High Coupling Files                 │
│  service.py | Fan-in: 8 | Fan-out: 12│
│  utils.py   | Fan-in: 6 | Fan-out: 9 │
├──────────────────────────────────────┤
│  Circular Dependencies               │
│  a.py → b.py → c.py → a.py          │
└──────────────────────────────────────┘
```

**Features:**
- Overall metrics
- High coupling identification
- Circular dependency detection
- Visual indicators

### 4. Impact Tab
```
┌──────────────────────────────────────┐
│  Change Impact Analysis              │
├──────────────────────────────────────┤
│  [Enter file path...              ]  │
│  [Analyze Impact]                    │
├──────────────────────────────────────┤
│  Impact Results                      │
│  File: src/auth.py                   │
│  Risk Level: HIGH                    │
│                                      │
│  Affected Files (3)                  │
│  • login.py                          │
│  • middleware.py                     │
│  • routes.py                         │
│                                      │
│  Explanation                         │
│  Changing auth.py affects...         │
└──────────────────────────────────────┘
```

**Features:**
- File path input
- Risk level classification
- Blast radius visualization
- AI-generated explanation

### 5. Architecture Tab
```
┌──────────────────────────────────────┐
│  Architecture Explanation            │
├──────────────────────────────────────┤
│  Macro Level (System Overview)       │
│  The system follows a layered...     │
├──────────────────────────────────────┤
│  Meso Level (Module Responsibilities)│
│  The presentation layer handles...   │
├──────────────────────────────────────┤
│  Micro Level (File/Function Details) │
│  The auth.py file contains...        │
├──────────────────────────────────────┤
│  Evidence                            │
│  • src/models/user.py                │
│    Contains user authentication...   │
└──────────────────────────────────────┘
```

**Features:**
- Multi-level explanations
- Evidence citations
- Structured information
- Scrollable content

### 6. Graph Tab
```
┌──────────────────────────────────────┐
│  Dependency Graph                    │
│  Files in repository: 25             │
├──────────────────────────────────────┤
│                                      │
│     ●────●                           │
│    /│\   │\                          │
│   ● ● ●  ● ●                         │
│    \│/   │/                          │
│     ●────●                           │
│                                      │
│  (Interactive D3.js Force Graph)     │
│  Drag nodes to rearrange             │
└──────────────────────────────────────┘
```

**Features:**
- Interactive force-directed graph
- Drag-and-drop nodes
- File name labels
- Real-time physics simulation

## 🎨 Color Scheme

```
Primary:   #667eea (Purple)
Secondary: #764ba2 (Dark Purple)
Success:   #28a745 (Green)
Warning:   #ffc107 (Yellow)
Danger:    #dc3545 (Red)
Info:      #007bff (Blue)
Light:     #f0f2f5 (Light Gray)
Dark:      #333333 (Dark Gray)
```

## 🔄 User Flow

```
1. User lands on Analyze tab
   ↓
2. Enters GitHub repository URL
   ↓
3. Clicks "Analyze" button
   ↓
4. Backend processes repository
   ↓
5. Status updates in real-time
   ↓
6. Analysis completes
   ↓
7. User explores other tabs:
   - Patterns: View detected patterns
   - Coupling: Check coupling metrics
   - Impact: Analyze specific files
   - Architecture: Read explanations
   - Graph: Visualize dependencies
```

## 📊 Component Hierarchy

```
App
├── Header
├── Navigation (Tabs)
└── Main Content
    ├── AnalyzeRepo
    ├── PatternDetection
    ├── CouplingAnalysis
    ├── ImpactAnalysis
    ├── ArchitectureView
    └── DependencyGraph
```

## 🔌 API Integration Flow

```
Frontend Component
      ↓
   api.js (Axios)
      ↓
   HTTP Request
      ↓
Backend (FastAPI)
      ↓
   Response (JSON)
      ↓
   Component State
      ↓
   UI Update
```

## 📱 Responsive Design

- **Desktop**: Full layout with sidebar navigation
- **Tablet**: Stacked layout with collapsible sections
- **Mobile**: Single column, touch-optimized

## ⚡ Performance Features

- **Lazy Loading**: Components load on demand
- **Memoization**: Prevent unnecessary re-renders
- **Debouncing**: API calls are debounced
- **Caching**: Results cached in component state
- **Optimized Rendering**: D3.js graph limited to 100 nodes

## 🎯 Key Interactions

1. **Tab Navigation**: Click tabs to switch views
2. **Form Submission**: Enter data and click buttons
3. **Real-time Updates**: Status polling every 2 seconds
4. **Graph Interaction**: Drag nodes, zoom, pan
5. **Scrolling**: Long content areas are scrollable

## 🚀 Future UI Enhancements

- [ ] Dark mode toggle
- [ ] Export functionality (PDF/JSON)
- [ ] Advanced filtering options
- [ ] Search functionality
- [ ] Comparison view (multiple repos)
- [ ] Real-time WebSocket updates
- [ ] Customizable dashboards
- [ ] Mobile app version

---

**Design Philosophy**: Clean, minimal, functional
**Framework**: React 18 with Hooks
**Styling**: Inline CSS + App.css
**Visualization**: D3.js v7
