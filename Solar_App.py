# app.py
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
import datetime
import math

# -----------------------
# Branding / Defaults
# -----------------------
BRAND = {
    "name": "Annur Tech 💡",
    "company": "ANNUR TECH SOLAR SOLUTIONS",
    "motto": "Illuminating Innovation",
    "phone": "09051693000",
    "email": "albataskumyjr@gmail.com",
    "address": "No 6 Kolo Drive, Behind Zuma Barrack, Tafa LGA, Niger State, Nigeria",
}

# Common battery unit choices (Ah at given voltage; user can override)
COMMON_BATTERIES = {
    "Lead-Acid 225Ah (Trojan T-105)": 225,
    "Lithium 200Ah (Pylontech US2000 ~200Ah)": 200,
    "Custom (enter Ah below)": None,
}

# -----------------------
# Helper functions (calculations)
# -----------------------
def compute_loads_df(items):
    """items: list of dicts with keys: name,watt,qty,hours"""
    if not items:
        return pd.DataFrame(columns=["name","watt","qty","hours","total_w","daily_Wh"])
    rows = []
    for it in items:
        total_w = it["watt"] * it["qty"]
        daily_wh = total_w * it["hours"]
        rows.append({
            "name": it["name"],
            "watt": it["watt"],
            "qty": it["qty"],
            "hours": it["hours"],
            "total_w": total_w,
            "daily_Wh": daily_wh,
        })
    return pd.DataFrame(rows)

def energy_required_for_backup(total_w, backup_hours, inverter_eff=0.95):
    """Return Wh required from battery (accounting for inverter efficiency)."""
    # If loads are AC via inverter, battery must supply more to cover inverter losses
    return (total_w * backup_hours) / inverter_eff

def battery_ah_for_voltage(energy_wh, battery_voltage, dod=0.8):
    """Energy_wh usable = Ah * V * dod => Ah = energy_wh / (V * dod)"""
    if battery_voltage <= 0 or dod <= 0:
        return None
    return energy_wh / (battery_voltage * dod)

def num_battery_units(ah_required, unit_capacity_ah):
    if unit_capacity_ah is None or unit_capacity_ah <= 0:
        return None
    return ah_required / unit_capacity_ah

def pv_power_to_charge_energy(energy_wh, desired_hours, system_eff=0.75):
    """Return required PV power in W to deliver energy_wh in desired_hours at system efficiency."""
    if desired_hours <= 0:
        return None
    return energy_wh / (desired_hours * system_eff)

def pv_power_from_sunhours(energy_wh, sun_hours, system_eff=0.75):
    """Return PV power (W) required if you have sun_hours/day to deliver energy_wh in one day."""
    return pv_power_to_charge_energy(energy_wh, sun_hours, system_eff)

def panels_needed_from_pv_power(pv_power_w, panel_w=300):
    return pv_power_w / panel_w

def mppt_current_for_pv(pv_power_w, battery_voltage, safety_factor=1.25):
    """Approx. PV current into MPPT: I = Ppv / Vbattery; apply safety factor."""
    if battery_voltage <= 0:
        return None
    return (pv_power_w / battery_voltage) * safety_factor

def recommend_inverter(total_w):
    """Recommend inverter sizing: 1.3x surge factor baseline"""
    return max(total_w * 1.3, 1000)  # at least 1kW recommended

# -----------------------
# Streamlit UI
# -----------------------
st.set_page_config(page_title="Annur Tech Solar Planner", layout="wide", page_icon="💡")
st.title(f"{BRAND['company']}")
st.caption(BRAND["motto"])

# Sidebar: client info & system defaults
with st.sidebar:
    st.header("Project & Client")
    client_name = st.text_input("Client name", "")
    client_phone = st.text_input("Client phone", "")
    client_email = st.text_input("Client email", "")
    client_address = st.text_area("Client address", "", height=80)
    st.markdown("---")

    st.header("System defaults")
    inverter_eff = st.slider("Inverter efficiency (%)", 80, 99, 95) / 100.0
    system_eff = st.slider("PV→Battery system eff (%)", 50, 95, 75) / 100.0
    default_panel_w = st.selectbox("Default panel W", [250, 300, 350, 400], index=1)
    st.markdown("---")
    st.markdown("**Export / PDF**")
    desired_charge_hours = st.number_input("Desired recharge hours (to refill battery)", min_value=1.0, max_value=24.0, value=4.0)
    sun_hours = st.number_input("Peak sun hours (hrs/day)", min_value=1.0, max_value=10.0, value=5.0)

