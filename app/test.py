# import requests
# from oauthlib.oauth1 import Client
# import urllib.parse

# # Your BrickLink API endpoint URL
# base_url = "https://api.bricklink.com/api/store/v1/items/part/"

# # List of part numbers to fetch pricing for
# part_numbers = ["sw0845", "87610pb08", "varactyl"]  # Replace with your list of part numbers

# # Your BrickLink API credentials
# consumer_key = "redacted"
# consumer_secret = "redacted" 
# #token_key is called TokenValue on BL
# token_key = "redacted" 
# token_secret = "redacted" 

# # Initialize the OAuth1 client
# client = Client(
#     consumer_key,
#     client_secret=consumer_secret,
#     resource_owner_key=token_key,
#     resource_owner_secret=token_secret,
#     signature_method='HMAC-SHA1',
# )

# # Loop through the list of part numbers and make API requests
# for part_number in part_numbers:
#     encoded_part_number = urllib.parse.quote(part_number)
#     url = f"{base_url}{encoded_part_number}/price"

#     print(f"Request URL: {url}")

#     uri, headers, body = client.sign(url)

#     # Make the GET request
#     response = requests.get(uri, headers=headers)

#     # Check if the request was successful
#     if response.status_code == 200:
#         # Parse and print the entire response JSON
#         data = response.json()
#         print(f"Response for Part Number: {part_number}")
#         print(data)
#     else:
#         print(f"Failed to fetch data for part number: {part_number}. Status code: {response.status_code}, Response: {response.text}")
#         print(f"OAuth Headers: {headers}")





# import os
# import requests
# from requests_oauthlib import OAuth1Session

# # --- 1. CONFIGURE YOUR CREDENTIALS AND ENDPOINT ---

# # IMPORTANT: Replace these placeholders with your actual BrickLink credentials.
# # The issue you are having is likely due to the IP address being tied to the token.
# CONSUMER_KEY = "F77F41502C8041E49EC42529EA26FAD7" # Replace with your Consumer Key
# CONSUMER_SECRET = "E214EF5F097441F0949514A76DE5749E"           # Replace with your Consumer Secret
# ACCESS_TOKEN = "D8BEDCA603844337BA58181B5FCF644F" # Replace with your Access Token
# TOKEN_SECRET = "192A31C402C84AABB37EB1CD886707C2"                 # Replace with your Token Secret


# # Correct endpoint for getting the PARTS (inventory) of the set
# SET_NO = "7730-1"
# BRICKLINK_API_URL = f"https://api.bricklink.com/api/store/v1/items/set/{SET_NO}"
# # https://api.bricklink.com/api/store/v1/items/set/7730-1/subsets
# # --- 2. AUTHENTICATION AND REQUEST EXECUTION ---

# def fetch_set_inventory():
#     """
#     Creates an OAuth1Session and executes the GET request to the BrickLink API.
#     """
#     print(f"--- Attempting to fetch inventory for set: {SET_NO} ---")
#     print(f"API URL: {BRICKLINK_API_URL}")

#     try:
#         oauth = OAuth1Session(
#             CONSUMER_KEY,
#             client_secret=CONSUMER_SECRET,
#             resource_owner_key=ACCESS_TOKEN,
#             resource_owner_secret=TOKEN_SECRET,
#             signature_method='HMAC-SHA1'
#         )
#     except Exception as e:
#         print(f"Error initializing OAuth session: {e}")
#         return

#     # Execute the GET request
#     try:
#         response = oauth.get(BRICKLINK_API_URL)

#         print("\n--- RESPONSE DETAILS ---")
#         print(f"Status Code: {response.status_code}")
        
#         # Check for success
#         if response.status_code == 200:
#             print("\n✅ SUCCESS: Request executed successfully.")
            
#             # --- FIX: Safely parse and check the JSON response once ---
#             try:
#                 data = response.json()
#             except requests.exceptions.JSONDecodeError:
#                 print("Error: Could not decode JSON response.")
#                 print(response.text[:500])
#                 return

#             if data.get('data') and isinstance(data['data'], list):
#                 if data['data']:
#                     print(f"Total parts found: {len(data['data'])}")
#                     print("First Part Object (Item, Color, Quantity, etc.):")
#                     # Print the first item in the 'data' list
#                     print(data['data'][0])
#                 else:
#                     print("Response 'data' array is empty.")
#             else:
#                 print("No expected 'data' list found in response. Full JSON response (meta/error):")
#                 print(data)
#             # -----------------------------------------------------------

#         # Check for authentication failure (though unlikely now)
#         elif response.status_code == 401:
#             error_data = response.json()
#             print("\n❌ FAILURE: Authentication Error (401)")
#             print(f"Message: {error_data.get('meta', {}).get('message')}")
#             print(f"Description: {error_data.get('meta', {}).get('description')}")
            
#         else:
#             print(f"\n⚠️ UNEXPECTED ERROR: Status {response.status_code}")
#             print(response.text)

#     except requests.exceptions.RequestException as e:
#         print(f"\nAn error occurred during the HTTP request: {e}")


# # if __name__ == "__main__":
#     fetch_set_inventory()

import math

def calculate_monthly_sales_probabilities(X: int, Y: float, Q: int) -> list[float]:
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
    probabilities = []
    running_sum = 0.0

    # Calculate probabilities for selling i units (from 0 to Q-1)
    # Using the Binomial formula: P(i) = (Y choose i) * (p^i) * (q^(Y-i))
    for i in range(Q):
        # If the number of market sales Y is less than the specific count i, 
        # it's impossible to sell i items.
        if i > Y:
            p_i = 0.0
        else:
            # Combination: Y! / (i! * (Y-i)!)
            combinations = math.comb(X, i)
            p_i = combinations * (p**i) * (q**(Y - i))
        
        probabilities.append(p_i)
        running_sum += p_i

    # The final element P(i=Q) is the probability of selling Q OR MORE units.
    # In practice, for a seller with stock Q, this is 1 minus the probability 
    # of selling fewer than Q.
    p_q = max(0.0, 1.0 - running_sum)
    probabilities.append(p_q)

    # Clean up floating point precision issues (ensure sum is exactly 1.0)
    total = sum(probabilities)
    return [p_val / total for p_val in probabilities]

def calculate_projected_sale(X: int, Y: float, Q: int, price: float) -> float:
    """
    Calculates the Expected Value (EV) of sales revenue for one month.
    
    Args:
        X (int): Number of lots/sellers.
        Y (float): Avg sales per month.
        Q (int): Seller's quantity.
        price (float): Price per item.
        
    Returns:
        float: The expected revenue (Projected_sale).
    """
    # Get the probability distribution
    list_probs = calculate_monthly_sales_probabilities(X, Y, Q)
    
    # Expected Quantity Sold = Sum(i * P(i)) for i from 0 to Q
    # Note: i=0 is skipped in sum because 0 * P(0) = 0
    expected_quantity_sold = sum(i * list_probs[i] for i in range(1, Q + 1))
    
    projected_sale = price * expected_quantity_sold
    return projected_sale

# Example Usage:
if __name__ == "__main__":
    X = 150      # 15 sellers
    Y = 10   # 25.5 average sales per month
    Q = 2      # We have 10 in stock
    unit_price = 2.50
    
    projection = calculate_projected_sale(X, Y, Q, unit_price)
    print(f"Projected Monthly Revenue: ${projection:.2f}")