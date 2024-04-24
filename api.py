from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import StreamingResponse
from io import BytesIO
from kml import generate_kml
from typing import Annotated
import tempfile
import os

app = FastAPI()


@app.post("/generate")
async def generate(file: UploadFile,
                   output_filename: Annotated[str, Form()],
                   home_longtitude: Annotated[float, Form()],
                   home_latitude: Annotated[float, Form()]):
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(await file.read())
        temp_file_name = temp_file.name
    content = generate_kml(temp_file_name, home_longtitude, home_latitude)
    os.remove(temp_file_name)
    byte_string = content.encode("utf-8")
    byte_stream = BytesIO(byte_string)
    headers = {
        'Content-Disposition': f'attachment; filename="{output_filename}"'
    }
    return StreamingResponse(byte_stream,
                             media_type="text/plain",
                             headers=headers)
