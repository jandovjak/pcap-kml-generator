# PCAPNG to KML Converter

This Python script converts packet capture files in the PCAPNG format into Keyhole Markup Language (KML) files. The KML file can be visualized using mapping software such as [Google My Maps](https://www.google.com/maps/d/) or [Google Earth](https://earth.google.com/web/), displaying the network traffic in a geographical context.

## Installation

1. This script requires Python 3.
2. Install the required dependencies from requirements.txt using pip:
    ```bash
    pip3 install -r requirements.txt
    ```

## Usage

If you want to use "terminal" version, then run the following script from the command line:

```bash
python3 kml.py dump.pcapng output_file.kml
```

There is also an API version in FastAPI. To start API, run the following script from the command line:
```bash
python3 uvicorn api:app --reload
```

Endpoint is running on http://127.0.0.1:8000 and API for generating KML is on http://127.0.0.1:8000/generate. Swagger UI is available on http://127.0.0.1:8000/docs/.
