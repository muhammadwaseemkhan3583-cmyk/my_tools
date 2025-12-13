from fastapi import FastAPI
import requests

app = FastAPI()

@app.post("/get-info/")
async def get_phone_info(phone_number: str):
    # This new website has a direct API endpoint we can call
    api_url = "https://simdataupdates.com/wp-admin/admin-ajax.php"
    params = {
        'action': 'fetch_sim_data',
        'term': phone_number
    }
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': 'https://simdataupdates.com/',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    try:
        # The request is a simple GET request
        
        response = requests.get(
            api_url,
            params=params,
            headers=headers,
            timeout=10
        )

        # 1️⃣ HTTP check
        if response.status_code != 200:
            print("STATUS:", response.status_code)
            return {"error": f"HTTP Error {response.status_code}"}

        # 2️⃣ Empty response check
        if not response.text or len(response.text.strip()) == 0:
            return {"error": "Empty response from website (blocked)"}

        # 3️⃣ Content-Type check
        content_type = response.headers.get("content-type", "")
        print("TYPE:", response.headers.get("content-type"))
        if "application/json" not in content_type:
            return {
                "error": "Non-JSON response received (likely blocked)",
                "preview": response.text[:200]
            }

        # 4️⃣ Now safe to parse JSON
        try:
            data = response.json()
        except ValueError:


            print("STATUS:", response.status_code)
            print("TYPE:", response.headers.get("content-type"))
            print("BODY:", response.text[:300])

            return {"error": "Invalid JSON response"}

            
        
        # Check if the API call was successful and if any data was returned
        if data.get("success") and data.get("data") and len(data["data"]) > 0:
            # We will return the first record found
            info = data["data"][0]
            return {
                "name": info.get("name"),
                "number": info.get("number"),
                "cnic": info.get("cnic"),
                "address": info.get("address")
            }
        else:
            return {"error": "No record found for this number."}

    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to retrieve data from the website: {e}"}
    except ValueError:
        # Catches JSON decoding errors if the response is not valid JSON
        return {"error": "Failed to decode the response from the server. The API might be down or has changed."}

@app.post("/get-vehicle-info/")
async def get_vehicle_info(reg_no: str, category: str):
    api_url = "https://api.mahisite.xyz/sindh/api.php"
    params = {
        'reg_no': reg_no,
        'category': category
    }

    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        
        data = response.json()

        if data.get("statusCode") == 0 and data.get("data") and len(data["data"]) > 0:
            info = data["data"][0]
            return {
                "registrationNumber": info.get("registrationNumber"),
                "ownerName": info.get("ownerName"),
                "ownerCNIC": info.get("ownerCNIC"),
                "ownerAddress": info.get("ownerAddress"),
                "registrationDate": info.get("registrationDate"),
                "engineNumber": info.get("engineNumber"),
                "chassisNumber": info.get("chassisNumber"),
                "branchName": info.get("branchName"),
                "districtName": info.get("districtName"),
                "modelYear": info.get("modelYear"),
                "manufacturerName": info.get("manufacturerName"),
                "modelName": info.get("modelName"),
                "color": info.get("color"),
                "cplcStatus": info.get("cplcStatus"),
            }
        else:
            return {"error": "No vehicle record found."}

    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to retrieve data from the vehicle API: {e}"}
    except ValueError:
        return {"error": "Failed to decode the response from the vehicle API server."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
