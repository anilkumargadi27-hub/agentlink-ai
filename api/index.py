from fastapi import FastAPI

app = FastAPI()

@app.get("/health/ready")
@app.get("/health")
@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "message": "Python Vercel function is active!"}