# Main layout
col_a, col_b = st.columns([2,1])

with col_a:
    st.subheader("1) Load audit — add appliances")
    if "loads" not in st.session_state:
        st.session_state.loads = []
    # quick add form
    with st.form("add_load_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([3,1,1,1])
        name = c1.text_input("Appliance", placeholder="e.g. LED light")
        watt = c2.number_input("W (single)", min_value=0.0, value=60.0)
        qty = c3.number_input("Qty", min_value=1, value=1, step=1)
        hours = c4.number_input("Hours/day", min_value=0.0, value=4.0, step=0.5)
        submitted = st.form_submit_button("Add appliance")
        if submitted and name:
            st.session_state.loads.append({"name": name, "watt": watt, "qty": qty, "hours": hours})
            st.success(f"Added {qty} × {name}")

    st.markdown("**Current load list**")
    df_loads = compute_loads_df(st.session_state.loads)
    if not df_loads.empty:
        st.dataframe(df_loads[["name","watt","qty","hours","total_w","daily_Wh"]], use_container_width=True)
        total_w = df_loads["total_w"].sum()
        total_daily_wh = df_loads["daily_Wh"].sum()
        st.metric("Total instant load (W)", f"{total_w:.0f} W")
        st.metric("Total daily energy", f"{total_daily_wh:.0f} Wh/day")
        if st.button("Clear load list"):
            st.session_state.loads = []
            st.experimental_rerun()
    else:
        st.info("Add appliances using the form above (name, W, qty, hours/day).")

with col_b:
    st.subheader("2) Backup & battery targets")
    if "loads" in st.session_state and len(st.session_state.loads) > 0:
        # user inputs for backup
        backup_hours = st.number_input("Required backup hours", min_value=1.0, max_value=168.0, value=4.0)
        st.markdown("**Battery voltage options** — compare results below")
        volt_options = [12, 24, 48]
        dod = st.slider("Depth of Discharge (usable fraction %)", 30, 95, 80) / 100.0

        # compute energy needed (accounting for inverter efficiency)
        total_w = df_loads["total_w"].sum()
        energy_wh = energy_required_for_backup(total_w, backup_hours, inverter_eff)

        st.metric("Energy required from battery", f"{energy_wh:.0f} Wh (including inverter loss)")

        # show battery Ah per voltage
        battery_table = []
        for V in volt_options:
            ah = battery_ah_for_voltage(energy_wh, V, dod)
            battery_table.append({"Voltage (V)": V, "Required Ah": round(ah,1), "Equivalent kWh (usable)": round((ah*V*dod)/1000,3)})
        st.table(pd.DataFrame(battery_table))

        st.markdown("**Choose a battery unit size to compute number of modules**")
        battery_choice = st.selectbox("Common battery unit", list(COMMON_BATTERIES.keys()))
        custom_unit_ah = None
        if COMMON_BATTERIES[battery_choice] is None:
            custom_unit_ah = st.number_input("Enter battery unit capacity (Ah)", min_value=20.0, value=200.0)
            unit_ah = custom_unit_ah
        else:
            unit_ah = COMMON_BATTERIES[battery_choice]

        # compute number of units per voltage
        number_table = []
        for V in volt_options:
            ah_req = battery_ah_for_voltage(energy_wh, V, dod)
            n_units = num_battery_units(ah_req, unit_ah)
            number_table.append({"Voltage (V)": V, "Required Ah": round(ah_req,1), f"Units of {unit_ah}Ah": round(n_units,2)})
        st.table(pd.DataFrame(number_table))
    else:
        st.info("Add loads first to compute battery sizing.")

# -----------------------
# System Sizing (detailed)
# -----------------------
st.markdown("---")
st.header("3) Solar & Charging Planner")

if "loads" in st.session_state and len(st.session_state.loads) > 0:
    # Recompute variables to use below
    total_w = df_loads["total_w"].sum()
    total_daily_wh = df_loads["daily_Wh"].sum()

    # Ask user: do you want to recharge battery in desired_charge_hours or daily with sun_hours?
    st.subheader("How quickly do you want to recharge the battery?")
    charge_mode = st.radio("Charge mode", ["Charge within desired hours (fast)", "Recharge across sun-hours (daily)"])
    # energy to replenish = energy_wh (as computed earlier) — reuse backup_hours and energy_wh if set above
    backup_hours = backup_hours if 'backup_hours' in locals() else 4.0
    energy_wh = energy_required_for_backup(total_w, backup_hours, inverter_eff)

    if charge_mode.startswith("Charge within"):
        desired_hours_local = desired_charge_hours  # from sidebar
        pv_needed_w = pv_power_to_charge_energy(energy_wh, desired_hours_local, system_eff)
        st.write(f"To replenish **{energy_wh:.0f} Wh** in **{desired_hours_local} h** at system efficiency {system_eff*100:.0f}% you need approx:")
        st.metric("PV array power (W)", f"{pv_needed_w:.0f} W")
    else:
        pv_needed_w = pv_power_from_sunhours(energy_wh, sun_hours, system_eff)
        st.write(f"To replenish **{energy_wh:.0f} Wh** across **{sun_hours} sun-hours/day** at system efficiency {system_eff*100:.0f}% you need approx:")
        st.metric("PV array power (W)", f"{pv_needed_w:.0f} W")

    # Panel choices & counts
    panel_w = st.selectbox("Panel watt rating to use for counting", [250,300,350,400], index=[250,300,350,400].index(default_panel_w))
    panels_needed = panels_needed_from_pv_power(pv_needed_w, panel_w)
    st.metric("Panels needed (approx)", f"{math.ceil(panels_needed)} × {panel_w}W")

    # MPPT / Charge controller suggestion
    st.subheader("MPPT / Charge Controller & Inverter")
    mppt_current = mppt_current_for_pv(pv_needed_w, battery_voltage if 'battery_voltage' in locals() else 24, safety_factor=1.25)
    st.write("Assuming battery voltage of 24V (change above in backup section to see other voltages).")
    st.metric("Recommended MPPT input current (A) (incl. 1.25 safety factor)", f"{mppt_current:.1f} A")
    inverter_rec = recommend_inverter(total_w)
    st.metric("Recommended inverter (continuous) size", f"{inverter_rec:.0f} W")
else:
    st.info("Add loads above to see solar & charging planner.")

# -----------------------
# Cost estimate quick view
# -----------------------
st.markdown("---")
st.header("4) Quick Cost Estimate (optional)")
if "loads" in st.session_state and len(st.session_state.loads) > 0:
    # use example unit prices
    avg_panel_price = 100000  # Naira per panel (example)
    avg_battery_price = 250000  # Naira per battery unit (example)
    avg_inverter_price = 200000
    est_panels = math.ceil(panels_needed) if 'panels_needed' in locals() else 0
    est_batteries = math.ceil(num_batteries) if 'num_batteries' in locals() else 0
    est_inverter_cost = avg_inverter_price
    est_solar_cost = est_panels * avg_panel_price
    est_battery_cost = est_batteries * avg_battery_price
    est_total = est_solar_cost + est_battery_cost + est_inverter_cost + 150000
    st.metric("Estimated total system cost (₦)", f"{est_total:,.0f}")
else:
    st.info("Add loads to compute cost estimates.")

# -----------------------
# PDF generation (Report)
# -----------------------
st.markdown("---")
st.header("5) Generate PDF Proposal / Report")

def create_pdf_report(
    client_name,
    client_phone,
    client_email,
    client_address,
    project_location,
    loads,
    total_w,
    total_daily_wh,
    backup_hours,
    energy_wh,
    battery_table,
    chosen_panel_w,
    panels_needed,
    inverter_rec,
    mppt_current
):
    buff = BytesIO()
    c = canvas.Canvas(buff, pagesize=A4)
    w, h = A4

    # Watermark on every page: we'll draw once per page when saving
    def draw_watermark(canv):
        canv.saveState()
        canv.setFont("Helvetica-Bold", 48)
        canv.setFillGray(0.85)
        canv.translate(w/2, h/2)
        canv.rotate(45)
        canv.drawCentredString(0, 0, BRAND["name"])
        canv.restoreState()

    # Page 1 - Cover & summary
    draw_watermark(c)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(30, h-50, BRAND["company"])
    c.setFont("Helvetica", 10)
    c.drawString(30, h-68, BRAND["motto"])
    c.drawString(30, h-82, f"{BRAND['phone']} | {BRAND['email']}")
    c.drawString(30, h-96, BRAND["address"])

    c.setFont("Helvetica-Bold", 14)
    c.drawString(30, h-130, "Client:")
    c.setFont("Helvetica", 11)
    c.drawString(110, h-130, client_name or "Not provided")
    c.drawString(30, h-146, f"Project Location: {project_location}")
    c.drawString(30, h-162, f"Date: {datetime.datetime.now().strftime('%Y-%m-%d')}")

    c.setFont("Helvetica-Bold", 13)
    c.drawString(30, h-190, "System Summary")
    c.setFont("Helvetica", 11)
    c.drawString(30, h-206, f"Total instantaneous load: {total_w:.0f} W")
    c.drawString(30, h-222, f"Total daily energy: {total_daily_wh:.0f} Wh/day")
    c.drawString(30, h-238, f"Backup target: {backup_hours} hours -> Energy to supply: {energy_wh:.0f} Wh")

    # Small table: battery_table (list of dicts per voltage)
    y = h-270
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, y, "Battery sizing by voltage")
    y -= 16
    c.setFont("Helvetica", 10)
    for row in battery_table:
        c.drawString(30, y, f"{row['Voltage (V)']}: Required Ah = {row['Required Ah']:.1f} Ah (usable kWh ≈ {row['Equivalent kWh (usable)']:.3f} kWh)")
        y -= 14

    # Page 2 - Panels & MPPT & Wiring notes
    c.showPage()
    draw_watermark(c)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(30, h-50, "PV & Charging Plan")
    c.setFont("Helvetica", 10)
    c.drawString(30, h-70, f"Recommended PV array size: {pv_needed_w:.0f} W")
    c.drawString(30, h-86, f"Using ~{math.ceil(panels_needed)} × {chosen_panel_w}W panels")
    c.drawString(30, h-102, f"Recommended MPPT current (with safety factor): {mppt_current:.1f} A")
    c.drawString(30, h-118, f"Recommended inverter (continuous): {inverter_rec:.0f} W")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, h-150, "Notes & Wiring (brief)")
    c.setFont("Helvetica", 10)
    c.drawString(30, h-166, "• Panels should be arranged in strings to match MPPT input voltage/current.")
    c.drawString(30, h-182, "• Use PV combiner and string fuses. Size battery cabling per manufacturer's current rating.")
    c.drawString(30, h-198, "• Verify battery manufacturer's max charge current and inverter start-up surge.")

    # Footer on this page
    c.setFont("Helvetica", 9)
    c.drawString(30, 30, f"{BRAND['company']} | {BRAND['phone']} | {BRAND['email']} | {BRAND['address']}")
    c.showPage()

    # Done; ensure watermark on pages already drawn; save
    c.save()
    buff.seek(0)
    return buff

