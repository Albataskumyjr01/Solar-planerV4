import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

# ===== Helper Functions =====
def calculate_solar(needs_watt, hours, battery_voltage, battery_dod, inverter_eff, solar_irradiance, panel_watt):
    # Daily energy need
    daily_energy = needs_watt * hours  

    # Battery capacity (Ah)
    battery_capacity_ah = (daily_energy / (battery_voltage * battery_dod * inverter_eff))

    # Total solar panel capacity
    total_panel_capacity = daily_energy / (solar_irradiance * inverter_eff)

    # Number of panels
    num_panels = total_panel_capacity / panel_watt

    return daily_energy, battery_capacity_ah, total_panel_capacity, num_panels


def generate_pdf(data):
    file_name = f"solar_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    c = canvas.Canvas(file_name, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, height - 50, "Solar System Sizing Report")

    c.setFont("Helvetica", 12)
    y = height - 100
    for key, value in data.items():
        c.drawString(50, y, f"{key}: {value}")
        y -= 20

    c.save()
    return file_name


# ===== Streamlit App =====
st.set_page_config(page_title="Solar Planner", layout="centered")
st.title("☀️ Solar Power Planner")

st.subheader("Enter Your Load Details")

needs_watt = st.number_input("Total Load (Watts)", min_value=10, value=500)
hours = st.number_input("Hours of Load per Day", min_value=1, value=5)
battery_voltage = st.number_input("Battery Voltage (V)", min_value=12, value=24)
battery_dod = st.slider("Battery Depth of Discharge (%)", 0.1, 1.0, 0.8)
inverter_eff = st.slider("Inverter Efficiency (%)", 0.5, 1.0, 0.9)
solar_irradiance = st.number_input("Average Sun Hours per Day", min_value=1.0, value=5.0)
panel_watt = st.number_input("Solar Panel Watt Rating", min_value=50, value=300)

if st.button("Calculate"):
    daily_energy, battery_capacity_ah, total_panel_capacity, num_panels = calculate_solar(
        needs_watt, hours, battery_voltage, battery_dod, inverter_eff, solar_irradiance, panel_watt
    )

    st.success("✅ Calculation Complete!")

    st.metric("Daily Energy Need", f"{daily_energy:.0f} Wh")
    st.metric("Required Battery Capacity", f"{battery_capacity_ah:.0f} Ah")
    st.metric("Total Panel Capacity", f"{total_panel_capacity:.0f} W")
    st.metric("Number of Panels", f"{num_panels:.0f}")

    report_data = {
        "Daily Energy (Wh)": f"{daily_energy:.0f}",
        "Battery Capacity (Ah)": f"{battery_capacity_ah:.0f}",
        "Total Panel Capacity (W)": f"{total_panel_capacity:.0f}",
        "Number of Panels": f"{num_panels:.0f}",
    }

    if st.button("📄 Download Report as PDF"):
        pdf_file = generate_pdf(report_data)
        with open(pdf_file, "rb") as file:
            st.download_button(
                label="⬇️ Download PDF",
                data=file,
                file_name=pdf_file,
                mime="application/pdf"
    )
