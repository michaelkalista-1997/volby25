"""Spouštěcí skript pro webovou aplikaci."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("webapp.app:app", host="0.0.0.0", port=8000, reload=False)