# Button to generate PDF
if st.button("📄 Create professional PDF proposal"):
    if not client_name or not st.session_state.load_data:
        st.error("Please provide client info and add at least one appliance before generating report.")
    else:
        # Prepare tables and arguments for PDF builder
        total_w = df_loads["total_w"].sum()
        total_daily_wh = df_loads["daily_Wh"].sum()
        backup_hours = backup_hours if 'backup_hours' in locals() else 4.0
        energy_wh = energy_required_for_backup(total_w, backup_hours, inverter_eff)

        battery_table = []
        for V in [12,24,48]:
            ah_req = battery_ah_for_voltage(energy_wh, V, dod)
            battery_table.append({
                "Voltage (V)": V,
                "Required Ah": ah_req,
                "Equivalent kWh (usable)": (ah_req*V*dod)/1000
            })

        # choose chosen_panel_w and panels_needed from above context
        chosen_panel_w = panel_w
        panels_needed = panels_needed_from_pv_power(pv_needed_w, chosen_panel_w)
        inverter_rec = recommend_inverter(total_w)
        mppt_current = mppt_current_for_pv(pv_needed_w, 24, safety_factor=1.25)

        pdf_buffer = create_pdf_report(
            client_name, client_phone, client_email, client_address,
            project_location, st.session_state.load_data, total_w,
            total_daily_wh, backup_hours, energy_wh, battery_table,
            chosen_panel_w, panels_needed, inverter_rec, mppt_current
        )
        st.session_state.pdf_data = pdf_buffer
        st.success("PDF proposal generated.")

if st.session_state.get("pdf_data") is not None:
    st.download_button(
        "⬇️ Download generated PDF",
        data=st.session_state["pdf_data"],
        file_name=f"AnnurTech_Proposal_{client_name.replace(' ','_') if client_name else 'client'}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf"
    )

# Footer
st.markdown("---")
st.markdown(f"<div style='text-align:center;color:#666;font-size:12px'>{BRAND['company']} — {BRAND['motto']}<br/>{BRAND['phone']} | {BRAND['email']}<br/>{BRAND['address']}</div>", unsafe_allow_html=True)
