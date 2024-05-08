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
                   home_latitude: Annotated[float, Form()])\
                    -> StreamingResponse:
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(await file.read())
        temp_file_name: str = temp_file.name
    content: str = generate_kml(temp_file_name, home_longtitude, home_latitude)
    os.remove(temp_file_name)
    byte_string: bytes = content.encode("utf-8")
    byte_stream: BytesIO = BytesIO(byte_string)
    headers: dict[str, str] = {
        'Content-Disposition': f'attachment; filename="{output_filename}"'
    }
    return StreamingResponse(byte_stream,
                             media_type="text/plain",
                             headers=headers)
