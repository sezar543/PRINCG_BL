import os
from pathlib import Path
from enum import Enum # Correctly used for PartCondition
import csv

from typing import List, Dict, Any, Optional, Literal
from typing_extensions import Annotated 
from fastapi import FastAPI, HTTPException, Query # Query is imported here
from pydantic import BaseModel, Field
from requests_oauthlib import OAuth1Session
from oauthlib.oauth1 import Client
import requests
from datetime import datetime
from fastapi.responses import HTMLResponse

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dotenv import load_dotenv
# --- Configuration and Setup ---

import json
import textwrap
import sys
import math
from plotly.offline import plot

# Define the path to the project root where .env is located
# uncomment for local running
# ENV_PATH = Path(__file__).resolve().parent.parent / ".env" 
# Load environment variables from the explicit path
# load_dotenv(dotenv_path=ENV_PATH)

load_dotenv()

BRICKLINK_BASE_URL = "https://api.bricklink.com/api/store/v1"

# Load credentials from environment variables
# CONSUMER_KEY = os.getenv("BRICKLINK_CONSUMER_KEY")
# CONSUMER_SECRET = os.getenv("BRICKLINK_CONSUMER_SECRET")
# ACCESS_TOKEN = os.getenv("BRICKLINK_TOKEN_VALUE")
# TOKEN_SECRET = os.getenv("BRICKLINK_TOKEN_SECRET")

# CONSUMER_KEY = os.environ.get("BRICKLINK_CONSUMER_KEY")
# CONSUMER_SECRET = os.environ.get("BRICKLINK_CONSUMER_SECRET")
# ACCESS_TOKEN = os.environ.get("BRICKLINK_TOKEN_VALUE")
# TOKEN_SECRET = os.environ.get("BRICKLINK_TOKEN_SECRET")

BRICKLINK_CONSUMER_KEY = "F77F41502C8041E49EC42529EA26FAD7"
BRICKLINK_CONSUMER_SECRET = "E214EF5F097441F0949514A76DE5749E"
BRICKLINK_TOKEN_VALUE = "D8BEDCA603844337BA58181B5FCF644F"
BRICKLINK_TOKEN_SECRET = "192A31C402C84AABB37EB1CD886707C2"


# CONSUMER_KEY = "F77F41502C8041E49EC42529EA26FAD7" # Replace with your Consumer Key
# CONSUMER_SECRET = "E214EF5F097441F0949514A76DE5749E"           # Replace with your Consumer Secret

# IP:  ....201  Breka
ACCESS_TOKEN = "D8BEDCA603844337BA58181B5FCF644F" # Replace with your Access Token
TOKEN_SECRET = "192A31C402C84AABB37EB1CD886707C2" # Replace with your Token Secret


# # IP: Home 	154.20.185.194
# ACCESS_TOKEN = "C251EE63370A4B7F81DD21DE45176719"
# TOKEN_SECRET = "D1517DCF204C41D5815629BE350C168D"

# IP: 50.64.16.78 Artistry
# ACCESS_TOKEN = "E584C64AF7C547FBA82B7D730624C274"
# TOKEN_SECRET = "17B5ED145DF84EB898CED907A0F07DA0"

#IP parents    135.12.196.68
# ACCESS_TOKEN = "D821AF251A794843AAAC9B7123BB7B09"
# TOKEN_SECRET = "F117B1921E344DB2AF74C26DEEDB1CA7"

#IP     184.71.139.178 StarBucks broadway
# ACCESS_TOKEN = "C43E5D5FD4244E21A3B35EFBD1E6D523"
# TOKEN_SECRET = "B3285CDD9D5D4992BAFDD90784DB7C3D"

# if not all([CONSUMER_KEY, CONSUMER_SECRET, TOKEN_VALUE, TOKEN_SECRET]):
#     raise ValueError("Missing one or more BrickLink API credentials in .env file.")

# Temporary debug: Print all available environment keys to see what Railway IS providing
print(f"DEBUG: Available Env Keys: {list(os.environ.keys())}")

# DEBUGGING PRINTS (Check your Railway Logs for these)
print(f"DEBUG: CONSUMER_KEY present: {bool(CONSUMER_KEY)}")
print(f"DEBUG: TOKEN_VALUE present: {bool(TOKEN_VALUE)}")

if not all([CONSUMER_KEY, CONSUMER_SECRET, TOKEN_VALUE, TOKEN_SECRET]):
    # This prints exactly which one is missing to your logs
    missing = [k for k, v in {
        "KEY": CONSUMER_KEY, 
        "C_SECRET": CONSUMER_SECRET, 
        "TOKEN": TOKEN_VALUE, 
        "T_SECRET": TOKEN_SECRET
    }.items() if not v]
    print(f"CRITICAL ERROR: Missing variables: {missing}")
    # Keep your raise here so the app doesn't try to run with broken auth
    raise ValueError(f"Missing BrickLink credentials: {missing}")


# Define the directory where inventory files will be saved
INVENTORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'inventories')

