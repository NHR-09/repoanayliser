# ARCHITECH API Documentation

## Base URL
`http://localhost:8000`

## Endpoints

### 1. Analyze Repository
**POST** `/analyze`

Initiates repository analysis (async job).

**Request:**
```json
{
  "repo_url": "https://github.com/user/repo"
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "processing"
}
```

### 2. Check Job Status
**GET** `/status/{job_id}`

**Response:**
```json
{
  "status": "completed|processing|failed",
  "result": {...}
}
```

### 3. Get Architecture Explanation
**GET** `/architecture`

Returns AI-generated architecture explanation with detected patterns.

**Response:**
```json
{
  "explanation": "...",
  "evidence_files": ["file1.py", "file2.js"],
  "detected_patterns": {...}
}
```

### 4. Get Detected Patterns
**GET** `/patterns`

**Response:**
```json
{
  "layered": {
    "detected": true,
    "layers": ["presentation", "business", "data"],
    "confidence": 0.8
  },
  "mvc": {...},
  "hexagonal": {...}
}
```

### 5. Get Coupling Analysis
**GET** `/coupling`

**Response:**
```json
{
  "high_coupling": [
    {"file": "service.py", "fan_in": 8, "fan_out": 12}
  ],
  "cycles": [["a.py", "b.py", "a.py"]],
  "metrics": {
    "total_files": 50,
    "total_dependencies": 120,
    "avg_coupling": 2.4
  }
}
```

### 6. Analyze Change Impact
**POST** `/impact`

**Request:**
```json
{
  "file_path": "/path/to/file.py"
}
```

**Response:**
```json
{
  "file": "/path/to/file.py",
  "impact_explanation": "...",
  "affected_files": ["file1.py", "file2.py"],
  "blast_radius": ["file1.py", "file2.py", "file3.py"],
  "risk_level": "high|medium|low",
  "evidence": ["file1.py"]
}
```

### 7. Get File Dependencies
**GET** `/dependencies/{file_path}`

**Response:**
```json
{
  "file": "/path/to/file.py",
  "dependencies": ["module1", "module2"]
}
```

### 8. Get Blast Radius
**GET** `/blast-radius/{file_path}`

**Response:**
```json
{
  "file": "/path/to/file.py",
  "affected_files": ["file1.py", "file2.py"],
  "count": 2
}
```

## Error Responses
```json
{
  "error": "Error message"
}
```
