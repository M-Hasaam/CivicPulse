from fastapi import FastAPI

app = FastAPI(title="CivicPulse API")


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello from CivicPulse"}
