# 🌊⚓ AquaPath AI: Intelligent Maritime Routing System

AquaPath AI is an advanced, terminal-based Python application designed to optimize global maritime shipping routes. By combining **Graph-Based Pathfinding**, **Live API Integration**, and **Machine Learning**, the system calculates the safest and most efficient path between global ports based on physical distance, live weather conditions, and historical traffic density.


## Installation & Setup

## Installation and Setup

### Prerequisites

Install the following:

- Python 3.10 or later
- Node.js and npm
- Git

### 1. Clone the repository

```bash
git clone https://github.com/AquaPathAI/aquapath-ai-gui.git
cd aquapath-ai-gui
```

### 2. Create a Python virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install Flask requests
```

### 4. Install npm dependencies

```bash
npm install
```

### 5. Compile the TypeScript code

```bash
npx tsc
```

This compiles `src/script.ts` into `static/dist/script.js`, which is loaded by the Flask template.

## Running the Application

Start the Flask development server:

```bash
python app.py
```

Open the application in a browser