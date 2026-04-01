import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import SimulationRequest, SimulationResponse
from engine import optimizer

app = FastAPI(title="ZüriWealth Optimizer API", version="1.0.0")

# --- CORS MIDDLEWARE REQUIRED FOR FRONTEND GENERATORS (LOVABLE AI) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows any frontend URL to hit your API. 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

zh_config = {}

@app.on_event("startup")
async def load_config():
    global zh_config
    try:
        with open("config/zh_tax_2024.json", "r") as f:
            zh_config = json.load(f)
        print("Zurich 2024 Tax Configuration loaded into memory.")
    except Exception as e:
        print(f"Failed to load tax config: {e}")

@app.post("/api/v1/simulate", response_model=SimulationResponse)
async def simulate_wealth(request: SimulationRequest):
    try:
        response = optimizer.run_optimization(request, zh_config)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))