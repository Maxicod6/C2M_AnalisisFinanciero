import streamlit as st
import pandas as pd
from datetime import datetime

def show_socios(dm):
    st.header("Control de Socios")

    tab1, tab2 = st.tabs(["Resumen Aportes", "Registrar Nuevo Aporte"])

    with tab1:
        st.subheader("Capital Aportado por Socio")
        df_socios = dm.get_socios()
        
        if not df_socios.empty:
            # Group by Socio and Sum Monto
            # Ensure Monto is numeric
            df_socios['Monto'] = pd.to_numeric(df_socios['Monto'], errors='coerce').fillna(0)
            resumen = df_socios.groupby("Socio")['Monto'].sum().reset_index()
            resumen = resumen.sort_values(by="Monto", ascending=False)
            
            st.dataframe(resumen, hide_index=True, use_container_width=True)
            
            # Chart
            import plotly.express as px
            st.subheader("Distribución de Capital")
            fig = px.pie(resumen, values='Monto', names='Socio', title="Capital por Socio", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("Ver detalle completo de movimientos"):
                st.dataframe(df_socios)
        else:
            st.info("No hay registros de socios aún.")

    with tab2:
        st.subheader("Nuevo Aporte / Movimiento")
        with st.form("form_socios"):
            date = st.date_input("Fecha", datetime.today())
            socio = st.text_input("Nombre del Socio")
            tipo = st.selectbox("Tipo", ["Aporte Capital", "Préstamo", "Retiro"])
            monto = st.number_input("Monto", min_value=0.0, format="%.2f")
            desc = st.text_area("Descripción")
            url = st.text_input("URL Comprobante (opcional)")
            
            submitted = st.form_submit_button("Registrar")
            if submitted:
                if socio and monto > 0:
                    new_row = {
                        "Fecha": date.strftime("%Y-%m-%d"),
                        "Socio": socio,
                        "Tipo_Aporte": tipo,
                        "Monto": monto,
                        "Descripción": desc,
                        "Comprobante_URL": url
                    }
                    dm.add_row("Socios", new_row)
                    st.success("Movimiento registrado correctamente!")
                    st.rerun()
                else:
                    st.warning("Completa los campos obligatorios (Socio, Monto).")