# Define the directory where statistics files will be saved (adjacent to the app folder)
STATISTICS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'statistics')

# Define the new directory for set-specific price guide reports
PRICE_GUIDE_SET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'price_guide_set')

# 2. Logic Fix: Map condition codes to full words
condition_map = {'N': 'new', 'U': 'used'}

# Initialize FastAPI app
app = FastAPI(
    title="BrickLink Inventory API",
    description="Fetches set inventory data using OAuth 1.0.",
)

# # Updated model for the Projected Sale and part-out value result
# class ProjectedSaleResult(BaseModel):
#     set_no: str
#     condition: Literal['N', 'U']
#     projected_sale: float
#     part_out_value: float 
#     total_parts_processed: int
#     report_file: str
#     message: Optional[str] = None


# Pydantic Model MUST match the requested CSV fields
class Part(BaseModel):
    item_no: str
    item_type: str 
    color_id: int
    quantity: int
    match_id: str = ""      
    is_alternate: bool
    is_counterpart: bool  

# Model for a single fetched price guide statistic (for internal use)
class PriceStat(BaseModel):
    avg_price: float
    qty_avg_price: float
    unit_quantity: int
    total_quantity: int

# Model for the final CSV row combining all four required statistics
class ItemPriceStats(BaseModel):
    timestamp: str
    item_no: str
    color_id: int
    
    # New Condition, Stock Guide (Currently for Sale)
    new_stock_avg_price: float
    new_stock_qty_avg_price: float
    new_stock_unit_quantity: int
    new_stock_total_quantity: int
    
    # Used Condition, Stock Guide (Currently for Sale)
    used_stock_avg_price: float
    used_stock_qty_avg_price: float
    used_stock_unit_quantity: int
    used_stock_total_quantity: int
    
    # New Condition, Sold Guide (Last 6 Months Sales)
    new_sold_avg_price: float
    new_sold_qty_avg_price: float
    new_sold_total_quantity: int
    new_sold_total_quantity: int
    
    # Used Condition, Sold Guide (Last 6 Months Sales)
    used_sold_avg_price: float
    used_sold_qty_avg_price: float
    used_sold_total_quantity: int
    used_sold_total_quantity: int

class ProjectionRequest(BaseModel):
    set_number: str
    buy_price: float

class MonthlyProjection(BaseModel):
    month: int
    projected_sale: float
    roi_percent: str

class ProjectedSaleResult(BaseModel):
    set_no: str
    condition: str
    part_out_value: float
    projections: List[MonthlyProjection]
    total_parts_processed: int
    report_file: str
    message: Optional[str] = None

# class ProjectedSaleResult(BaseModel):
#     set_no: str
#     condition: str
#     # Renamed field to match your request
#     projected_sale_after_six_months: float = Field(..., alias="projected_sale after six month")
#     part_out_value: float
#     total_parts_processed: int
#     report_file: str
#     projections: List[MonthlyProjection]
#     message: Optional[str] = None

    class Config:
        # This allows the alias to be used in the JSON output
        populate_by_name = True
        serialization_alias_kind = 'alias'
     
# --- 2. CORE OAUTH FUNCTIONALITY ---

def get_oauth_session() -> OAuth1Session:
    """Initializes and returns the OAuth1Session object."""
    try:
        oauth = OAuth1Session(
            CONSUMER_KEY,
            client_secret=CONSUMER_SECRET,
            resource_owner_key=ACCESS_TOKEN,
            resource_owner_secret=TOKEN_SECRET,
            signature_method='HMAC-SHA1'
        )
        return oauth
    except Exception as e:
        # In a real app, log this error securely
        print(f"Failed to initialize OAuth session: {e}")
        # Raise an exception that FastAPI can handle
        raise HTTPException(status_code=500, detail="Internal server configuration error (OAuth init).")

    
    
