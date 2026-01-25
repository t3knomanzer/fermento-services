# TNM Validation API

Author: Ruben Henares  

## Technologies Used

- Python 3.8+
- FastAPI
- SQLAlchemy for ORM
- SQLite as a database
- Pydantic for data validation
- aiofiles for asynchronous file operations
- Docker

## Installation

1. **Create a virtual environment** (optional but recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
   ```

2. **Install the required packages**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Start the FastAPI application**:
   ```bash
   uvicorn src.main:app --reload
   ```

2. **Access the documentation**:
   Open your browser and navigate to [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the interactive API documentation provided by Swagger UI.

3. **Use the Health Check endpoint**:
   You can check if the service is running by navigating to [http://127.0.0.1:8000/healthcheck](http://127.0.0.1:8000/healthcheck).

## Logging
Logging is printed to the console (info) as to a file (debug).
   