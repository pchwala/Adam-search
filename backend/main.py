import os
import requests
import json
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import gspread
from fastapi import FastAPI
from fastapi.responses import JSONResponse

class Adam:
    def __init__(self):
        """Initialize the IdoSell API client with credentials."""
        # First try to get API key from environment variable
        self.ids_key = os.environ.get("IDOSELL_API_KEY")
        
        # If not found in environment variable, try to get from tokens file
        if not self.ids_key:
            try:
                with open("/home/vis/Projects/refurbed/keys/tokens.json", "r") as f:
                    tokens = json.load(f)
                    self.ids_key = tokens.get("idosell_api_key")
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                # Handle any errors loading from file
                pass
        
        if not self.ids_key:
            raise ValueError("IdoSell API key must be provided as IDOSELL_API_KEY environment variable or in tokens.json file")
        
        # === Google Sheets Setup ===
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Try to get credentials from environment variable
        creds_json = os.environ.get("GCLOUD_CREDENTIALS_JSON")
        
        if creds_json:
            # Use credentials from environment variable
            self.creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_json), scope)
        else:
            # Fallback to loading from file
            credentials_file_path = "/home/vis/Projects/Adam/keys/ref-ids-6c3ebadcd9f8.json"
            try:
                self.creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file_path, scope)
            except FileNotFoundError:
                raise FileNotFoundError(f"Google credentials not found in environment variable or at {credentials_file_path}")
        
        self.client = gspread.authorize(self.creds)

        self.sheet_id = "15e6oc33_A21dNNv03wqdixYc9_mM2GTQzum9z2HylEg"
        
        # Open Orders Google Sheet
        self.orders_sheet = self.client.open_by_key(self.sheet_id).worksheet("Orders")
        
        # Base URL for API requests
        self.base_url = os.environ.get("IDOSELL_API_BASE_URL", "https://vedion.pl/api/admin/v5")
        
        # Default headers for requests for IdoSell
        self.ids_headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "X-API-KEY": self.ids_key
        }
        
    def count_new(self):
        """
        Count rows from the Orders sheet where r_state is 'NEW' and r_item_name does not contain 'iphone'.
        
        Returns:
            int: Number of rows matching the criteria
        """
        try:
            # Get all data from the Orders sheet
            all_data = self.orders_sheet.get_all_records()
            
            # Counter for matching rows
            count = 0
            
            # Check each row
            for row in all_data:
                # Check if 'r_state' column exists and equals 'NEW'
                if 'r_state' in row and row['r_state'] == 'NEW':
                    # Check if 'r_item_name' column exists and doesn't contain 'iphone'
                    if 'r_item_name' in row and 'iphone' not in str(row['r_item_name']).lower():
                        count += 1
            
            return count
            
        except Exception as e:
            print(f"Error counting new non-iPhone orders: {str(e)}")
            return 0

    def search_orders(self):
        endpoint = f"{self.base_url}/orders/orders/search"
        
        payload_realizowane = {
            "params": {
                "ordersStatuses": [
                "on_order"
                ]
            }
        }
        
        payload_oczekuje = {
            "params": {
                "ordersStatuses": [
                "wait_for_dispatch"
                ]
            }
        }
        
        # Send first request for "realizowane" orders
        response_realizowane = requests.post(endpoint, headers=self.ids_headers, json=payload_realizowane)
        
        # Send second request for "oczekuje" orders
        response_oczekuje = requests.post(endpoint, headers=self.ids_headers, json=payload_oczekuje)
        
        orders_realizowane = []
        orders_oczekuje = []
        
        # Process "realizowane" response
        if response_realizowane.status_code in [200, 207]:
            realizowane_data = response_realizowane.json()
            if 'Results' in realizowane_data:
                orders_realizowane = realizowane_data['Results']
        else:
            raise Exception(f"Błąd wyszukiwania zamówień 'on_order': {response_realizowane.status_code}, {response_realizowane.text}")
            
        # Process "oczekuje" response
        if response_oczekuje.status_code in [200, 207]:
            oczekuje_data = response_oczekuje.json()
            if 'Results' in oczekuje_data:
                orders_oczekuje = oczekuje_data['Results']
        else:
            raise Exception(f"Błąd wyszukiwania zamówień 'delivery_waiting': {response_oczekuje.status_code}, {response_oczekuje.text}")
        
        # Combine for "wszystko" category
        combined_orders = orders_realizowane + orders_oczekuje
        
        # Calculate counts for each category
        stats = {}
        
        categories = {
            'realizowane': orders_realizowane,
            'oczekuje': orders_oczekuje,
            'wszystko': combined_orders
        }
        
        for category, orders in categories.items():
            orders_count = len(orders)
            iphone_count = 0
            
            # Check each order for iPhone products
            for order in orders:
                if 'orderDetails' in order and 'productsResults' in order['orderDetails']:
                    for product in order['orderDetails']['productsResults']:
                        if 'productName' in product and 'iphone' in product['productName'].lower():
                            iphone_count += 1
                            break  # Count each order only once
            
            non_iphone_count = orders_count - iphone_count
            
            stats[category] = {
                "orders_count": orders_count,
                "iphone_count": iphone_count,
                "non_iphone_count": non_iphone_count,
            }
        
        return stats

app = FastAPI()

@app.get("/search_orders")
def search_orders_route():
    adam_instance = Adam()
    try:
        stats = adam_instance.search_orders()
        new_orders_count = adam_instance.count_new()
        output_realizowane = f"{stats['realizowane']['non_iphone_count']}"
        output_oczekuje = f"{stats['oczekuje']['non_iphone_count']}"
        output_nie_dodane = f"{new_orders_count}"
        total_combined = stats['wszystko']['non_iphone_count'] + new_orders_count
        output_combined = f"{total_combined}"
        return JSONResponse(content={
            "output_realizowane": output_realizowane,
            "output_oczekuje": output_oczekuje,
            "output_combined": output_combined,
            "output_nie_dodane": output_nie_dodane
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
