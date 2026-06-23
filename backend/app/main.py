from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.weather import router as weather_router

app = FastAPI()

app.include_router(weather_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["http://localhost:5173"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)

@app.get("/")
def root():
    return {
        "message": "Hiking Weather API"
    } 

@app.get("/health")
def health():
    return {
        "status": "OK"
    }
    

# Step 11 Start work on the frontend