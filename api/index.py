from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()


@app.get("/")
async def home():
    return FileResponse("static/index.html")


app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)