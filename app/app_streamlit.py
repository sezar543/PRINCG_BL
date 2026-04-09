import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Literal
import os
import time
import streamlit.components.v1 as components
import requests

from app_fastapi import get_set_inventory, get_projections_list

# 1. Get the directory where app_streamlit.py is located
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Build the path to the images folder relative to this file
# This works on Windows AND Railway automatically
img_path = os.path.join(current_dir, "images", "roi_75361,75387.png")

if os.path.exists(img_path):
    st.image(img_path, caption="ROI Comparison Graph")
else:
    # Diagnostic message to help you see where the app is looking
    st.error(f"Image not found at: {img_path}")
    st.info(f"Current working directory: {os.getcwd()}")


API_URL = os.getenv("API_URL", "http://localhost:8000")
API_URL = "http://127.0.0.1:8000"

# Example call:
# response = requests.get(f"{API_URL}/items/set/{set_no}...")

condition_map = {
    'N': 'New',
    'U': 'Used'
}

# --- CONFIGURATION & PAGE SETUP ---
st.set_page_config(page_title="Set Sales & ROI Tracker", layout="wide")


# # --- DEBUG SIDEBAR (Add this here) ---
# with st.sidebar:
#     st.header("🛠️ Debug Tools")
#     if st.button("🔍 Check Image Files"):
#         # We check the directory relative to this script
#         img_folder = os.path.join(current_dir, "images")
#         if os.path.exists(img_folder):
#             files = os.listdir(img_folder)
#             st.write(f"Files found in {img_folder}:")
#             st.write(files)
#         else:
#             st.error(f"Directory not found: {img_folder}")
            
#     # Also check the Volume while we are at it
#     if st.button("📦 Check Volume"):
#         vol_path = "/app/inventories"
#         if os.path.exists(vol_path):
#             st.write(f"Inventories in Volume: {os.listdir(vol_path)}")
#         else:
#             st.error("Volume path /app/inventories not found")