def get_set_inventory(set_no: str) -> List[Part]:
    """
    Fetches the part inventory for a given set number. 
    Checks local CSV cache first before calling BrickLink API.
    """
    os.makedirs(INVENTORY_DIR, exist_ok=True)
    file_path = os.path.join(INVENTORY_DIR, f"{set_no}.csv")

    # --- 1. Check if local cache exists ---
    if os.path.exists(file_path):
        print(f"Loading inventory for set {set_no} from local cache: {file_path}")
        try:
            import pandas as pd
            import numpy as np
            
            # Use dtype argument to force item_no and match_id to be strings
            # and keep_default_na=False to prevent empty strings from becoming NaN
            df = pd.read_csv(
                file_path, 
                dtype={'item_no': str, 'match_id': str},
                keep_default_na=False
            )
            
            # Replace any actual remaining NaN with empty strings just in case
            df = df.replace(np.nan, '', regex=True)
            
            cached_data = df.to_dict(orient='records')
            return [Part(**data) for data in cached_data]
            
        except Exception as e:
            print(f"Error reading local cache for {set_no}, falling back to API: {e}")

    # --- 2. If not cached, proceed to API Request ---
    oauth = get_oauth_session()
    url = f"{BRICKLINK_BASE_URL}/items/SET/{set_no}/subsets"
    
    print(f"\n--- BrickLink API Request ---")
    print(f"Target URL: {url}")
    
    try:
        response = oauth.get(url)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.HTTPError as e:
        # ... (error handling remains the same)
        print(f"BrickLink API returned HTTP Error: {e.response.status_code}")
        try:
            error_data = e.response.json()
            error_message = error_data.get('meta', {}).get('description', 'Unknown API Error')
        except:
            error_message = f"HTTP {e.response.status_code} Error. Cannot parse error message."
        if e.response.status_code == 401:
             raise HTTPException(status_code=401, detail=f"Authentication Failed (401): {error_message}. Check TOKEN_IP_MISMATCHED issue.")
        raise HTTPException(status_code=502, detail=f"BrickLink API Error: {error_message}")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        raise HTTPException(status_code=503, detail="Could not connect to BrickLink API service.")

    # --- 3. Process the API data ---
    raw_inventory_groups = []
    if isinstance(data, dict) and 'data' in data:
        raw_inventory_groups = data['data']
    elif isinstance(data, list):
        raw_inventory_groups = data
    else:
        meta_description = data.get('meta', {}).get('description', 'No detailed description.')
        raise HTTPException(status_code=500, detail=f"Unexpected API response structure. Meta: {meta_description}")

    if not isinstance(raw_inventory_groups, list):
        raise HTTPException(status_code=500, detail="API 'data' content is not a list of inventory groups.")

    processed_parts_dicts: List[Dict[str, Any]] = []
    
    for item_group in raw_inventory_groups:
        for item in item_group.get('entries', []):
            item_data = item.get('item')
            if item_data is None: continue 

            part_data = {
                'item_no': str(item_data.get('no', '')), # Force string conversion        
                'item_type': item_data.get('type', 'PART'),
                'color_id': item.get('color_id', 0),
                'quantity': item.get('quantity', 0),
                'is_alternate': item.get('is_alternate', False),
                'is_counterpart': item.get('is_counterpart', False), 
                'match_id': '',                                    
            }
            processed_parts_dicts.append(part_data)

    # --- 4. Save to local cache ---
    csv_headers = ['item_no', 'item_type', 'color_id', 'quantity', 'match_id', 'is_alternate', 'is_counterpart']
    try:
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_headers)
            writer.writeheader()
            writer.writerows(processed_parts_dicts)
        print(f"Successfully saved inventory for set {set_no} to {file_path}")
    except Exception as e:
        print(f"Error saving file: {e}")
        
    processed_parts_models = [Part(**data) for data in processed_parts_dicts]
    return processed_parts_models

# --- 5. PRICE GUIDE LOGIC (New with Cache Check) ---

def _get_monthly_stats_filepath() -> str:
    """Returns the full file path for the current month's statistics CSV."""
    file_name = datetime.now().strftime("%y_%m_stats.csv")
    return os.path.join(STATISTICS_DIR, file_name)


def _check_if_stats_exist(item_no: str, color_id: int) -> Optional[ItemPriceStats]:
    """
    Checks the current month's CSV file for an existing entry for the given item_no and color_id.
    NOTE: item_type check REMOVED as requested.
    Returns the ItemPriceStats object if found, otherwise None.
    """
    file_path = _get_monthly_stats_filepath()
    
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            color_id_str = str(color_id)
            
            for row in reader:
                # Check for item_no and color_id only
                if row.get('item_no') == item_no and row.get('color_id') == color_id_str:
                    print(f"Found existing stats for {item_no}/{color_id} in CSV. Skipping API calls.")
                    
                    try:
                        # Convert necessary fields back to their correct types (float/int)
                        data = {
                            k: (float(v) if 'price' in k else int(v) if 'quantity' in k else v)
                            for k, v in row.items()
                        }
                        # The ItemPriceStats model no longer includes item_type, so we pass only existing fields
                        return ItemPriceStats(**data)
                    except ValueError as ve:
                        print(f"Error converting types from CSV row: {ve}. Row skipped: {row}")
                        continue
                        
            return None

    except Exception as e:
        print(f"Error reading or parsing CSV file {file_path}: {e}")
        return None

# --- 5. PRICE GUIDE LOGIC (New) ---

