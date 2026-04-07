#!/bin/bash

# 1. Start FastAPI in the background
# We use 127.0.0.1 for internal communication
uvicorn app.app_fastapi:app --host 127.0.0.1 --port 8000 &

# 2. Wait a few seconds for FastAPI to actually boot up
sleep 5

# 3. Start Streamlit (This is the one Railway "sees")
streamlit run app/app_streamlit.py --server.port $PORT --server.address 0.0.0.0

