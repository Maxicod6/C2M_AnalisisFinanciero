import streamlit as st
import plotly.express as px
import pandas as pd

def show_dashboard(dm):
    st.header("Dashboard Financiero")

    # Load Data
    with st.spinner("Cargando datos..."):
        gastos_df = dm.get_gastos()
        cobros_df = dm.get_cobros()
        productos_df = dm.get_productos()

    # KPIs Calculation
    ingresos = 0
    if not cobros_df.empty:
        # Assuming only Paid entries count as actual Cash In, or maybe user wants "Cash Flow" (typically actual movement)
        # Prompt says "Cash Flow actual (Ingresos - Gastos)".
        # Usually Ingresos = Cobros Realizados.
        # But for 'Total por Cobrar' we use Pendiente.
        # Let's sum 'Monto_Total' where 'Estado' == 'Pagado'? Or just all sales?
        # A simpler "Cash Flow" often implies liquidity. Let's use "Pagado" for real cash flow.
        pagados = cobros_df[cobros_df['Estado'] == 'Pagado']
        ingresos = pagados['Monto_Total'].astype(float).sum()

    egresos = 0
    if not gastos_df.empty:
        egresos = gastos_df['Monto'].astype(float).sum()

    cash_flow = ingresos - egresos

    por_cobrar = 0
    if not cobros_df.empty:
        pendientes = cobros_df[cobros_df['Estado'] == 'Pendiente']
        por_cobrar = pendientes['Monto_Total'].astype(float).sum()

    valor_inventario = 0
    if not productos_df.empty:
        # Costo_Unitario * Stock_Actual
        valor_inventario = (productos_df['Costo_Unitario'].astype(float) * productos_df['Stock_Actual'].astype(float)).sum()

    # Display KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cash Flow (Ingresos - Gastos)", f"${cash_flow:,.2f}")
    col2.metric("Total por Cobrar", f"${por_cobrar:,.2f}")
    col3.metric("Valor Inventario", f"${valor_inventario:,.2f}")
    col4.metric("Total Gastos", f"${egresos:,.2f}")

    st.divider()

    # Charts
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Gastos por Categoría")
        if not gastos_df.empty:
            fig_gastos = px.bar(gastos_df, x="Categoria", y="Monto", title="Gastos por Categoría", color="Categoria")
            st.plotly_chart(fig_gastos, use_container_width=True)
        else:
            st.info("No hay datos de gastos.")

    with c2:
        st.subheader("Alertas de Stock")
        if not productos_df.empty:
            # Low Stock
            low_stock = productos_df[productos_df['Stock_Actual'].astype(float) < productos_df['Stock_Minimo'].astype(float)]
            if not low_stock.empty:
                st.error(f"⚠️ {len(low_stock)} Productos con Stock Bajo!")
                # Show Codigo_Big and Codigo_Estanteria
                display_cols = ['Codigo_Big', 'Codigo_Estanteria', 'Nombre', 'Stock_Actual', 'Stock_Minimo']
                # Ensure cols exist
                available_cols = [c for c in display_cols if c in low_stock.columns]
                st.dataframe(low_stock[available_cols], hide_index=True)
            else:
                st.success("Inventario Saludable (Todo sobre mínimo).")
        else:
            st.info("No hay productos registrados.")

