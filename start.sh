#!/bin/bash

# Start FastAPI on port 8000
uvicorn app.app_fastapi:app --host 0.0.0.0 --port 8000 &

# Start Streamlit on the port Railway provides ($PORT)
streamlit run app/streamlit_app.py --server.port $PORT --server.address 0.0.0.0
