"""FastAPI example with BugStack error capture."""

from fastapi import FastAPI

import bugstack
from bugstack.integrations.fastapi import FastAPIMiddleware

bugstack.init(
    api_key="bs_live_your_api_key_here",
    auto_fix=True,
)

app = FastAPI()
app.add_middleware(FastAPIMiddleware)


@app.get("/")
async def root():
    return {"message": "Hello, World!"}


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    if user_id == 0:
        raise ValueError("User ID cannot be zero")
    return {"user_id": user_id, "name": "Alice"}


# Run: uvicorn main:app --reload
