from fastapi import FastAPI
import uvicorn
from config import Settings

settings = Settings()
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Ceci est l'API IA de la solution!"}   

def main():
    uvicorn.run(app, host="0.0.0.0", port=5005)
if __name__ == "__main__":    main()