def _fetch_single_price_stat(
    oauth: OAuth1Session, 
    item_no: str, 
    item_type: str, # NEW REQUIRED ARGUMENT
    color_id: int, 
    new_or_used: str, 
    guide_type: str
) -> PriceStat:
    """
    Fetches a single price statistic (e.g., Used/Sold) from the BrickLink API.
    Uses the provided item_type (PART, MINIFIG, etc.).
    """
    
    # Use the explicitly provided item_type
    url = (
        f"{BRICKLINK_BASE_URL}/items/{item_type}/{item_no}/price"
        f"?color_id={color_id}"
        f"&new_or_used={new_or_used}"
        f"&guide_type={guide_type}"
    )
    
    print(f"--- Fetching Price Stat for {item_no} (Type: {item_type}): Guide={guide_type}, Cond={new_or_used} ---")
    
    try:
        response = oauth.get(url)
        response.raise_for_status()
        data = response.json()
        
        price_guide_data = data.get('data')
        if not price_guide_data:
            print(f"--- DEBUG: No price guide data found for item {item_no} (Type: {item_type}) ---")
            return PriceStat(avg_price=0.0, qty_avg_price=0.0, unit_quantity=0, total_quantity=0)

        # Convert numbers from strings (Fixed Point Number)
        return PriceStat(
            avg_price=float(price_guide_data.get('avg_price', 0.0)),
            qty_avg_price=float(price_guide_data.get('qty_avg_price', 0.0)),
            unit_quantity=int(price_guide_data.get('unit_quantity', 0)),
            total_quantity=int(price_guide_data.get('total_quantity', 0)),
        )

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error fetching price stat ({guide_type}/{new_or_used}) for {item_no} (Type: {item_type}): {e.response.status_code}. Using zeroed stats.")
        return PriceStat(avg_price=0.0, qty_avg_price=0.0, unit_quantity=0, total_quantity=0)
    except Exception as e:
        print(f"Unexpected error fetching price stat ({guide_type}/{new_or_used}) for {item_no}: {e}. Using zeroed stats.")
        return PriceStat(avg_price=0.0, qty_avg_price=0.0, unit_quantity=0, total_quantity=0)


def get_and_save_price_stats(item_no: str, item_type: str, color_id: int) -> ItemPriceStats:
    """
    Checks local CSV cache (using item_type), fetches all four required price statistics if not found, 
    and saves them as one row in a CSV file.
    """

    # Define the 4 calls needed (Stock N/U, Sold N/U)
    # CRITICAL: We add 'country_code=US' or 'region=US' if that's what your manual call used.
    # Also ensuring currency_code=USD is explicitly handled by BL based on your account settings.
    
    # 1. CHECK CACHE FIRST
    cached_stats = _check_if_stats_exist(item_no, color_id)
    if cached_stats:
        return cached_stats

    # 2. DEFINE INTERNAL FETCH LOGIC
    # We use the session object directly to avoid the 'object is not callable' error
    session = get_oauth_session()
    base_url = f"https://api.bricklink.com/api/store/v1/items/{item_type}/{item_no}/price"
    
    def fetch_raw_bl_data(guide_type, condition):
        params = {
            'color_id': color_id,
            'guide_type': guide_type,
            'new_or_used': condition,
            'currency_code': 'USD'
            # 'country_code': 'US', # <--- If your manual call was US-only, uncomment this!
        }
        
        # Use the session directly (session.get instead of requests.get)
        resp = session.get(base_url, params=params)
        data = resp.json()
        
        if data.get('meta', {}).get('code') != 200:
            print(f"Error fetching {item_no}: {data.get('meta', {}).get('message')}")
            return None
        return data.get('data', {})

    
    # 3. Compile the data into the ItemPriceStats model
    # current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def fetch_stat(guide_type, condition):
        params = {'color_id': color_id, 'guide_type': guide_type, 'new_or_used': condition, 'currency_code': 'USD'}
        resp = session.get(base_url, params=params)
        return resp.json().get('data', {})

    ns = fetch_stat('stock', 'N')
    us = fetch_stat('stock', 'U')
    nso = fetch_stat('sold', 'N')
    uso = fetch_stat('sold', 'U')

    # # --- CRITICAL DEBUG PRINT ---
    # if raw_new_sold:
    #     print(f"\n========================================")
    #     print(f"DEBUGGING DISCREPANCY FOR {item_no}")
    #     print(f"Target: Sold / Condition: New")
    #     print(f"API qty_avg_price: {raw_new_sold.get('qty_avg_price')}")
    #     print(f"API avg_price:     {raw_new_sold.get('avg_price')}")
    #     print(f"API unit_quantity: {raw_new_sold.get('unit_quantity')}")
    #     print(f"========================================\n")

    stats_data = {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'item_no': item_no,
        'color_id': color_id,
        'new_stock_avg_price': float(ns.get('avg_price', 0)),
        'new_stock_qty_avg_price': float(ns.get('qty_avg_price', 0)),
        'new_stock_unit_quantity': int(ns.get('unit_quantity', 0)),
        'new_stock_total_quantity': int(ns.get('total_quantity', 0)),
        'used_stock_avg_price': float(us.get('avg_price', 0)),
        'used_stock_qty_avg_price': float(us.get('qty_avg_price', 0)),
        'used_stock_unit_quantity': int(us.get('unit_quantity', 0)),
        'used_stock_total_quantity': int(us.get('total_quantity', 0)),
        'new_sold_avg_price': float(nso.get('avg_price', 0)),
        'new_sold_qty_avg_price': float(nso.get('qty_avg_price', 0)),
        'new_sold_unit_quantity': int(nso.get('unit_quantity', 0)),
        'new_sold_total_quantity': int(nso.get('total_quantity', 0)),
        'used_sold_avg_price': float(uso.get('avg_price', 0)),
        'used_sold_qty_avg_price': float(uso.get('qty_avg_price', 0)),
        'used_sold_unit_quantity': int(uso.get('unit_quantity', 0)),
        'used_sold_total_quantity': int(uso.get('total_quantity', 0)),
    }
    
    stats_model = ItemPriceStats(**stats_data)
    
    # 4. Save the data to the CSV file
    
    file_path = _get_monthly_stats_filepath()
    
    # Ensure the directory exists
    os.makedirs(STATISTICS_DIR, exist_ok=True)
    
    csv_headers = list(ItemPriceStats.model_fields.keys())
    row_to_write = stats_model.model_dump()

    try:
        file_exists = os.path.exists(file_path)
        
        with open(file_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_headers)
            
            if not file_exists:
                writer.writeheader()
                
            writer.writerow(row_to_write)
            
        print(f"Successfully appended fresh price stats for item {item_type}/{item_no} to {file_path}")
        
    except Exception as e:
        print(f"Error saving statistics file: {e}")
        
    return stats_model

