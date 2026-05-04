import requests
import json

def run_demo(query):
    url = "http://127.0.0.1:8000/api/v1/query"
    payload = {
        "messages": [
            {"role": "user", "content": query}
        ]
    }
    
    print(f"\n--- Query: {query} ---")
    print("Response: ", end="", flush=True)
    
    try:
        # Use stream=True to handle Server-Sent Events (SSE)
        with requests.post(url, json=payload, stream=True) as response:
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        content = decoded_line[6:] # Remove 'data: ' prefix
                        try:
                            # Try to parse as JSON if it's an error or structured event
                            data = json.loads(content)
                            if "message" in data:
                                print(f"\n[ERROR/SYSTEM]: {data['message']}")
                        except json.JSONDecodeError:
                            # If it's just a text chunk, print it
                            print(content, end="", flush=True)
    except Exception as e:
        print(f"\nCould not connect to server: {e}")

if __name__ == "__main__":
    print("Valura AI Demo Client")
    print("Make sure your server is running with: python -m uvicorn src.main:app")
    
    # Example 1: Successful Portfolio Analysis
    run_demo("How is Apple (AAPL) performing today? Should I be worried about my portfolio health?")
    
    # Example 2: Safety Violation
    # run_demo("Can you give me some insider trading tips for Tesla?")
