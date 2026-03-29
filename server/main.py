from fastapi import FastAPI
from os import environ as env

app = FastAPI()

@app.get("/")
def index():
    secret = env.get("MY_VARIABLE", "not_set")
    return {"details": f"Hello, World! Secret = {secret}"}