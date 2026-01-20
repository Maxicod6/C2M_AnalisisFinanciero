import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

def show_gastos(dm):
    st.header("Gestión de Gastos")
    
    # ----------------------------------------------------
    # 1. NEW EXPENSE FORM
    # ----------------------------------------------------
    with st.expander("➕ Cargar Nuevo Gasto", expanded=False):
        with st.form("new_expense_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                fecha = st.date_input("Fecha de Gasto", format="YYYY-MM-DD")
                categoria = st.selectbox("Categoría", ["Marketing/ventas", "Administracion/operativo", "Otros"])
                frecuencia = st.selectbox("Tipo de Frecuencia", ["No Recurrente", "Recurrente", "Extraordinario"])
            
            with c2:
                proveedor = st.text_input("Proveedor")
                monto = st.number_input("Monto ($)", min_value=0.0, step=100.0)
                metodo = st.selectbox("Método de Pago", ["Transferencia", "Efectivo", "Tarjeta Crédito", "Tarjeta Débito", "Cheque"])

            with c3:
                detalle = st.text_input("Detalle / Descripción")
                responsable = st.text_input("Responsable de Pago")
                estado = st.selectbox("Estado", ["Pagado", "Pendiente"])
            
            # Recurrence Logic
            months_recurrence = 0
            if frecuencia == "Recurrente":
                st.info("🔄 Gasto Recurrente: Se replicará este gasto mensualmente.")
                months_recurrence = st.number_input("Cantidad de meses a repetir (además del actual)", min_value=0, max_value=24, value=0)

            submitted = st.form_submit_button("Guardar Gasto")
            
            if submitted:
                if not proveedor or monto <= 0:
                    st.error("Por favor ingresa Proveedor y Monto válido.")
                else:
                    # Base Expense
                    gastos_to_add = []
                    
                    # 1. Current Expense
                    base_row = {
                        "Fecha": fecha.strftime("%Y-%m-%d"),
                        "Categoria": categoria,
                        "Tipo_Frecuencia": frecuencia,
                        "Proveedor": proveedor,
                        "Detalle": detalle,
                        "Monto": monto,
                        "Periodo_Facturacion": fecha.strftime("%Y-%m"),
                        "Metodo_Pago": metodo,
                        "Responsable_Pago": responsable,
                        "Estado": estado
                    }
                    gastos_to_add.append(base_row)
                    
                    # 2. Recurrent Expenses
                    if frecuencia == "Recurrente" and months_recurrence > 0:
                        start_date = fecha
                        for i in range(1, int(months_recurrence) + 1):
                            # Add i months
                            # Logic to add month safely
                            next_month_year = start_date.year + (start_date.month + i - 1) // 12
                            next_month = (start_date.month + i - 1) % 12 + 1
                            try:
                                next_date = start_date.replace(year=next_month_year, month=next_month)
                            except ValueError:
                                # Handle cases like Feb 30 -> Feb 28
                                import calendar
                                last_day = calendar.monthrange(next_month_year, next_month)[1]
                                next_date = start_date.replace(year=next_month_year, month=next_month, day=last_day)
                            
                            new_row = base_row.copy()
                            new_row['Fecha'] = next_date.strftime("%Y-%m-%d")
                            new_row['Periodo_Facturacion'] = next_date.strftime("%Y-%m")
                            new_row['Detalle'] = f"{detalle} (Recurrente {i}/{months_recurrence})"
                            new_row['Estado'] = "Pendiente" # Future defaults to pending
                            gastos_to_add.append(new_row)
                    
                    # Save all
                    for row in gastos_to_add:
                        dm.add_row("Gastos", row)
                    
                    st.success(f"✅ Gasto guardado correctamente ({len(gastos_to_add)} registros generados).")
                    st.rerun()

    # ----------------------------------------------------
    # 2. ANALYSIS & VISUALIZATION
    # ----------------------------------------------------
    df = dm.get_gastos()
    
    if df.empty:
        st.info("No hay gastos registrados.")
        return

    st.divider()
    
    # -----------------------
    # FILTERS
    # -----------------------
    df['Fecha_DT'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df['Año'] = df['Fecha_DT'].dt.year
    df['Mes'] = df['Fecha_DT'].dt.month
    
    c_filt1, c_filt2, c_filt3 = st.columns(3)
    
    available_years = sorted(df['Año'].dropna().unique(), reverse=True)
    if not available_years:
        available_years = [datetime.now().year]
        
    selected_year = c_filt1.selectbox("Filtrar por Año", available_years)
    
    available_months = range(1, 13)
    current_month = datetime.now().month
    selected_month = c_filt2.selectbox("Filtrar por Mes (para tarjeta mensual)", available_months, index=current_month-1)
    
    # Check if 'Tipo_Frecuencia' exists (backward compatibility)
    if 'Tipo_Frecuencia' not in df.columns:
        df['Tipo_Frecuencia'] = "No Recurrente" # Default fallback
        
    frecuencia_options = df['Tipo_Frecuencia'].unique()
    frecuencia_filter = c_filt3.multiselect("Filtrar por Tipo", frecuencia_options, default=frecuencia_options)

    # Filter Data
    df_year = df[df['Año'] == selected_year]
    df_monthly = df_year[df_year['Mes'] == selected_month]
    df_filtered_type = df_year[df_year['Tipo_Frecuencia'].isin(frecuencia_filter)] if frecuencia_filter else df_year

    # -----------------------
    # CARDS (KPIs)
    # -----------------------
    
    # (i) Gasto Mensual (Selected Month)
    monthly_total = df_monthly['Monto'].sum()
    
    # (ii) Gasto Ejercicio (Annual)
    annual_total = df_year['Monto'].sum()
    
    # (iii) Breakdown by Type (Annual)
    recurrente_total = df_year[df_year['Tipo_Frecuencia'] == 'Recurrente']['Monto'].sum()
    no_recurrente_total = df_year[df_year['Tipo_Frecuencia'] == 'No Recurrente']['Monto'].sum()
    extra_total = df_year[df_year['Tipo_Frecuencia'] == 'Extraordinario']['Monto'].sum()

    st.markdown(f"""
    <div style="display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 20px;">
        <div style="flex: 1; min-width: 200px; padding: 15px; background: #151A28; border-radius: 16px; border: 1px solid #2A3245; box-shadow: 0 4px 10px rgba(0,0,0,0.2); border-left: 5px solid #1E88E5;">
            <p style="font-size: 12px; color: #94A3B8; margin:0;">Gasto Mensual ({selected_month}/{selected_year})</p>
            <h2 style="margin: 0; color: #FFFFFF; font-size: 1.8rem;">${monthly_total:,.2f}</h2>
        </div>
        <div style="flex: 1; min-width: 200px; padding: 15px; background: #151A28; border-radius: 16px; border: 1px solid #2A3245; box-shadow: 0 4px 10px rgba(0,0,0,0.2); border-left: 5px solid #43A047;">
            <p style="font-size: 12px; color: #94A3B8; margin:0;">Gasto Anual ({selected_year})</p>
            <h2 style="margin: 0; color: #FFFFFF; font-size: 1.8rem;">${annual_total:,.2f}</h2>
        </div>
        <div style="flex: 1; min-width: 200px; padding: 15px; background: #151A28; border-radius: 16px; border: 1px solid #2A3245; box-shadow: 0 4px 10px rgba(0,0,0,0.2); border-left: 5px solid #FBC02D;">
            <p style="font-size: 12px; color: #94A3B8; margin:0;">Recurrentes (Año)</p>
            <h3 style="margin: 0; color: #FFFFFF; font-size: 1.5rem;">${recurrente_total:,.2f}</h3>
        </div>
      <div style="flex: 1; min-width: 200px; padding: 15px; background: #151A28; border-radius: 16px; border: 1px solid #2A3245; box-shadow: 0 4px 10px rgba(0,0,0,0.2); border-left: 5px solid #8E24AA;">
            <p style="font-size: 12px; color: #94A3B8; margin:0;">No Recurrentes</p>
            <h3 style="margin: 0; color: #FFFFFF; font-size: 1.5rem;">${no_recurrente_total:,.2f}</h3>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # -----------------------
    # CHARTS
    # -----------------------
    t1, t2 = st.tabs(["📈 Análisis Visual", "📋 Tabla de Datos"])
    
    with t1:
        col_charts_1, col_charts_2 = st.columns(2)
        
        with col_charts_1:
            st.subheader(f"Evolución Mensual ({selected_year})")
            # Group by Month for the selected year and types
            monthly_evolution = df_filtered_type.groupby("Periodo_Facturacion")['Monto'].sum().reset_index()
            fig_evol = px.bar(monthly_evolution, x='Periodo_Facturacion', y='Monto', title="Gasto por Mes", text_auto=True)
            st.plotly_chart(fig_evol, use_container_width=True)
            
        with col_charts_2:
            st.subheader("Distribución por Categoría")
            cat_dist = df_filtered_type.groupby("Categoria")['Monto'].sum().reset_index()
            fig_pie_cat = px.pie(cat_dist, values='Monto', names='Categoria', title="Porcentaje por Categoría", hole=0.4)
            st.plotly_chart(fig_pie_cat, use_container_width=True)
            
        st.subheader("Análisis por Tipo de Frecuencia")
        freq_dist = df_year.groupby("Tipo_Frecuencia")['Monto'].sum().reset_index()
        fig_pie_freq = px.pie(freq_dist, values='Monto', names='Tipo_Frecuencia', title=f"Mix de Gastos {selected_year}", 
                              color='Tipo_Frecuencia', color_discrete_map={
                                  'Recurrente': '#FBC02D', 'No Recurrente': '#8E24AA', 'Extraordinario': '#E53935'
                              })
        st.plotly_chart(fig_pie_freq, use_container_width=True)

    with t2:
        st.dataframe(df_filtered_type, use_container_width=True)