def get_real_projections(set_no: str, condition: str, buy_price: float):
    try:
        url = f"{API_URL}/items/set/{set_no}/data"
        params = {"condition": condition, "buy_price": buy_price}
        
        # DEBUG PRINT: This will show up in Railway logs
        print(f"DEBUG: Streamlit is calling URL: {url} with params {params}")
        
        response = requests.get(url, params=params, timeout=30) # Add a timeout
        
        print(f"DEBUG: FastAPI responded with status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            return pd.DataFrame(result['projections']), result['part_out_value'], None, result['num_lots'], result['total_items']
        else:
            # Reveal the actual error from FastAPI
            error_detail = response.text
            return None, 0, f"Backend Error {response.status_code}: {error_detail}", 0, 0
            
    except Exception as e:
        print(f"DEBUG: Request failed entirely: {str(e)}")
        return None, 0, f"Connection Failed: {str(e)}", 0, 0
        
# def get_real_projections(set_no: str, condition: str, buy_price: float):
#     try:
#         # We call the FastAPI endpoint we created in Step 1
#         url = f"API_URL/items/set/{set_no}/risk_value/{condition}/data"
#         params = {"condition": condition, "buy_price": buy_price}
        
#         response = requests.get(url, params=params)
        
#         if response.status_code == 200:
#             result = response.json()
#             # result['projections'] is now a standard list of dicts
#             df = pd.DataFrame(result['projections'])
            
#             return (
#                 df, 
#                 result['part_out_value'], 
#                 None, 
#                 result['num_lots'], 
#                 result['total_items']
#             )
#         else:
#             return None, 0, f"API Error: {response.status_code}", 0, 0
            
#     except Exception as e:
#         return None, 0, f"Connection Failed: {str(e)}", 0, 0
    

# def get_real_projections(set_no: str, condition: Literal['N', 'U'], buy_price: float):
#     try:
#         # This calls your FastAPI method
#         inventory = get_set_inventory(set_no) 
        
#         if not inventory:
#             return None, 0, "No inventory found", 0, 0
            
#         # --- NEW LOGIC: Calculate Metadata ---
#         num_lots = len(inventory)
#         total_items = sum(part.quantity for part in inventory)
#         # -------------------------------------

#         projections_list, total_part_out_value = get_projections_list(condition, buy_price, inventory)
#         df = pd.DataFrame(projections_list)
        
#         return df, total_part_out_value, None, num_lots, total_items
#     except Exception as e:
#         return None, 0, str(e), 0, 0




def create_plots(df, set_no, condition, buy_price, part_out_val=0, num_lots=0, total_items=0):
    df = df.copy()
    # 1. Fix: Ensure we don't have negative months
    df['month'] = pd.to_numeric(df['month'], errors='coerce')
    df = df[df['month'] >= 0]
    
    df['projected_sale'] = pd.to_numeric(df['projected_sale'], errors='coerce')
    
    origin_row = pd.DataFrame({'month': [0.0], 'projected_sale': [0.0]})
    plot_df = pd.concat([origin_row, df], ignore_index=True).sort_values('month')
    pct_of_buy = (part_out_val / buy_price * 100) if buy_price > 0 else 0

    # Updated Markdown to include Lots and Total Items
    st.markdown(f"""
    <div style="background-color: #f8fafc; padding: 15px; border: 1px solid #e2e8f0; border-radius: 5px; margin-bottom: 10px; line-height: 1.6;">
        <span style="font-size: 1.1em;"><b>Set {set_no}</b></span><br>
        <b>Inventory Info:</b> {num_lots} Lots ({total_items} Total Items)<br>
        <b>Buy price:</b> ${buy_price:,.2f} USD<br>
        <b>Part out value:</b> ${part_out_val:,.2f} <span style="color: #2ecc71;">({pct_of_buy:.0f}% of buy price)</span>
    </div>
    """, unsafe_allow_html=True)

    fig_sales = go.Figure()
    fig_sales.add_trace(go.Scatter(
        x=plot_df['month'], y=plot_df['projected_sale'],
        mode='lines+markers', line=dict(color='#2ecc71', width=3),
        marker=dict(size=8), name="Projected Sale"
    ))

    if buy_price > 0:
        fig_sales.add_hline(y=buy_price, line_dash="dash", line_color="red",
                           annotation_text=f"Buy Price = ${buy_price:,.2f}", annotation_position="bottom right")

    # 2. Fix: Ensure axis starts exactly at (0,0) by setting range [0, None]
    fig_sales.update_layout(
        xaxis=dict(rangemode='tozero', range=[0, None], title="Month", dtick=1),
        yaxis=dict(rangemode='tozero', range=[0, None], title="USD ($)"),
        template="plotly_white", height=500, margin=dict(t=30) 
    )
    return fig_sales, {'displayModeBar': True, 'toImageButtonOptions': {'format': 'png', 'filename': f'sales_{set_no}'}}

# --- STYLING ---
st.markdown("""
    <style>
    /* 1. Remove the default gap between columns entirely */
    [data-testid="stHorizontalBlock"] {
        gap: 0px !important;
        justify-content: flex-start !important;
    }

    /* 2. Prevent columns from expanding */
    [data-testid="column"] {
        flex: 0 1 auto !important;
        min-width: unset !important;
        padding-right: 5px !important; /* Tiny gap for breathing room */
    }

    /* 3. Force the inputs to a fixed small width */
    div[data-baseweb="input"], 
    div[data-baseweb="select"],
    .stTextInput > div > div > input {
        width: 100px !important;
    }
    
    /* Specific width for the Suffix dropdown to be smaller */
    div[key^="suf_"] div[data-baseweb="select"] {
        width: 80px !important;
    }

    /* 4. Dash alignment - perfectly centered between inputs */
    .dash-container { 
        display: flex; 
        align-items: center; 
        justify-content: center; 
        height: 100%; 
        font-weight: bold; 
        font-size: 1.2rem; 
        margin-top: 32px; 
        width: 20px;
        padding: 0 !important;
    }
    .no-label-dash { margin-top: 10px !important; }
    
    /* 5. Centered Red Status Text */
    .status-text-container {
        color: #ff4b4b;
        text-align: center;
        width: 100%;
        font-weight: bold;
        margin: 20px 0;
        font-size: 1.1rem;
    }
            
    /* 6. Centered Primary Button */
    div.stButton > button[kind="primary"] {
        width: 350px !important;
        display: block;
        margin: 20px auto;
    }

    /* Fix to prevent labels from wrapping */
    label p {
        font-size: 0.85rem !important;
        white-space: nowrap !important;
    }
    </style>
""", unsafe_allow_html=True)


tab_analysis, tab_guide = st.tabs(["📊 Market Analysis", "📖 User Guide & Examples"])

with tab_analysis:
    if 'num_sets' not in st.session_state: st.session_state.num_sets = 1
    if 'results_state' not in st.session_state: st.session_state.results_state = []

    st.title("Market Analysis Dashboard")
    suffixes = [str(i) for i in range(1, 26)]
    set_entries = []

    for i in range(st.session_state.num_sets):
        has_labels = (i == 0)
        cols = st.columns([0.1, 0.05, 0.1, 0.15, 0.2, 0.33])
        with cols[0]: s_id = st.text_input("set Number (ID)" if has_labels else "", key=f"id_{i}", placeholder="ID")
        with cols[1]: st.markdown(f'<div class="{"dash-container" if has_labels else "dash-container no-label-dash"}">-</div>', unsafe_allow_html=True)
        with cols[2]: s_suf = st.selectbox("Suffix" if has_labels else "", options=suffixes, key=f"suf_{i}")
        with cols[3]: s_cond = st.selectbox("Condition" if has_labels else "", options=["New", "Used"], key=f"cond_{i}")
        with cols[4]: s_price = st.text_input("Buy Price ($ USD)" if has_labels else "", key=f"pr_{i}", placeholder="0.00")
        set_entries.append({'id': s_id, 'suffix': s_suf, 'cond': 'N' if s_cond == "New" else 'U', 'price': s_price})

    btn_cols = st.columns([0.15, 0.15, 0.7])
    with btn_cols[0]:
        if st.button("➕ More sets"):
            st.session_state.num_sets += 1
            st.rerun()
    with btn_cols[1]:
        if st.button("🗑️ Delete row") and st.session_state.num_sets > 1:
            st.session_state.num_sets -= 1
            st.rerun()

    st.divider()

    # Red button centered and limited in width via CSS
    if st.button("📊 View the ROI and Projection Sale graphs", type="primary"):
        temp_results = []

        status_area = st.empty()
        status_messages = []

        for entry in set_entries:
            if not entry['id']: continue
            try:
                val = entry['price'].replace('$', '').replace(',', '').strip()
                b_price = float(val) if val else 0.0
                full_id = f"{entry['id']}-{entry['suffix']}"

                #Update status to "being retrieved"
                status_messages.append(f"- The inventory and sale data of the set {full_id} is being retrieved...")
                # Render messages in a red centered div
                status_area.markdown(f'<div class="status-text-container">{"<br>".join(status_messages)}</div>', unsafe_allow_html=True)



                # Updated call to receive num_lots and total_items
                df, total_val, err_msg, n_lots, t_items = get_real_projections(full_id, entry['cond'], b_price)
                
                if not err_msg and df is not None:
                    temp_results.append({
                        'id': full_id, 
                        'df': df, 
                        'cond': entry['cond'], 
                        'price': b_price, 
                        'part_out': total_val,
                        'num_lots': n_lots,        # Added to results_state
                        'total_items': t_items     # Added to results_state
                    })

                    status_messages[-1] = f"- The inventory and sale data of the set {full_id} is retrieved."
                    status_area.markdown(f'<div class="status-text-container">{"<br>".join(status_messages)}</div>', unsafe_allow_html=True)

            except: continue

        # After loop is complete, clear the status area to make it "disappear"
        time.sleep(1) # Brief pause so the user sees the final "retrieved" status
        status_area.empty()
        st.session_state.results_state = temp_results

    if st.session_state.results_state:
        st.subheader("Comparison: ROI Projections")
        fig_roi_combined = go.Figure()
        
        # 2.b) Horizontal reference lines
        y_lines = [100, 110, 125, 150]
        for y_val in y_lines:
            if y_val == 100:
                ann = "100% ROI: Breakeven Point"
            else:
                ann = f"%{y_val}"

            fig_roi_combined.add_hline(
                y=y_val, 
                line_dash="dot", 
                line_color="#555",
                annotation_text=ann, 
                annotation_position="bottom right"
            )

        for res in st.session_state.results_state:
            origin_row = pd.DataFrame({'month': [0.0], 'roi_percent': [0.0]})
            plot_df = pd.concat([origin_row, res['df']], ignore_index=True).sort_values('month')
            fig_roi_combined.add_trace(go.Scatter(x=plot_df['month'], y=plot_df['roi_percent'], name=res['id'], mode='lines+markers'))
        
        # 2) Grid at 0, 10, 20... 2.c) Range to 200
        fig_roi_combined.update_layout(
            xaxis=dict(title="Month", dtick=1),
            yaxis=dict(title="ROI (%)", dtick=10, range=[0, 300]),
            template="plotly_white",
            height=600
        )
        st.plotly_chart(fig_roi_combined, use_container_width=True, config={'displayModeBar': True})

        st.divider()
        st.subheader("Individual Sales Growth")
        if "results_state" in st.session_state:
            for index, res in enumerate(st.session_state.results_state):
                # We use 'index' and 'res['id']' to ensure the key is always unique 
                # even if you search for the same set multiple times.
                unique_key = f"chart_{res['id']}_{index}"
                
                fig, config = create_plots(
                    res['df'], 
                    res['id'], 
                    res['cond'], 
                    res['price'], 
                    res['part_out'], 
                    res.get('num_lots', 0), 
                    res.get('total_items', 0)
                )
                
                # Pass the unique_key to the key argument
                st.plotly_chart(fig, use_container_width=True, config=config, key=unique_key)

with tab_guide:
    st.title("User Guide & Strategic Analysis")
    
    g_col1, g_col2 = st.columns(2)
    with g_col1:
        st.markdown("""
        <div class="help-card">
            <div class="concept-title">📈 What is Sale Projection?</div>
            <p>This predicts your <b>"Sales Speed."</b> It shows the cumulative money returned to your pocket month-by-month based on market demand. It helps you see how long your cash is "tied up" in plastic.</p>
        </div>
        """, unsafe_allow_html=True)
    with g_col2:
        st.markdown("""
        <div class="help-card">
            <div class="concept-title">💰 ROI (Return on Investment)</div>
            <p>ROI shows how hard your money is working. 
            <b>100%</b> means you got your initial investment back. 
            Anything <b>above 100%</b> is profit you can use to grow your store.</p>
        </div>
        """, unsafe_allow_html=True)

    st.subheader("💡 The Sprinter vs. The Marathoner")
    st.write("""Imagine you have **$1,000** to spend. You are choosing to buy 10 copies of each of two sets 78361 and 78387, but then you thought: "Wait a minute! I should also look at the ROI graph and compare the turnaround of these two sets..." By using the **ROI Comparison Graph**, you see a clear difference between the two sets:""")

    # Clean logic that works on Windows and Railway
    img_filename = "roi_75361,75387.png"
    img_path = os.path.join(current_dir, "images", img_filename)
    
    if os.path.exists(img_path):
        st.image(img_path, caption="ROI Comparison Graph")
    else:
        st.error(f"Image not found. Railway is looking at: {img_path}")

    # Improved image path logic
    # img_path = "C:\\Pricing_BL\\app\\images\\roi_75361,75387.png"
    # if not os.path.exists(img_path):
    #     img_path = "/app/images/roi_78361,78387.png"


    if os.path.exists(img_path):
        st.image(img_path, caption="ROI Comparison Graph")
    else:
        st.error(f"Image not found. Please ensure it is located at: app/images/roi_78361,78387.png")

    e_col1, e_col2 = st.columns(2)
    with e_col1:
        st.info("**Set 75387 (The Sprinter)**")
        st.write("- **Buy price:** $49\n- **Part out value:** $82.28 USD (168% of its buy price)\n- **Break-even point:** Hits 100% ROI in **1 months**.\n- **Velocity:** Hits 133% ROI in **2 months**.")
    with e_col2:
        st.warning("**Set 75361 (The Marathoner)**")
        st.write("- **Buy price:** $51\n- **Part out value:** $78.84 USD (155% of its buy price)\n- **Break-even point:** Hits 100% ROI in **4 months**.\n- **Velocity:** Hits 133% ROI in **10 months**.")

    st.success("""
    **The Lesson:** Even if both sets eventually reach a high profit, set 75387 sells much faster. While it takes 10 months for the set 75361 to return 133% of your initial investment, the set 75387 does this in just 2 months. In the time it takes the "Marathoner" to reach that milestone, you could have "flipped" the "Sprinter" multiple times! It also takes only one month for set 75387 to reach 100% ROI (i.e., to have your initial investment fully back), while this takes 4 months for set 75361!
               
    Since you still want to have a good variety of parts in your store's inventory, you want to buy a few copies of both sets, 
    which leads you to decide to buy **16 copies of the set 75387** and **4 copies of the set 75361.**
               
    """)