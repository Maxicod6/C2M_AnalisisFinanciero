import streamlit as st
import pandas as pd
from io import StringIO

def show_inventory(dm):
    st.header("Inventario y Compras")

    tab1, tab2 = st.tabs(["Stock Actual", "Cargar Compra (CSV)"])

    with tab1:
        st.subheader("Listado de Productos")
        df_prod = dm.get_productos()
        if not df_prod.empty:
            # Reorder columns
            cols = ['Codigo_Big', 'Codigo_Estanteria', 'Nombre', 'Descripcion', 'Stock_Actual', 'Stock_Minimo', 'Costo_Unitario', 'Precio_Venta']
            available_cols = [c for c in cols if c in df_prod.columns]
            st.dataframe(df_prod[available_cols], use_container_width=True)
            
            st.divider()
            
            # Chart Top 20 Stock
            import plotly.express as px
            st.subheader("Niveles de Stock (Top 20 Productos)")
            # Sort by Stock Value or Quantity
            df_prod['Valor_Stock'] = pd.to_numeric(df_prod['Stock_Actual'], errors='coerce') * pd.to_numeric(df_prod['Costo_Unitario'], errors='coerce')
            top_stock = df_prod.sort_values(by='Valor_Stock', ascending=False).head(20)
            
            fig_bar = px.bar(top_stock, x='Nombre', y='Stock_Actual', title="Stock Actual por Producto", 
                             color='Valor_Stock', hover_data=['Codigo_Big'])
            st.plotly_chart(fig_bar, use_container_width=True)

            # LOW STOCK ALERT TABLE
            st.divider()
            st.subheader("⚠️ Productos a Pedir (Bajo Stock)")
            low_stock_df = df_prod[df_prod['Stock_Actual'] <= df_prod['Stock_Minimo']].copy()
            
            if not low_stock_df.empty:
                st.warning(f"Hay {len(low_stock_df)} productos por debajo del stock mínimo.")
                st.dataframe(low_stock_df[['Codigo_Big', 'Nombre', 'Stock_Actual', 'Stock_Minimo']], use_container_width=True)
            else:
                st.success("✅ Todo el stock está por encima del mínimo.")
                
        else:
            st.info("No hay productos en la base de datos.")

    with tab2:
        st.subheader("Carga Masiva de Compras")
        st.markdown("Sube un archivo CSV con las columnas: `Codigo_Big`, `Cantidad_Comprada`.")
        
        uploaded_file = st.file_uploader("Subir Planilla de Compras", type=["csv", "xlsx"])
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_upload = pd.read_csv(uploaded_file)
                else:
                    df_upload = pd.read_excel(uploaded_file)
                
                # Check columns
                required_cols = {'Codigo_Big', 'Cantidad_Comprada'}
                if not required_cols.issubset(df_upload.columns):
                    st.error(f"El archivo debe tener las columnas: {required_cols}")
                else:
                    st.write("Vista previa:", df_upload.head())
                    if st.button("Procesar Carga"):
                        progress_bar = st.progress(0)
                        
                        try:
                            # Verify Codigo_Bigs first
                            current_codes = dm.get_productos()['Codigo_Big'].astype(str).values
                            errors = []
                            for idx, row in df_upload.iterrows():
                                if str(row['Codigo_Big']) not in current_codes:
                                    errors.append(f"Fila {idx+1}: Codigo Big {row['Codigo_Big']} no existe.")
                            
                            if errors:
                                st.error("Errores encontrados:")
                                for e in errors:
                                    st.write(e)
                                st.stop()
                            
                            # Process
                            for idx, row in df_upload.iterrows():
                                dm.update_stock_and_log_movement(
                                    codigo_big=row['Codigo_Big'],
                                    quantity=row['Cantidad_Comprada'],
                                    movement_type="Compra",
                                    doc_ref=f"Carga Masiva {uploaded_file.name}"
                                )
                                progress_bar.progress((idx + 1) / len(df_upload))
                                
                            st.success("Carga procesada correctamente. Stock actualizado.")
                            st.rerun()

                        except Exception as e:
                            st.error(f"Error procesando el archivo: {e}")
                            
            except Exception as e:
                st.error(f"Error leyendo el archivo: {e}")
