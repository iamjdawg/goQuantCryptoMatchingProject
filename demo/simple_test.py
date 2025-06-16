import requests
import json
import time

def test_rest_api():
    """Simple REST API test"""
    base_url = "http://localhost:8000/api/v1"
    
    print("Testing REST API...")
    
    # Test order submission
    order_data = {
        'symbol': 'BTC-USDT',
        'side': 'buy',
        'order_type': 'limit',
        'quantity': '1.0',
        'price': '50000.00'
    }
    
    try:
        response = requests.post(f"{base_url}/orders", json=order_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Order submitted successfully: {result['order_id']}")
            order_id = result['order_id']
            
            # Test order status
            status_response = requests.get(f"{base_url}/orders/{order_id}")
            if status_response.status_code == 200:
                print(f"✓ Order status retrieved: {status_response.json()['status']}")
            
        else:
            print(f"Order submission failed: {response.status_code}")
    
    except requests.exceptions.ConnectionError:
        print("Cannot connect to REST API. Make sure the server is running on port 8000")
    except Exception as e:
        print(f" Error: {e}")
    
    # Test BBO endpoint
    try:
        bbo_response = requests.get(f"{base_url}/bbo/BTC-USDT")
        if bbo_response.status_code == 200:
            bbo = bbo_response.json()
            print(f"BBO retrieved - Bid: {bbo.get('best_bid')}, Ask: {bbo.get('best_ask')}")
    except Exception as e:
        print(f"BBO test failed: {e}")

if __name__ == "__main__":
    test_rest_api()