def calculate_monthly_sales_probabilities(X: int, Y: int, Q: int) -> list[float]:
    """
    Calculates the probability distribution of selling specific quantities 
    of an item in a single month based on market competition.
    
    Args:
        X (int): Number of lots/sellers selling the part.
        Y (int): Total number of sales events per month (total units sold in market).
        Q (int): Quantity this specific seller has available.
        
    Returns:
        list[float]: A list of length Q+1 where index i is the probability of selling i units.
    """
    # Edge case: If there are no sales in the market, 0 items are sold with 100% probability.
    if Y <= 0:
        probs = [0.0] * (Q + 1)
        probs[0] = 1.0
        return probs

    # Edge case: If you are the only seller, you sell everything up to your stock 
    # or the total market demand.
    if X <= 1:
        probs = [0.0] * (Q + 1)
        actual_sales = min(Y, Q)
        probs[actual_sales] = 1.0
        return probs

    p = 1 / X          # Probability of "this seller" being chosen for one sale
    q = 1 - p          # Probability of "another seller" being chosen

    def get_normal_approximation():
        """Helper to calculate probabilities using the Normal Distribution."""
        mean = Y * p
        std_dev = math.sqrt(Y * p * q)
        
        # Avoid division by zero if std_dev is 0
        if std_dev == 0:
            probs = [0.0] * (Q + 1)
            probs[min(Q, round(mean))] = 1.0
            return probs

        def normal_cdf(x):
            return 0.5 * (1 + math.erf((x - mean) / (std_dev * math.sqrt(2))))

        probabilities = []
        running_sum = 0.0
        for k in range(Q):
            p_k = max(0.0, normal_cdf(k + 0.5) - normal_cdf(k - 0.5))
            probabilities.append(p_k)
            running_sum += p_k
            
        probabilities.append(max(0.0, 1.0 - running_sum))
        return probabilities

    # # Step 1: Check if Y is already obviously too large for Binomial math
    # if Y > 2000:
    #     return get_normal_approximation()

    # Step 2: Try exact Binomial calculation
    try:
        probabilities = []
        running_sum = 0.0

        for k in range(Q):
            if k > Y:
                p_k = 0.0
            else:
                # This is the line likely to throw OverflowError: int too large to convert to float
                # because math.comb(Y, k) can result in a number larger than float max (~1.8e308)
                p_k = math.comb(Y, k) * (p**k) * (q**(Y - k))
            
            probabilities.append(p_k)
            running_sum += p_k

        p_q_or_more = max(0.0, 1.0 - running_sum)
        probabilities.append(p_q_or_more)
        return probabilities

    except OverflowError:
        # Step 3: If float conversion fails at any point, fall back to Normal Approximation
        return get_normal_approximation()


# --- Helper Functions ---

