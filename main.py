import configparser
from fastapi import FastAPI, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from loguru import logger
from pathlib import Path
from shutil import make_archive
from time import gmtime, strftime

config = configparser.ConfigParser()
config_path = Path("./config.ini")
config.read(config_path)

base_dir = Path(config["Settings"]["BaseDir"])

app = FastAPI()

templates = Jinja2Templates(".")


@app.get("/zip/{filename:path}")
def zipHandler(filename: str):
    cache_path = Path("./cache")
    cache_path.mkdir(exist_ok=True)
    dir_path = Path(filename)
    output_path = cache_path / dir_path.name
    make_archive(output_path, "zip", base_dir / dir_path)
    return FileResponse(
        cache_path / (dir_path.name + ".zip"),
        filename=f"{dir_path.name}.zip",
        media_type="application/octet-stream",
    )


@logger.catch
@app.get("/{filename:path}")
def file(filename: str, request: Request):
    file_path = base_dir / filename
    if not file_path.exists():
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})
    if file_path.is_dir():
        paths = [
            {
                "path": i.name,
                "is_file": i.is_file(),
                "href": i.relative_to(base_dir),
                "size": f"{i.stat().st_size / 1e6 :.2f} MB"
                if i.is_file()
                else "",  # f"{sum([f.stat().st_size for f in i.glob('**/*') if f.is_file()]) / 1e6:.2} MB",
                "mtime": i.stat().st_mtime,
            }
            for i in file_path.iterdir()
        ]
        paths.sort(key=lambda x: x["mtime"])
        for i in paths:
            i["mtime"] = strftime("%d %b %y %H:%M:%S UTC", gmtime(i["mtime"]))
        resp = {
            "request": request,
            "title": str(file_path.relative_to(base_dir)),
            "paths": paths,
            "parent": file_path.relative_to(base_dir).parent,
        }

        return templates.TemplateResponse("template.html", resp)
    else:
        return FileResponse(file_path)
