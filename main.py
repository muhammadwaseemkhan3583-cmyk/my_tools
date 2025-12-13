import streamlit as st
import requests
import pandas as pd
from io import BytesIO
import subprocess
import atexit

st.set_page_config(page_title="Information Extractor", layout="centered")

# --- Server Management ---
def start_server():
    """Starts the FastAPI server as a background process."""
    if "server_process" not in st.session_state:
        st.session_state.server_process = subprocess.Popen(
            ["uvicorn", "phoneinfoserver:app"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        st.info("Starting backend server...")

def stop_server():
    """Stops the FastAPI server if it's running."""
    if "server_process" in st.session_state:
        st.session_state.server_process.terminate()
        st.session_state.server_process = None

# Start the server when the app starts
start_server()

# Register the stop_server function to be called on exit
atexit.register(stop_server)


def check_password():
    """Returns `True` if the user had a correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if (
            st.session_state["username"] in st.secrets["passwords"]
            and st.session_state["password"]
            == st.secrets["passwords"][st.session_state["username"]]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show inputs for username + password.
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 User not known or password incorrect")
        return False
    else:
        # Password correct.
        return True

# Create a secrets.toml file with the following content:
# [passwords]
# m.waseem5196@gamil.com = "waseemkhan"
if "secrets" not in st.session_state:
    st.secrets = {"passwords": {"m.waseem5196@gamil.com": "waseemkhan"}}

if check_password():
    # FastAPI backend URLs
    SIM_BACKEND_URL = "http://127.0.0.1:8000/get-info/"
    VEHICLE_BACKEND_URL = "http://127.0.0.1:8000/get-vehicle-info/"

    st.title("🇵🇰 Information Extractor")
    st.markdown("Select the type of information you want to search for.")

    # --- Search Type Selector ---
    search_type = st.selectbox("Select Search Type", ["SIM Info", "Vehicle Info"])

    st.markdown("---")

    # ---------------- SIM INFO ----------------
    if search_type == "SIM Info":
        st.header("SIM Owner Details (Multiple Search)")

        search_terms = st.text_area(
            "Enter Phone Numbers / CNICs",
            placeholder="03001234567\n03111234567\n3520212345678",
            help="Enter multiple values separated by new line or comma"
        )

        if st.button("🔍 Search SIM Info"):
            # Parse input
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
                                "Input": item,
                                "Name": "Invalid",
                                "Number": "Invalid",
                                "CNIC": "Invalid",
                                "Address": "Invalid",
                                "Status": "Invalid Format"
                            })
                            continue

                        try:
                            response = requests.post(
                                f"{SIM_BACKEND_URL}?phone_number={item}",
                                timeout=10
                            )
                            data = response.json()

                            if data.get("error"):
                                results.append({
                                    "Input": item,
                                    "Name": "",
                                    "Number": "",
                                    "CNIC": "",
                                    "Address": "",
                                    "Status": data["error"]
                                })
                            else:
                                results.append({
                                    "Input": item,
                                    "Name": data.get("name", ""),
                                    "Number": data.get("number", ""),
                                    "CNIC": data.get("cnic", ""),
                                    "Address": data.get("address", ""),
                                    "Status": "Found"
                                })

                        except Exception as e:
                            results.append({
                                "Input": item,
                                "Name": "",
                                "Number": "",
                                "CNIC": "",
                                "Address": "",
                                "Status": "Request Failed"
                            })

                df = pd.DataFrame(results)
                st.success(f"Results found: {len(df)}")
                st.dataframe(df, use_container_width=True)

                # -------- Excel Download --------
                excel_buffer = BytesIO()
                df.to_excel(excel_buffer, index=False)
                excel_buffer.seek(0)

                st.download_button(
                    label="⬇️ Download Excel",
                    data=excel_buffer,
                    file_name="sim_info_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    # ---------------- VEHICLE INFO ----------------
    elif search_type == "Vehicle Info":
        st.header("Sindh Vehicle Details")

        vehicle_category = st.selectbox(
            "Select Vehicle Category",
            ["", "2 wheeler", "4 wheeler"]
        )

        reg_number = st.text_input(
            "Enter Registration Number",
            placeholder="ABC-123"
        )

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
                                    "Registration Number", "Owner Name", "Owner CNIC",
                                    "Model", "Model Year", "Color", "Engine Number",
                                    "Chassis Number", "Registration Date", "CPLC Status",
                                    "District", "Branch"
                                ],
                                "Value": [
                                    data.get("registrationNumber"),
                                    data.get("ownerName"),
                                    data.get("ownerCNIC"),
                                    f"{data.get('manufacturerName', '')} {data.get('modelName', '')}",
                                    data.get("modelYear"),
                                    data.get("color"),
                                    data.get("engineNumber"),
                                    data.get("chassisNumber"),
                                    data.get("registrationDate"),
                                    data.get("cplcStatus"),
                                    data.get("districtName"),
                                    data.get("branchName"),
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