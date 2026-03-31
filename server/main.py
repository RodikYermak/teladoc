# from fastapi import FastAPI

# from app.routes.issues import router as issues_router
# from app.routes.auth import router as auth_router
# from app.routes.health import router as health_router

# from app.middleware.timer import timing_middleware
# from fastapi.middleware.cors import CORSMiddleware

# app = FastAPI(
#     title="Issue Tracker API",
#     version="0.1.0",
#     description="A mini production-style API built with FastAPI",
# )

# app.middleware("http")(timing_middleware)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# app.include_router(auth_router)
# app.include_router(issues_router)
# app.include_router(health_router)


# # https://teladoc-poug.onrender.com/api/v1/issues/


import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List


class Fruit(BaseModel):
    name: str


class Fruits(BaseModel):
    fruits: List[Fruit]


app = FastAPI(debug=True)

origins = [
    "http://localhost:5173",
    # Add more origins here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

memory_db = {"fruits": []}

@app.get("/fruits", response_model=Fruits)
def get_fruits():
    return Fruits(fruits=memory_db["fruits"])


@app.post("/fruits")
def add_fruit(fruit: Fruit):
    memory_db["fruits"].append(fruit)
    return fruit


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)