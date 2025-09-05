import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO
import datetime
import math

# Branding info
COMPANY = "ANNUR TECH SOLAR SOLUTIONS"
MOTTO = "Illuminating Nigeria's Future"
ADDRESS = "No 6 Kolo Drive, Behind Zuma Barrack, Tafa LGA, Niger State, Nigeria"
PHONE = "+234 905 169 3000"
EMAIL = "albataskumyjr@gmail.com"

# Nigerian-specific component database
NIGERIAN_SOLAR_PANELS = {
    "Jinko Tiger 350W": {"price": 85000, "vmp": 35.5},
    "Canadian Solar 400W": {"price": 105000, "vmp": 37.2},
    "Trina Solar 450W": {"price": 125000, "vmp": 39.8},
}

NIGERIAN_BATTERIES = {
    "Trojan T-105 (225Ah)": {"price": 65000, "capacity": 225},
    "Pylontech US2000 (200Ah)": {"price": 280000, "capacity": 200},
}

NIGERIAN_INVERTERS = {
    "Growatt 3000W 24V": {"price": 185000, "power": 3000, "voltage": 24},
    "Victron 5000W 48V": {"price": 450000, "power": 5000, "voltage": 48},
}

# Common Nigerian appliances
NIGERIAN_APPLIANCES = {
    "Ceiling Fan": 75,
    "Standing Fan": 55,
    "TV (32-inch LED)": 50,
    "TV (42-inch LED)": 80,
    "Refrigerator (Medium)": 150,
    "Deep Freezer": 200,
    "Air Conditioner (1HP)": 750,
    "Air Conditioner (1.5HP)": 1100,
    "Water Pump (1HP)": 750,
    "Lighting (LED Bulb)": 10,
}

st.set_page_config(page_title="Annur Tech Solar Planner", layout="wide", page_icon="☀️")

# Custom CSS
st.markdown(f"""
<style>
    .main .block-container {{
        padding-top: 2rem;
    }}
    .stApp {{
        background-color: #f8f9fa;
    }}
    .green-header {{
        background-color: #006400;
        color: white;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
    }}
    .input-label {{
        font-weight: bold;
        margin-bottom: 5px;
        display: block;
    }}
    .help-text {{
        font-size: 12px;
        color: #666;
        font-style: italic;
        margin-top: 3px;
    }}
</style>
""", unsafe_allow_html=True)

# App header
st.markdown(f'<div class="green-header"><h1>⚡ {COMPANY}</h1></div>', unsafe_allow_html=True)
st.markdown(f'<h3 style="text-align: center; color: #006400;">{MOTTO}</h3>', unsafe_allow_html=True)

# Sidebar client info
st.sidebar.markdown(f'<div class="green-header"><h3>👤 Client Information</h3></div>', unsafe_allow_html=True)

with st.sidebar:
    with st.expander("Client Details", expanded=True):
        client_name = st.text_input("Full Name", placeholder="Enter client's full name", key="client_name")
        client_address = st.text_area("Address", placeholder="Enter complete address", key="client_address")
        client_phone = st.text_input("Phone Number", placeholder="e.g., 08012345678", key="client_phone")
        client_email = st.text_input("Email Address", placeholder="client@example.com", key="client_email")
        project_location = st.selectbox("Project Location", ["Abuja", "Lagos", "Kano", "Port Harcourt", "Kaduna", "Other"], key="project_location")

# Session state init
if "load_data" not in st.session_state:
    st.session_state.load_data = []
if "pdf_data" not in st.session_state:
    st.session_state.pdf_data = None

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["🔋 Load Audit", "⚡ System Sizing", "💰 Cost Estimate", "📋 Report"])

