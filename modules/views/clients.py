import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

def show_clients(dm):
    st.header("Clientes 360")

    # Load Data
    cobros_df = dm.get_cobros()
    clientes_df = dm.get_clientes()
    
    # helper for view
    start_clients_view(cobros_df, clientes_df)

def start_clients_view(cobros_df, clientes_df):
    
    tab1, tab2 = st.tabs(["📊 Dashboard 360", "📇 Directorio de Clientes"])
    
    with tab1:
        if cobros_df.empty:
            st.info("No hay datos de cobros/ventas disponibles para generar el dashboard.")
        else:
            # Get unique clients from SALES history
            clientes_ventas = sorted(cobros_df['Cliente'].unique())
            selected_client = st.selectbox("Seleccionar Cliente", clientes_ventas)
            
            if selected_client:
                # Show Contact Info if available
                if not clientes_df.empty and 'Nombre' in clientes_df.columns:
                    info = clientes_df[clientes_df['Nombre'] == selected_client]
                    if not info.empty:
                        with st.expander(f"ℹ️ Información de Contacto: {selected_client}", expanded=True):
                            c1, c2, c3 = st.columns(3)
                            row = info.iloc[0]
                            c1.markdown(f"**🆔 CUIT:** {row.get('CUIT', '-')}")
                            c1.markdown(f"**📞 Teléfono:** {row.get('Telefono', '-')}")
                            
                            c2.markdown(f"**✉️ Email:** {row.get('Email', '-')}")
                            c2.markdown(f"**📍 Localidad:** {row.get('Localidad', '-')}")
                            
                            c3.markdown(f"**🏠 Dirección:** {row.get('Direccion', '-')}")
                            
                            if row.get('Notas'):
                                st.markdown(f"**📝 Notas:** {row.get('Notas')}")

                # Filter for client
                # Ensure Numeric cols
                cols_to_numeric = ['Monto_Total']
                for col in cols_to_numeric:
                    cobros_df[col] = pd.to_numeric(cobros_df[col], errors='coerce').fillna(0)
                
                # ... (rest of Dashboard Logic remains) ...
                client_data = cobros_df[cobros_df['Cliente'] == selected_client].copy() # Continue existing logic

        
                # Calculate KPIs
                total_facturado = client_data['Monto_Total'].sum()
                
                pagados = client_data[client_data['Estado'] == 'Pagado']
                total_pagado = pagados['Monto_Total'].sum()
                
                pendientes = client_data[client_data['Estado'] == 'Pendiente']
                deuda_pendiente = pendientes['Monto_Total'].sum()
                
                # Display Cards (Custom CSS style)
                st.markdown(f"""
                <div style="display: flex; gap: 20px; margin-bottom: 20px;">
                    <div data-testid="metric-container" style="flex: 1;">
                        <p style="font-size: 14px; color: #666;">Total Facturado</p>
                        <h2 style="margin: 0;">${total_facturado:,.2f}</h2>
                    </div>
                    <div data-testid="metric-container" style="flex: 1;">
                        <p style="font-size: 14px; color: #666;">Total Pagado</p>
                        <h2 style="margin: 0; color: green;">${total_pagado:,.2f}</h2>
                    </div>
                    <div data-testid="metric-container" style="flex: 1;">
                        <p style="font-size: 14px; color: #666;">Saldo Pendiente</p>
                        <h2 style="margin: 0; color: #D32F2F;">${deuda_pendiente:,.2f}</h2>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Smart Summary
                last_purchase_date = pd.to_datetime(client_data['Fecha_Venta']).max()
                days_since_last = (datetime.now() - last_purchase_date).days
                
                behavior = "Bueno"
                if deuda_pendiente > (total_facturado * 0.5):
                    behavior = "Regular (Deuda Alta)"
                if not pendientes.empty:
                    # Check if any overdue
                    now = datetime.now()
                    overdue = pendientes[pd.to_datetime(pendientes['Fecha_Vencimiento']) < now]
                    if not overdue.empty:
                        behavior = "Malo (Pagos Vencidos)"
                
                st.info(f"💡 **Resumen Inteligente**: El cliente **{selected_client}** tiene un comportamiento de pago **{behavior}**. Su última compra fue hace **{days_since_last}** días.")
                
                # Charts
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("Estado de Pagos")
                    # Pie Chart of Status
                    status_counts = client_data.groupby('Estado')['Monto_Total'].sum().reset_index()
                    fig_pie = px.pie(status_counts, values='Monto_Total', names='Estado', title="Distribución de Pagos", color='Estado',
                                     color_discrete_map={'Pagado':'green', 'Pendiente':'red', 'Vencido':'darkred'})
                    st.plotly_chart(fig_pie, use_container_width=True)
                    
                with c2:
                    st.subheader("Historial de Compras")
                    # Line chart over time
                    client_data['Fecha_Venta'] = pd.to_datetime(client_data['Fecha_Venta'])
                    sales_over_time = client_data.groupby('Fecha_Venta')['Monto_Total'].sum().reset_index().sort_values('Fecha_Venta')
                    fig_line = px.line(sales_over_time, x='Fecha_Venta', y='Monto_Total', title="Evolución de Compras", markers=True)
                    st.plotly_chart(fig_line, use_container_width=True)
    
                # Detailed Table
                st.subheader("Estado de Cuenta Detallado")
                
                # Custom coloring for Status column
                # Using Styler is best for static, but let's try to add a visual icon column
                def get_status_icon(row):
                    if row['Estado'] == 'Pagado':
                        return "🟢 Pagado"
                    elif row['Estado'] == 'Pendiente':
                         # Check overdue
                         if pd.to_datetime(row['Fecha_Vencimiento']) < datetime.now():
                             return "🔴 Vencido"
                         return "🟡 Pendiente"
                    return row['Estado']
        
                display_df = client_data.copy()
                display_df['Estado_Visual'] = display_df.apply(get_status_icon, axis=1)
                
                st.dataframe(
                    display_df[['Fecha_Venta', 'Monto_Total', 'Plazo_Cobro', 'Fecha_Vencimiento', 'Estado_Visual']], 
                    use_container_width=True,
                    hide_index=True
                )

    with tab2:
        st.subheader("Directorio de Clientes")
        if not clientes_df.empty:
            st.dataframe(clientes_df, use_container_width=True)
        else:
            st.info("No hay clientes registrados en la hoja 'Clientes'.")
            st.markdown("""
            **Estructura esperada en Google Sheets (Hoja: `Clientes`):**
            - `Nombre` (Debe coincidir con el usado en Ventas)
            - `CUIT`
            - `Telefono`
            - `Email`
            - `Direccion`
            - `Localidad`
            - `Notas`
            """)

    return True