# --- Helper: Visualization Logic (Separate Graphs) ---
def generate_separate_graphs_html(df: pd.DataFrame, set_no: str, condition: str, part_out_value: float, buy_price: float):
    """
    Generates a single HTML string with two separate Plotly charts.
    
    Args:
        df: DataFrame containing 'month', 'projected_sale', and 'roi_percent'
        set_no: The LEGO set number
        condition: 'N' or 'U'
        part_out_value: Total calculated value
        buy_price: User's purchase price for the threshold line
    """
    # 1. Logic Fix: Adjust month to start at 1 if it starts at 0
    # We create a copy to avoid modifying the original dataframe passed in
    plot_df = df.copy()

    full_condition = condition_map.get(condition.upper(), condition)

    # --- 2. ROI Percent Graph ---
    # Convert roi_percent to float if it's a string (handling the '%' sign)
    if 'roi_percent' in plot_df.columns:
        if plot_df['roi_percent'].dtype == object:
            plot_df['roi_float'] = plot_df['roi_percent'].astype(str).str.replace('%', '').astype(float)
        else:
            plot_df['roi_float'] = plot_df['roi_percent'].astype(float)
    else:
        plot_df['roi_float'] = 0.0
    
        # Ensure we only have relevant columns before adding origin
    plot_df = plot_df[['month', 'projected_sale', 'roi_float']]
    
    # 2. Add the Origin Point (0,0)
    # We create a 0-month row to make the graph start at the origin
    origin_row = pd.DataFrame({'month': [0], 'projected_sale': [0.0], 'roi_float': [0.0]})

    # If the original data started at 0, we replace it; otherwise, we prepend
    if not plot_df.empty and plot_df['month'].iloc[0] == 0:
        plot_df = pd.concat([origin_row, plot_df.iloc[1:]], ignore_index=True)
    else:
        plot_df = pd.concat([origin_row, plot_df], ignore_index=True)
        


    # 1. Sales Projection Graph
    fig_sales = go.Figure()

    fig_sales.add_trace(go.Scatter(
        x=plot_df['month'], 
        y=plot_df['projected_sale'],
        name="Projected Sales",
        mode='lines+markers',
        line=dict(color='#2ecc71', width=3),
        hovertemplate='%{y:$.2f}<extra></extra>' # Show only Y value, formatted as currency
    ))

    fig_sales.update_layout(
        title=f"Cumulative Projected Sales ($) - Set {set_no} ({condition})",
        xaxis_title="Month",
        yaxis_title="USD ($)",
        template="plotly_white",
        height=400,
        hovermode='x unified', # Optional: makes hover cleaner, but hovertemplate above controls content
        xaxis=dict(tickmode='linear', tick0=0, dtick=1, range=[0, plot_df['month'].max() + 0.5]),
        yaxis=dict(rangemode='tozero')
    )

    if buy_price is not None or buy_price > 0:
        # 4. Logic Fix: Add horizontal line for Buy Price
        fig_sales.add_hline(
            y=buy_price, 
            line_dash="dash",
            line_color="#34495e",
            annotation_text=f"Buy Price: ${buy_price:,.2f}", 
            annotation_position="bottom right"
        )

    fig_sales.update_layout(
        title=f"Cumulative Projected Sales ($) - Set {set_no} (Condition: {full_condition})",
        xaxis_title="Month",
        yaxis_title="USD ($)",
        template="plotly_white",
        height=450,
        xaxis=dict(tickmode='linear', tick0=1, dtick=1) # Ensure month ticks are integers
    )

    fig_roi = go.Figure()

    fig_roi.add_trace(go.Scatter(
        x=plot_df['month'], 
        y=plot_df['roi_float'],
        name="ROI %",
        mode='lines+markers',
        line=dict(color='#e74c3c', width=3)
    ))

    # Add a horizontal line at 0% for ROI baseline
    fig_roi.add_hline(y=0, line_color="black", line_width=1)

    fig_roi.update_layout(
        title=f"24-Month ROI Projection (%) - Set {set_no}",
        xaxis_title="Month",
        yaxis_title="ROI Percentage (%)",
        template="plotly_white",
        height=450,
        xaxis=dict(tickmode='linear', tick0=1, dtick=1)
    )

    # Convert figures to HTML divs (no full HTML wrapper yet)
    sales_div = plot(fig_sales, output_type='div', include_plotlyjs='cdn')
    roi_div = plot(fig_roi, output_type='div', include_plotlyjs=False)

    # 3. Logic Fix: Part Out Value added to the template under the main title
    html_content = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>Analysis for {set_no}</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background-color: #f4f7f6; color: #333; }}
                .header-container {{ margin-bottom: 30px; border-bottom: 2px solid #dee2e6; padding-bottom: 20px; }}
                .stat-box {{ display: inline-block; background: #fff; padding: 15px 25px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 5px solid #3498db; }}
                .stat-label {{ font-size: 0.9rem; color: #7f8c8d; text-transform: uppercase; font-weight: bold; }}
                .stat-value {{ font-size: 1.8rem; color: #2c3e50; font-weight: bold; display: block; }}
                .chart-container {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.07); margin-bottom: 30px; }}
                h1 {{ color: #2c3e50; margin-bottom: 10px; }}
            </style>
        </head>
        <body>
            <div class="header-container">
                <h1>Set Analysis Report: {set_no}</h1>
                <div class="stat-box">
                    <span class="stat-label">Estimated Part Out Value</span>
                    <span class="stat-value">${part_out_value:,.2f}</span>
                </div>
            </div>
            
            <div class="chart-container">{sales_div}</div>
            <div class="chart-container">{roi_div}</div>
        </body>
    </html>
    """
    return html_content


def get_projections_list(condition, buy_price, regular_inventory) :
    """
    Converts the DataFrame of projections into a list of MonthlyProjection models.
    """
    # 1. Gather initial market stats for all items
    item_market_data = []
    total_part_out_value = 0.0
    
    for item in regular_inventory:
        try:
            stats = get_and_save_price_stats(item.item_no, item.item_type, item.color_id)
            
            if condition == 'N':
                price = stats.new_sold_avg_price
                base_vol = stats.new_sold_total_quantity
                sellers = stats.new_stock_unit_quantity
            else:
                price = stats.used_sold_avg_price
                base_vol = stats.used_sold_total_quantity
                sellers = stats.used_stock_unit_quantity

            total_part_out_value += (item.quantity * price)
            item_market_data.append({
                "item_no": item.item_no,
                "qty": item.quantity,
                "price": price,
                "sellers": sellers,
                "base_vol": base_vol
            })
        except Exception as e:
            print(f"Skipping item {item.item_no}: {e}")
            continue

    # 2. Calculate 24-Month Projections using the probability method
    projections_list = []
    
    for m in range(1, 25):
        total_projected_sale_for_month = 0.0
        
        for data in item_market_data:
            # Normalize 6-month aggregate data to a monthly baseline scaled by month 'm'
            monthly_volume_est = round((data["base_vol"] / 6) * m)
            
            # Ensure we don't pass 0 sellers to the probability function
            X_val = max(1, data["sellers"]) if data["sellers"] > 0 else 0
            Y_val = monthly_volume_est
            
            # probability logic (assuming calculate_monthly_sales_probabilities is imported)
            probs = calculate_monthly_sales_probabilities(
                X=X_val + 1,
                Y=Y_val,
                Q=data["qty"]
            )
            
            # Expected Value: Sum of k * P(k)
            expected_qty_sold_data = sum(k * p_k for k, p_k in enumerate(probs))
            total_projected_sale_for_month += (data["price"] * expected_qty_sold_data)
            
        # Calculate ROI for this specific month's cumulative projection
        roi_val = (100 * total_projected_sale_for_month / buy_price) if buy_price > 0 else 0.0
        
        projections_list.append({
            "month": m,
            "projected_sale": round(total_projected_sale_for_month, 5),
            "roi_percent": round(roi_val, 5)
        })

    return projections_list, total_part_out_value

# --- Routes ---


@app.get("/items/set/{set_no}/risk_value/{condition}/visualize", response_class=HTMLResponse)
def get_set_projected_sale_visuals(
    set_no: str, 
    condition: Literal['N', 'U'], 
    buy_price: float = 0.0
):
    try:
        inventory = get_set_inventory(set_no)
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to retrieve set inventory.")

    # --- Filter out alternate/counterpart parts ---
    regular_inventory = [
        part for part in inventory 
        if not part.is_alternate and not part.is_counterpart
    ]

    if not regular_inventory:
        # Returning a simple HTML error for the visual endpoint
        return HTMLResponse("<h1>Error: The set number is wrong or its inventory is missing.</h1>", status_code=404)

    projections_list, total_part_out_value = get_projections_list(condition, buy_price, inventory)

    # 3. Create DataFrame and Generate Visuals
    df = pd.DataFrame(projections_list)
    return generate_separate_graphs_html(df, set_no, condition, total_part_out_value, buy_price)






# def calculate_projected_sale(X: int, Y: float, Q: int, price: float) -> float:
#     """Calculates expected revenue for the month based on probabilities."""
#     list_probs = calculate_monthly_sales_probabilities(X, Y, Q)
#     expected_quantity_sold = 0
#     for i, prob in enumerate(list_probs):
#         expected_quantity_sold += i * prob
#     return price * expected_quantity_sold



# # --- Helper logic for the formula ---
# def calculate_risk_value(sellers: int, sales_vol: float, qty: int, price: float) -> float:
#     """
#     Calculates the expected return for a specific volume.
#     Probability = Sales Volume / (1 + Sellers)
#     """
#     denominator = 1 + sellers
#     prob_selling = min(1.0, sales_vol / denominator) if denominator > 0 else 0.0
#     return qty * price * prob_selling

@app.get("/items/set/{set_no}/risk_value/{condition}", 
         response_model=ProjectedSaleResult, 
         summary="Calculate Risk & 24-Month ROI Projection")
def get_set_projected_sale(
    set_no: str, 
    condition: Literal['N', 'U'], 
    buy_price: float = 0.0
):
    try:
        inventory = get_set_inventory(set_no)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    regular_inventory = [p for p in inventory if not p.is_alternate and not p.is_counterpart]
    if not regular_inventory:
        return ProjectedSaleResult(
            set_no=set_no, condition=condition,
            part_out_value=0, 
            projections=[], 
            total_parts_processed=0, 
            report_file="", 
            message="Inventory contains no regular (non-alternate/non-counterpart) items."
        )

    total_part_out_value = 0.0
    item_market_data = []

    # 1. Gather initial market stats
    for item in regular_inventory:
        stats = get_and_save_price_stats(item.item_no, item.item_type, item.color_id)
        
        if condition == 'N':
            price, base_vol, sellers = stats.new_sold_avg_price, stats.new_sold_total_quantity, stats.new_stock_unit_quantity
        else:
            price, base_vol, sellers = stats.used_sold_avg_price, stats.used_sold_total_quantity, stats.used_stock_unit_quantity

        # price = stats.new_sold_avg_price
        # base_vol = stats.new_sold_unit_quantity = Y
        # sellers = stats.new_stock_unit_quantity = X
        # "qty": item.quantity = Q

        total_part_out_value += (item.quantity * price)
        item_market_data.append({
            "item_no": item.item_no,
            "item.color_id": item.color_id,
            "qty": item.quantity,
            "price": price,
            "sellers": sellers,
            "base_vol": base_vol
        })

    print(f"\nTotal number of items processed: {len(item_market_data)}")
    # 2. Calculate 24-Month Projections using the probability method
    projections = []
    val_after_six_months = 0.0

    print("-------------------------------------------------------------")
    print("X = data[sellers] = ", item_market_data[0]["sellers"])
    print("Y = data[base_vol] = ", item_market_data[0]["base_vol"])
    print("Q = data[qty] = ", item_market_data[0]["qty"])
    print("-------------------------------------------------------------")
    for m in range(1, 25):
        expected_qty_sold = 0.0
        item_projected_sale = 0.0
        
        for data in item_market_data:
            print(f"\n iten no is = {data['item_no']} | month = {m}")
            print("item color_id = ", data["item.color_id"])
            # We normalize the 6-month aggregate data to a monthly baseline
            # and then scale the volume (Y) by the current month (m).
            # Using round() to get the closest integer.
            
            monthly_sellers_est = data["sellers"]
            monthly_volume_est = round((data["base_vol"] / 6) * m)
            # print("monthly_sellers_est = ", monthly_sellers_est)
            # print("monthly_volume_est = ", monthly_volume_est)

            # Ensure we don't pass 0 sellers to the probability function 
            # if the calculation rounded down to zero but data exists.
            X_val = max(1, monthly_sellers_est) if data["sellers"] > 0 else 0
            Y_val = monthly_volume_est
            
            probs = calculate_monthly_sales_probabilities(
                X=X_val + 1,
                Y=Y_val,
                Q=data["qty"]
            )
            
            # Expected Value calculation: Sum of k * P(k)
            # k is the index in the probs list
            expected_qty_sold_data = sum(k * p_k for k, p_k in enumerate(probs))
            expected_qty_sold += expected_qty_sold_data
            
            # Item Projection = Price * Expected Units Sold
            item_projected_sale_data = data["price"] * expected_qty_sold_data
            item_projected_sale += item_projected_sale_data

            print(f"  > Expected Qty Sold for item {data['item_no']}: {expected_qty_sold_data:.5f}")
            print(f"  > Projected Sale for item {data['item_no']}: ${item_projected_sale_data:.5f}")

        if m == 6:
            val_after_six_months = item_projected_sale

        roi_val = (100 * item_projected_sale / buy_price) if buy_price > 0 else 0.0
        
        projections.append(MonthlyProjection(
            month=m,
            projected_sale=round(item_projected_sale, 5),
            roi_percent=f"{roi_val:.5f}%"
        ))

    return ProjectedSaleResult(
        set_no=set_no,
        condition=condition,
        projections=projections,
        part_out_value=round(total_part_out_value, 5),
        total_parts_processed=len(item_market_data),
        report_file=f"set_analysis_{set_no}.csv",
    )











# @app.get("/project-investment", response_model=List[MonthlyProjection])
# async def project_investment(
#     buy_price: float = Query(..., description="The purchase price of the LEGO set"),
#     set_id: str = Query("75192", description="The ID of the LEGO set")
# ):
#     """
#     Simulates a 24-month projection for a specific LEGO set.
#     Now uses GET with query parameters so it can be accessed via URL.
#     Example: /project-investment?buy_price=500.0
#     """
    
#     # Mock lookup for set inventory
#     mock_inventory = [
#         {"name": "Plate 1x2", "qty": 50, "avg_price": 0.15, "sellers": 120, "monthly_sales": 400},
#         {"name": "Brick 2x4", "qty": 20, "avg_price": 0.45, "sellers": 80, "monthly_sales": 150},
#         {"name": "Technic Beam", "qty": 10, "avg_price": 1.20, "sellers": 40, "monthly_sales": 30},
#     ]

#     time_series = []
    
#     # Projection over 24 months
#     for month in range(1, 25):
#         month_total_projected = 0.0
        
#         for item in mock_inventory:
#             # Your original Formula logic
#             projected = calculate_projected_sale(
#                 item["sellers"],
#                 (4/6) * item["monthly_sales"] * month,
#                 item["qty"],
#                 item["avg_price"]
#             )
#             month_total_projected += projected

#         roi = (month_total_projected / buy_price) * 100 if buy_price > 0 else 0
        
#         time_series.append(MonthlyProjection(
#             month=month,
#             projected_sale=round(month_total_projected, 2),
#             roi_percent=round(roi, 2)
#         ))

#     return time_series