# ====== TAB 1 - LOAD AUDIT ======
with tab1:
    st.markdown(f'<div class="green-header"><h3>🔋 Load Audit & Energy Assessment</h3></div>', unsafe_allow_html=True)
    
    with st.expander("Quick Add Common Appliances", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="input-label">Select Common Appliance</div>', unsafe_allow_html=True)
            selected_appliance = st.selectbox("Select appliance", list(NIGERIAN_APPLIANCES.keys()), key="appliance_select", label_visibility="collapsed")
        with col2:
            appliance_wattage = st.number_input("Wattage", value=NIGERIAN_APPLIANCES[selected_appliance], key="appliance_wattage", label_visibility="collapsed")
        
        col3, col4 = st.columns(2)
        with col3:
            appliance_quantity = st.number_input("Quantity", 1, 100, 1, key="appliance_quantity", label_visibility="collapsed")
        with col4:
            appliance_hours = st.number_input("Hours", 0.0, 24.0, 5.0, key="appliance_hours", label_visibility="collapsed")
        
        add_appliance = st.button("➕ Add Appliance to Load List", use_container_width=True, key="add_appliance_btn")

    with st.expander("Custom Appliance Entry", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        custom_appliance = col1.text_input("Appliance name", placeholder="e.g., Water Dispenser", key="custom_name", label_visibility="collapsed")
        custom_watt = col2.number_input("Custom wattage", 0, 5000, 100, key="custom_watt_input", label_visibility="collapsed")
        custom_quantity = col3.number_input("Custom quantity", 1, 100, 1, key="custom_quantity_input", label_visibility="collapsed")
        custom_hours = col4.number_input("Custom hours", 0.0, 24.0, 5.0, key="custom_hours_input", label_visibility="collapsed")
        add_custom = st.button("➕ Add Custom Appliance", use_container_width=True, key="add_custom_btn")

    # Add appliances to load list
    if add_appliance and selected_appliance:
        total_watt = appliance_wattage * appliance_quantity
        daily_wh = total_watt * appliance_hours
        st.session_state.load_data.append({
            "appliance": selected_appliance,
            "watt": appliance_wattage,
            "quantity": appliance_quantity,
            "total_watt": total_watt,
            "hours": appliance_hours,
            "wh": daily_wh
        })
        st.success(f"Added {appliance_quantity} × {selected_appliance}")

    if add_custom and custom_appliance:
        total_watt = custom_watt * custom_quantity
        daily_wh = total_watt * custom_hours
        st.session_state.load_data.append({
            "appliance": custom_appliance,
            "watt": custom_watt,
            "quantity": custom_quantity,
            "total_watt": total_watt,
            "hours": custom_hours,
            "wh": daily_wh
        })
        st.success(f"Added {custom_quantity} × {custom_appliance}")

    # Display load summary
    if st.session_state.load_data:
        st.markdown("---")
        st.subheader("📊 Load Summary")
        total_wh = sum(item["wh"] for item in st.session_state.load_data)
        total_watt = sum(item["total_watt"] for item in st.session_state.load_data)
        df = pd.DataFrame(st.session_state.load_data)

        col1, col2 = st.columns(2)
        col1.plotly_chart(px.pie(df, values='wh', names='appliance', title='Energy Consumption by Appliance'), use_container_width=True)
        col2.plotly_chart(px.bar(df, x='appliance', y='wh', title='Daily Energy Consumption (Wh)'), use_container_width=True)

        st.dataframe(df, use_container_width=True)
        st.metric("Total Power Demand", f"{total_watt} W")
        st.metric("Total Daily Energy Consumption", f"{total_wh} Wh")

        if st.button("🗑️ Clear All Items", use_container_width=True, key="clear_items_btn"):
            st.session_state.load_data = []
            st.session_state.pdf_data = None
            st.rerun()
    else:
        st.info("👆 Add appliances to your load list to see the summary here.")

# ====== TAB 2 - SYSTEM SIZING ======
with tab2:
    st.markdown(f'<div class="green-header"><h3>⚡ System Sizing & Component Selection</h3></div>', unsafe_allow_html=True)
    
    if not st.session_state.load_data:
        st.warning("Please add appliances in the Load Audit tab first.")
    else:
        total_wh = sum(item["wh"] for item in st.session_state.load_data)
        total_watt = sum(item["total_watt"] for item in st.session_state.load_data)

        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Battery System")
            backup_time = st.slider("Backup time required (hours)", 1, 24, 5)
            battery_voltage = st.selectbox("System voltage", [12, 24, 48], index=1)
            dod_limit = st.slider("Depth of Discharge (%)", 50, 100, 80)
            
            try:
                battery_capacity_ah = (total_wh * backup_time) / (battery_voltage * (dod_limit/100))
                battery_type = st.selectbox("Battery technology", list(NIGERIAN_BATTERIES.keys()))
                battery_info = NIGERIAN_BATTERIES[battery_type]
                num_batteries = battery_capacity_ah / battery_info["capacity"]

                st.metric("Required Battery Capacity", f"{battery_capacity_ah:.0f} Ah")
                st.metric("Number of Batteries Needed", f"{num_batteries:.1f}")
            except:
                st.warning("⚠️ Unable to calculate battery requirements.")

        with col2:
            st.subheader("Solar Panel System")
            sun_hours = st.slider("Sun hours per day (Nigeria average)", 3.0, 8.0, 5.0)
            system_efficiency = st.slider("System efficiency (%)", 50, 95, 75)
            panel_type = st.selectbox("Solar panel type", list(NIGERIAN_SOLAR_PANELS.keys()))
            panel_info = NIGERIAN_SOLAR_PANELS[panel_type]
            
            try:
                required_solar = total_wh / (sun_hours * (system_efficiency/100))
                num_panels = required_solar / panel_info["vmp"] * (battery_voltage/panel_info["vmp"])
                controller_current = (required_solar * 1.25) / battery_voltage

                st.metric("Required Solar Capacity", f"{required_solar:.0f} W")
                st.metric("Number of Panels Needed", f"{num_panels:.1f}")
                st.metric("Charge Controller Size", f"{controller_current:.0f} A")
            except:
                st.warning("⚠️ Unable to calculate solar requirements.")

        st.subheader("Inverter Selection")
        try:
            inverter_size = max(total_watt * 1.3, 1000)
            selected_inverter = st.selectbox("Choose inverter", list(NIGERIAN_INVERTERS.keys()))
            inverter_info = NIGERIAN_INVERTERS[selected_inverter]

            st.metric("Recommended Inverter Size", f"{inverter_size:.0f} W")
            st.metric("Selected Inverter", selected_inverter)
        except:
            st.warning("⚠️ Unable to calculate inverter requirements.")

# ====== TAB 3 - COST ESTIMATION ======
with tab3:
    st.markdown(f'<div class="green-header"><h3>💰 Cost Estimation</h3></div>', unsafe_allow_html=True)
    
    if not st.session_state.load_data:
        st.warning("Please add appliances in the Load Audit tab first.")
    else:
        try:
            battery_cost = math.ceil(num_batteries) * battery_info["price"]
            solar_cost = math.ceil(num_panels) * panel_info["price"]
            inverter_cost = inverter_info["price"]
            installation_cost = max(150000, (battery_cost + solar_cost + inverter_cost) * 0.2)
            total_cost = battery_cost + solar_cost + inverter_cost + installation_cost

            col1, col2, col3 = st.columns(3)
            col1.metric("Battery Cost", f"₦{battery_cost:,.0f}")
            col2.metric("Solar Panel Cost", f"₦{solar_cost:,.0f}")
            col3.metric("Inverter Cost", f"₦{inverter_cost:,.0f}")

            st.metric("Installation & Miscellaneous", f"₦{installation_cost:,.0f}")
            st.metric("Estimated Total System Cost", f"₦{total_cost:,.0f}")
        except:
            st.warning("⚠️ Cost calculation failed. Ensure system sizing was successful.")

# ====== TAB 4 - REPORT ======
with tab4:
    st.markdown(f'<div class="green-header"><h3>📋 Professional Report</h3></div>', unsafe_allow_html=True)
    
    if not client_name or not st.session_state.load_data:
        st.warning("Please fill in client information and add at least one appliance first.")
    else:
        def create_professional_pdf():
            buffer = BytesIO()
            pdf_content = f"""
            {COMPANY}
            {MOTTO}

            CLIENT INFORMATION
            ==================
            Name: {client_name}
            Address: {client_address}
            Phone: {client_phone}
            Email: {client_email if client_email else "Not provided"}
            Location: {project_location}
            Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}

            Total Energy Demand: {total_wh} Wh/day
            Total Power Demand: {total_watt} W

            SYSTEM SIZING
            =============
            Backup Time: {backup_time} hours
            Battery Voltage: {battery_voltage}V
            Battery Capacity: {battery_capacity_ah:.0f} Ah
            Battery Type: {battery_type}
            Solar Panel Type: {panel_type}
            Required Solar Capacity: {required_solar:.0f} W
            Number of Panels: {num_panels:.1f}
            Charge Controller Size: {controller_current:.0f} A
            Inverter Size: {inverter_size:.0f} W
            Inverter Type: {selected_inverter}

            FINANCIAL ANALYSIS
            =================
            Battery Cost: ₦{battery_cost:,.0f}
            Solar Panel Cost: ₦{solar_cost:,.0f}
            Inverter Cost: ₦{inverter_cost:,.0f}
            Installation Cost: ₦{installation_cost:,.0f}
            TOTAL SYSTEM COST: ₦{total_cost:,.0f}

            TERMS & CONDITIONS
            ==================
            Quote Validity: 30 days
            Warranty: Manufacturer warranty + 1 year workmanship
            Payment Terms: 50% advance, 50% upon completion
            Installation Timeline: 5-7 working days
            Service: 6 months free maintenance included

            {COMPANY} | {PHONE} | {EMAIL}
            {ADDRESS}
            """
            buffer.write(pdf_content.encode('utf-8'))
            buffer.seek(0)
            return buffer

        if st.button("📄 Generate Professional Quotation PDF", use_container_width=True):
            st.session_state.pdf_data = create_professional_pdf()
            st.success("Professional quotation generated successfully!")

        if st.session_state.pdf_data is not None:
            st.download_button(
                "📥 Download Professional Quotation",
                data=st.session_state.pdf_data,
                file_name=f"AnnurTech_Quotation_{client_name.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

# Footer
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #666; font-size: 12px;">
    {COMPANY} | {PHONE} | {EMAIL}<br/>
    {ADDRESS}<br/>
    © {datetime.datetime.now().year} Annur Tech Solar Solutions
</div>
""", unsafe_allow_html=True)
