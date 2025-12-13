import streamlit as st
import requests
import pandas as pd
from io import BytesIO
import subprocess
import atexit
import os
import sys
import time

st.set_page_config(page_title="Information Extractor", layout="centered")

# --- Server Management ---
import socket
from contextlib import closing

def find_free_port(start_port):
    for port in range(start_port, start_port + 100):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return None

def start_server():
    """Starts the FastAPI server as a background process."""
    if "server_process" not in st.session_state:
        PORT_FILE = ".uvicorn_port"
        DEFAULT_PORT = 8000

        try:
            with open(PORT_FILE, "r") as f:
                port = int(f.read().strip())
        except (IOError, ValueError):
            port = DEFAULT_PORT
        
        free_port = find_free_port(port)
        
        if not free_port:
            st.error(f"Could not find a free port starting from {port}.")
            return

        try:
            with open(PORT_FILE, "w") as f:
                f.write(str(free_port))
        except IOError:
            # Non-critical, we can still proceed
            pass
        
        st.session_state["backend_port"] = free_port

        script_dir = os.path.dirname(os.path.abspath(__file__))
        venv_path = os.path.join(script_dir, "venv")
        
        command = []
        if os.path.exists(venv_path) and sys.platform == "win32":
            python_executable = os.path.join(venv_path, "Scripts", "python.exe")
            command = [
                python_executable, "-m", "uvicorn", "phoneinfoserver:app",
                "--host", "127.0.0.1", "--port", str(free_port)
            ]
        else:
            command = [
                "uvicorn", "phoneinfoserver:app", "--host", "0.0.0.0", "--port", str(free_port)
            ]

        try:
            st.session_state.server_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            time.sleep(3)

            if st.session_state.server_process.poll() is not None:
                st.error("Backend server failed to start. See logs below.")
                stdout, stderr = st.session_state.server_process.communicate()
                st.text("Server stdout:")
                st.code(stdout.decode('utf-8', errors='ignore'))
                st.text("Server stderr:")
                st.code(stderr.decode('utf-8', errors='ignore'))
                st.session_state.server_process = None

        except FileNotFoundError:
            st.error(f"Error: The command '{command[0]}' was not found.")
            st.error("Please ensure that your environment is set up correctly.")
            st.session_state.server_process = None
        except Exception as e:
            st.error(f"An unexpected error occurred while starting the server: {e}")
            st.session_state.server_process = None

def stop_server():
    """Stops the FastAPI server if it's running."""
    if "server_process" in st.session_state:
        st.session_state.server_process.terminate()
        st.session_state.server_process = None

# Start the server when the app starts
start_server()

# Register the stop_server function to be called on exit
atexit.register(stop_server)


def show_login_page():
    st.title("Login")
    
    credentials = {
        "passwords": {
            "m.waseem5196@gamil.com": "waseemkhan"
        }
    }

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if (
            username in credentials["passwords"]
            and password == credentials["passwords"][username]
        ):
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("Invalid username or password")

def show_main_app():
    def logout():
        st.session_state["password_correct"] = False
    
    st.sidebar.button("Logout", on_click=logout)

    port = st.session_state.get("backend_port", 8000)
    SIM_BACKEND_URL = f"http://127.0.0.1:{port}/get-info/"
    VEHICLE_BACKEND_URL = f"http://127.0.0.1:{port}/get-vehicle-info/"

    st.title("🇵🇰 Information Extractor")
    st.markdown("Select the type of information you want to search for.")

    search_type = st.selectbox("Select Search Type", ["SIM Info", "Vehicle Info"])

    st.markdown("---")

    if search_type == "SIM Info":
        st.header("SIM Owner Details (Multiple Search)")

        search_terms = st.text_area(
            "Enter Phone Numbers / CNICs",
            placeholder="03001234567\n03111234567\n3520212345678",
            help="Enter multiple values separated by new line or comma"
        )

        if st.button("🔍 Search SIM Info"):
            raw_items = search_terms.replace(",", "\n").split("\n")
            items = [i.strip() for i in raw_items if i.strip()]

            if not items:
                st.error("Please enter at least one phone number or CNIC.")
            else:
                results = []
                with st.spinner("Fetching SIM data..."):
                    for item in items:
                        if not item.isdigit() or len(item) not in (11, 13):
                            results.append({
                                "Input": item, "Name": "Invalid", "Number": "Invalid",
                                "CNIC": "Invalid", "Address": "Invalid", "Status": "Invalid Format"
                            })
                            continue
                        try:
                            response = requests.post(f"{SIM_BACKEND_URL}?phone_number={item}", timeout=10)
                            data = response.json()
                            if data.get("error"):
                                results.append({
                                    "Input": item, "Name": "", "Number": "", "CNIC": "",
                                    "Address": "", "Status": data["error"]
                                })
                            else:
                                results.append({
                                    "Input": item, "Name": data.get("name", ""), "Number": data.get("number", ""),
                                    "CNIC": data.get("cnic", ""), "Address": data.get("address", ""), "Status": "Found"
                                })
                        except Exception as e:
                            results.append({
                                "Input": item, "Name": "", "Number": "", "CNIC": "",
                                "Address": "", "Status": "Request Failed"
                            })
                df = pd.DataFrame(results)
                st.success(f"Results found: {len(df)}")
                st.dataframe(df, use_container_width=True)
                excel_buffer = BytesIO()
                df.to_excel(excel_buffer, index=False)
                excel_buffer.seek(0)
                st.download_button(
                    label="⬇️ Download Excel", data=excel_buffer,
                    file_name="sim_info_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    elif search_type == "Vehicle Info":
        st.header("Sindh Vehicle Details")
        vehicle_category = st.selectbox("Select Vehicle Category", ["", "2 wheeler", "4 wheeler"])
        reg_number = st.text_input("Enter Registration Number", placeholder="ABC-123")
        if st.button("🔍 Search Vehicle Info"):
            if not reg_number or not vehicle_category:
                st.error("Please select category and enter registration number.")
            else:
                category_map = {"2 wheeler": "2W", "4 wheeler": "4W"}
                api_category = category_map[vehicle_category]
                with st.spinner("Fetching vehicle data..."):
                    try:
                        response = requests.post(
                            f"{VEHICLE_BACKEND_URL}?reg_no={reg_number}&category={api_category}",
                            timeout=10
                        )
                        data = response.json()
                        if data.get("error"):
                            st.error(data["error"])
                        else:
                            vehicle_data = {
                                "Attribute": [
                                    "Registration Number", "Owner Name", "Owner CNIC", "Model",
                                    "Model Year", "Color", "Engine Number", "Chassis Number",
                                    "Registration Date", "CPLC Status", "District", "Branch"
                                ],
                                "Value": [
                                    data.get("registrationNumber"), data.get("ownerName"), data.get("ownerCNIC"),
                                    f"{data.get('manufacturerName', '')} {data.get('modelName', '')}",
                                    data.get("modelYear"), data.get("color"), data.get("engineNumber"),
                                    data.get("chassisNumber"), data.get("registrationDate"),
                                    data.get("cplcStatus"), data.get("districtName"), data.get("branchName"),
                                ]
                            }
                            df = pd.DataFrame(vehicle_data)
                            st.table(df)
                    except Exception as e:
                        st.error("Failed to connect to vehicle backend.")
    st.markdown("""
    ---
    *Disclaimer: This tool uses third-party public APIs. Data accuracy is not guaranteed.*
    """)

def main():
    start_server()
    atexit.register(stop_server)

    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        show_main_app()
    else:
        show_login_page()

if __name__ == "__main__":
    main()