import sys
import os
import streamlit as st

st.write(f"**Python Executable:** {sys.executable}")
st.write(f"**Python Path:** {sys.path}")

try:
    import plotly
    st.success(f"Plotly found at: {plotly.__file__}")
except ImportError as e:
    st.error(f"Plotly NOT found. Error: {e}")