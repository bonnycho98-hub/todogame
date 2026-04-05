from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers import npcs, needs, quests, subtasks, rewards, dashboard

app = FastAPI(title="Love Quest")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(npcs.router)
app.include_router(needs.router)
app.include_router(quests.router)
app.include_router(subtasks.router)
app.include_router(rewards.router)
app.include_router(dashboard.router)


@app.get("/")
def root():
    return FileResponse("static/index.html")
