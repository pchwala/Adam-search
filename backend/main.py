import os
import requests
import json
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import gspread
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from DatabaseManager import DatabaseManager
from models import Adam as AdamModel
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


        self.orders_sheet_id = os.environ.get("REFURBED_PLIK")
        if not self.orders_sheet_id:
            self.orders_sheet_id = "15e6oc33_A21dNNv03wqdixYc9_mM2GTQzum9z2HylEg"
            
        self.plikM2 = os.environ.get("M2_M47_PLIK")
        if not self.plikM2:
            raise ValueError("M2_M47_PLIK must be provided as environment variable")

        # Open Orders Google Sheet
        self.orders_sheet = self.client.open_by_key(self.orders_sheet_id).worksheet("Orders")

        self.config_sheet = self.client.open_by_key(self.orders_sheet_id).worksheet("Config")
        
        self.output_sheet = self.client.open_by_key(self.orders_sheet_id).worksheet("Szukajka")

        self.m2_sheet = self.client.open_by_key(self.plikM2).worksheet("Dane")

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

    def read_data_from_M2(self):
        """
        Read data from column C of the M2 sheet.
        
        Returns:
            list: List of values from column C (excluding empty values)
        """
        try:
            # Get all values from column C
            column_c_values = self.m2_sheet.col_values(3)  # Column C is index 3
            
            # Filter out empty values (handle different data types)
            filtered_values = []
            for value in column_c_values:
                if value is not None and str(value).strip():
                    filtered_values.append(value)
            
            # Return only the last 500 non-empty values
            return filtered_values[-500:]
            
        except Exception as e:
            print(f"Error reading column C from M2 sheet: {str(e)}")
            return []
        
    def save_last(self):
        data = self.read_data_from_M2()
        last_value = data[-1] if data else None

        if last_value:
            # Save the last value to cell A7 in config sheet
            self.config_sheet.update(range_name='A7', values=[[last_value]])
            print(f"Last value from M2 saved to Config: {last_value}")
        else:
            raise ValueError("No valid data found in M2.")

    def show_count(self):
        """
        Count how many new values were added to M2 data since the last saved serial number.
        
        Returns:
            int: Number of new values added since last_sn
        """
        try:
            # Get column A from config sheet
            column_a_values = self.config_sheet.col_values(1)  # Column A is index 1
            
            # Get value at row 7 (index 6 since list is 0-indexed)
            last_sn = column_a_values[6] if len(column_a_values) > 6 else None
            
            if not last_sn:
                print("No last_sn found in A7")
                raise ValueError("No last_sn found in A7")
            
            # Get M2 data
            m2_data = self.read_data_from_M2()
            
            if not m2_data:
                print("No M2 data found")
                raise ValueError("No M2 data found")
            
            # Count from the end until we find last_sn
            count = 0
            for i in range(len(m2_data) - 1, -1, -1):  # Start from end, go backwards
                if str(m2_data[i]) == str(last_sn):
                    break
                count += 1
            
            return count
            
        except Exception as e:
            print(f"Error counting daily values: {str(e)}")
            return 0

    def daily_count(self):
        """
        Get daily count, save it to output sheet based on current date, and update last saved value.
        """
        try:
            # Get current date in CEST timezone (UTC+2)
            current_date = datetime.now()
            
            # Get day and month
            day = current_date.day
            month = current_date.month
            
            # Map month number to column letter (B=Jan, C=Feb, ..., M=Dec)
            month_columns = {
                1: 'B',   # January
                2: 'C',   # February
                3: 'D',   # March
                4: 'E',   # April
                5: 'F',   # May
                6: 'G',   # June
                7: 'H',   # July
                8: 'I',   # August
                9: 'J',   # September
                10: 'K',  # October
                11: 'L',  # November
                12: 'M'   # December
            }
            
            # Get the column for current month
            column = month_columns.get(month)
            if not column:
                raise ValueError(f"Invalid month: {month}")
            
            # Calculate row (day + 1 because row 1 is header, so day 1 = row 2, day 25 = row 26)
            row = day + 1
            
            # Get count from show_count method
            count = self.show_count()
            
            # Save to output sheet at calculated cell
            cell_address = f"{column}{row}"
            self.output_sheet.update(range_name=cell_address, values=[[count]])
            
            print(f"Daily count {count} saved to {cell_address} for date {current_date.strftime('%d.%m.%Y')}")
            
            # Save last value
            self.save_last()
            
            return count
            
        except Exception as e:
            print(f"Error in daily_count: {str(e)}")
            raise e

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


# Allow frontend to talk to backend (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://szukajka-ids.web.app"],  # React dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/search_orders")
def search_orders_route():
    adam_instance = Adam()
    db_manager = DatabaseManager()
    try:
        stats = adam_instance.search_orders()
        new_orders_count = adam_instance.count_new()
        wykonane_count = adam_instance.show_count()
        output_realizowane = f"{stats['realizowane']['non_iphone_count']}"
        output_oczekuje = f"{stats['oczekuje']['non_iphone_count']}"
        output_nie_dodane = f"{new_orders_count}"
        output_wykonane = f"{wykonane_count}"
        total_combined = stats['wszystko']['non_iphone_count'] + new_orders_count
        output_combined = f"{total_combined}"

        db_manager.update_adam_record(
            output_realizowane=output_realizowane,
            output_oczekuje=output_oczekuje,
            output_combined=output_combined,
            output_nie_dodane=output_nie_dodane,
            output_wykonane=output_wykonane
        )

        return JSONResponse(
            status_code=200,
            content={"status": "success", "message": "Data updated successfully"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )
    
    
@app.get("/save_daily")
def save_daily():
    adam_instance = Adam()
    try:
        adam_instance.daily_count()
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/get_data")
def get_adam_data():
    db_manager = DatabaseManager()
    try:
        # Get the record with id=1 from the Adam table
        adam_record = db_manager.get_by_id(AdamModel, 1)
        
        if adam_record:
            # Format timestamp to show only time (HH:MM)
            timestamp_str = None
            if hasattr(adam_record, 'created_at') and adam_record.created_at is not None:
                timestamp_str = adam_record.created_at.strftime("%H:%M")
            
            return {
                "output_realizowane": adam_record.realizowane,
                "output_oczekuje": adam_record.oczekuje,
                "output_combined": adam_record.combined,
                "output_nie_dodane": adam_record.nie_dodane,
                "output_wykonane": adam_record.wykonane,
                "timestamp": timestamp_str
            }
        else:
            return {"error": "No record found with id=1"}
            
    except Exception as e:
        return {"error": str(e)}

    
    