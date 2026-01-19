import streamlit as st
import pandas as pd

# Page Config must be first
st.set_page_config(
    page_title="Control Financiero ERP",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Imports
try:
    from modules.data_manager import DataManager
    from modules.views.dashboard import show_dashboard
    from modules.views.gastos import show_gastos
    from modules.views.inventory import show_inventory
    from modules.views.sales import show_sales
    from modules.views.clients import show_clients
except ImportError as e:
    st.error(f"Error importando módulos: {e}")
    st.stop()

# Styles
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("assets/style.css")

def main():
    # Sidebar Logo
    st.sidebar.image("assets/logo.jpg", use_container_width=True)
    st.sidebar.title("💰 CSM ControlFin")
    
    # Navigation
    menu = st.sidebar.radio(
        "Navegación",
        ["Dashboard", "Clientes", "Gestión de Gastos", "Inventario y Compras", "Ventas y Cobros"]
    )

    st.sidebar.divider()
    st.sidebar.info("v1.1 - ERP Ligero")

    # Initialize Data Manager
    try:
        dm = DataManager()
    except Exception as e:
        st.error(f"Error conectando a la base de datos: {e}")
        st.stop()

    # Routing
    if menu == "Dashboard":
        show_dashboard(dm)
    elif menu == "Clientes":
        show_clients(dm)
    elif menu == "Gestión de Gastos":
        show_gastos(dm)
    elif menu == "Inventario y Compras":
        show_inventory(dm)
    elif menu == "Ventas y Cobros":
        show_sales(dm)

if __name__ == "__main__":
    main()
