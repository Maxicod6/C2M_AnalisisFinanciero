import streamlit as st
import pandas as pd
import plotly.express as px
import time
from datetime import datetime, timedelta

def show_sales(dm):
    st.header("Ventas y Cobros")

    tab1, tab2, tab3 = st.tabs(["📋 Ordenes de Compra (Cobranzas)", "🛒 Nueva Venta", "📤 Carga Masiva"])

    # ----------------------------------------------------------------------
    # TAB 1: PANEL DE COBROS (Collections Cards)
    # ----------------------------------------------------------------------
    with tab1:
        st.subheader("Gestionar Cobranzas Pendientes")
        
        df_cobros = dm.get_cobros()
        
        if not df_cobros.empty:
            # Filter for Pending only for the main card view
            pending_cobros = df_cobros[df_cobros['Estado'] == 'Pendiente'].copy()
            
            if pending_cobros.empty:
                st.success("¡No hay cobros pendientes! 🎉")
            else:
                pending_cobros['Fecha_Vencimiento_DT'] = pd.to_datetime(pending_cobros['Fecha_Vencimiento'], errors='coerce')
                now = datetime.now()
                
                # Sort by Due Date
                pending_cobros = pending_cobros.sort_values('Fecha_Vencimiento_DT')
                
                # Display using columns (grid layout)
                cols_per_row = 3
                cols = st.columns(cols_per_row)
                
                for idx, row in pending_cobros.iterrows():
                    col_idx = idx % cols_per_row # This index might not be sequential if filtered, better verify row iteration
                    # Let's use enumerate for clean column assignment
                    pass 
                
                # Better iteration for grid
                for i, (index, row) in enumerate(pending_cobros.iterrows()):
                    col = cols[i % cols_per_row]
                    
                    with col:
                        # Determine Color
                        days_left = (row['Fecha_Vencimiento_DT'] - now).days
                        
                        card_color = "#4CAF50" # Green (Safe)
                        status_text = f"Vence en {days_left} días"
                        
                        if days_left < 0:
                            card_color = "#E53935" # Red (Overdue)
                            status_text = f"VENCIDO hace {abs(days_left)} días"
                        elif days_left <= 7:
                            card_color = "#FBC02D" # Yellow (Warning)
                            status_text = f"Vence pronto ({days_left} días)"
                            
                        # Card HTML
                        st.markdown(f"""
                        <div style="border: 1px solid #2A3245; border-radius: 12px; padding: 15px; margin-bottom: 15px; border-left: 5px solid {card_color}; background-color: #151A28; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                            <h4 style="margin: 0; color: #FFFFFF;">{row['Cliente']}</h4>
                            <p style="margin: 0; font-size: 14px; color: #E2E8F0;">Monto: <b style="color: #FFFFFF;">${row['Monto_Total']:,.2f}</b></p>
                            <p style="margin: 5px 0 0 0; font-size: 12px; color: {card_color}; font-weight: bold;">{status_text}</p>
                            <p style="margin: 0; font-size: 12px; color: #94A3B8;">Venc: {row['Fecha_Vencimiento']}</p>
                            <p style="margin: 0; font-size: 12px; color: #94A3B8;">Vendedor: {row.get('Vendedor', '-')}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Payment Button / Expandable Form
                        with st.popover(f"Registrar Pago #{i}"):
                            st.write(f"Pago de **{row['Cliente']}**")
                            st.write(f"Monto Total: ${row['Monto_Total']:,.2f}")
                            
                            with st.form(f"pay_form_{index}"):
                                fecha_pago = st.date_input("Fecha de Pago", datetime.now())
                                forma_pago = st.selectbox("Forma de Pago", ["Transferencia", "Efectivo", "Cheque", "Otro"])
                                
                                if forma_pago == "Cheque":
                                    st.warning("⚠️ Recueda depositar el cheque antes de su vencimiento.")
                                
                                # Partial payments? For now full payment assumed as per "Registrar Pago" simple logic
                                # Or update status to Pagado.
                                
                                submit_pago = st.form_submit_button("Confirmar Pago")
                                
                                if submit_pago:
                                    # Update Logic
                                    # We need to find this row in the original DF and update it
                                    # Since we don't have unique IDs, we rely on matching fields logic (risky) or index if reliable.
                                    # DataManager.update_cobros expects the full DF.
                                    
                                    # Let's modify the full df_cobros
                                    # Assuming 'index' from iterrows matches original if not reset? 
                                    # It does match the index in pending_cobros, but pending_cobros is a copy? No, filtered from df_cobros.
                                    
                                    # Best approach with current DataManager structure (Replacing full sheet):
                                    # Find index in main df_cobros
                                    main_idx = index
                                    
                                    df_cobros.at[main_idx, 'Estado'] = "Pagado"
                                    df_cobros.at[main_idx, 'Fecha_Cobro_Real'] = fecha_pago.strftime("%Y-%m-%d")
                                    df_cobros.at[main_idx, 'Forma_Pago'] = forma_pago
                                    
                                    # Drop helper cols before saving
                                    save_df = df_cobros.drop(columns=['Fecha_Vencimiento_DT', 'Fecha_Mes'], errors='ignore')
                                    
                                    dm.update_cobros(save_df)
                                    st.success("Pago registrado!")
                                    st.rerun()

            st.divider()
            
            # History Table (Editable)
            with st.expander("Ver Historial de Cobros (Modificar / Eliminar)", expanded=False):
                st.warning("⚠️ Nota: Modificar montos o eliminar filas aquí NO ajusta el stock de productos automáticamente.")
                
                # Prepare DF for editor (Convert dates to datetime)
                df_editor = df_cobros.copy()
                df_editor['Fecha_Venta'] = pd.to_datetime(df_editor['Fecha_Venta'], errors='coerce')
                df_editor['Fecha_Vencimiento'] = pd.to_datetime(df_editor['Fecha_Vencimiento'], errors='coerce')

                # Full Editor
                history_editor = st.data_editor(
                    df_editor.drop(columns=['Fecha_Vencimiento_DT'], errors='ignore'),
                    use_container_width=True,
                    num_rows="dynamic", # Allows add/delete
                    key="history_editor",
                    column_config={
                        "Fecha_Venta": st.column_config.DateColumn("Fecha Venta", format="YYYY-MM-DD"),
                        "Fecha_Vencimiento": st.column_config.DateColumn("Vencimiento", format="YYYY-MM-DD"),
                        "Monto_Total": st.column_config.NumberColumn("Monto", format="$%.2f"),
                        "Estado": st.column_config.SelectboxColumn("Estado", options=["Pendiente", "Pagado", "Vencido"])
                    }
                )
                
                if st.button("💾 Guardar Cambios en Historial"):
                    try:
                        # Convert back to string for GSheets storage
                        history_editor['Fecha_Venta'] = pd.to_datetime(history_editor['Fecha_Venta']).dt.strftime('%Y-%m-%d')
                        history_editor['Fecha_Vencimiento'] = pd.to_datetime(history_editor['Fecha_Vencimiento']).dt.strftime('%Y-%m-%d')
                        
                        dm.update_cobros(history_editor)
                        st.success("Historial actualizado correctamente.")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al actualizar: {e}")

    # ----------------------------------------------------------------------
    # TAB 2: CARGAR VENTA INDIVIDUAL
    # ----------------------------------------------------------------------
    with tab2:
        st.subheader("🛒 Nueva Venta Individual")
        
        clients_df = dm.get_clientes()
        products_df = dm.get_productos()
        
        if clients_df.empty or products_df.empty:
            st.warning("Faltan datos de Clientes o Productos.")
        else:
            with st.form("single_sale_form_v2"):
                c_client, c_vend = st.columns(2)
                cliente_sel = c_client.selectbox("Cliente", sorted(clients_df['Nombre'].dropna().unique()))
                vendedor = c_vend.text_input("Vendedor")
                
                c_prod, c_qty = st.columns([2,1])
                
                # Product Helper
                products_df['Codigo_Estanteria'] = products_df['Codigo_Big'].apply(lambda x: str(x)[2:] if len(str(x)) > 2 else x)
                products_df['Display_Name'] = products_df.apply(lambda x: f"[{x['Codigo_Estanteria']}] {x['Nombre']}", axis=1)
                prod_map = products_df.set_index('Display_Name').to_dict('index')
                
                product_sel = c_prod.selectbox("Producto", options=sorted(products_df['Display_Name'].unique()))
                cantidad = c_qty.number_input("Cantidad", min_value=1, step=1)
                
                # Data
                selected_prod_data = prod_map[product_sel]
                base_price = float(selected_prod_data.get('Precio_Venta', 0))
                
                c_plazo, c_empty = st.columns(2)
                plazo = c_plazo.number_input("Plazo (Días)", value=30, step=15)
                
                # Discounts
                st.markdown("**Descuentos**")
                cd1, cd2, cd3 = st.columns(3)
                d1 = cd1.checkbox("Inicial (30%)", value=True)
                d2 = cd2.checkbox("Distribuidor (30%)")
                d3 = cd3.checkbox("Pronto Pago (4%)")
                
                # Calculation
                price_1 = base_price * (0.70 if d1 else 1.0)
                price_2 = price_1 * (0.70 if d2 else 1.0)
                final_unit_price = price_2 * (0.96 if d3 else 1.0)
                total_sale = final_unit_price * cantidad
                
                st.markdown(f"**Total a Pagar: :green[${total_sale:,.2f}]**")

                if st.form_submit_button("Registrar Venta"):
                    sale_record = {
                        "Cliente": cliente_sel,
                        "Vendedor": vendedor,
                        "Codigo_Big": selected_prod_data['Codigo_Big'],
                        "Cantidad": cantidad,
                        "Precio_Total": total_sale,
                        "Plazo_Dias": plazo
                    }
                    try:
                        dm.register_sale([sale_record])
                        st.success("Venta registrada!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

    # ----------------------------------------------------------------------
    # TAB 3: CARGAR VENTAS MASIVAS (Improved)
    # ----------------------------------------------------------------------
    with tab3:
        st.subheader("📤 Carga Masiva Simplificada")
        st.info("Sube un CSV con: `Codigo_Big`, `Cantidad`, `Descuento` (%), `Plazo`.")
        
        c_global1, c_global2 = st.columns(2)
        clients_df = dm.get_clientes()
        if not clients_df.empty:
            global_cliente = c_global1.selectbox("Cliente (para todo el archivo)", sorted(clients_df['Nombre'].unique()))
        else:
            global_cliente = c_global1.text_input("Cliente")
            
        global_vendedor = c_global2.text_input("Vendedor (para todo el archivo)")
        
        uploaded_file = st.file_uploader("Subir CSV", type=["csv", "xlsx"])
        
        if uploaded_file and global_cliente:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_upload = pd.read_csv(uploaded_file)
                else:
                    df_upload = pd.read_excel(uploaded_file)
                
                # Normalize cols
                df_upload.columns = [c.strip() for c in df_upload.columns]
                
                required = {'Codigo_Big', 'Cantidad', 'Descuento', 'Plazo'} 
                # User said: Codigo_Big, Cantidad, Descuento, Plazo
                
                if not required.issubset(df_upload.columns):
                    st.error(f"Faltan columnas. Requeridas: {required}")
                else:
                    st.write("Vista previa (Precios se calcularán al procesar):")
                    st.dataframe(df_upload)
                    
                    if st.button("Procesar Ventas Masivas"):
                        products_df = dm.get_productos()
                        # Map Codigo_Big to Price
                        # Ensure string matching and strip whitespace
                        products_df['Codigo_Big'] = products_df['Codigo_Big'].astype(str).str.strip()
                        price_map = products_df.set_index('Codigo_Big')['Precio_Venta'].to_dict()
                        
                        sales_to_register = []
                        errors = []
                        
                        for idx, row in df_upload.iterrows():
                            code = str(row['Codigo_Big']).strip()
                            if code in price_map:
                                base_price = float(price_map[code])
                                qty = float(row['Cantidad'])
                                
                                # Handle Discount format (remove % if present)
                                raw_desc = str(row.get('Descuento', 0)).replace('%', '').strip()
                                # Handle comma vs dot decimal just in case
                                raw_desc = raw_desc.replace(',', '.')
                                try:
                                    discount_pct = float(raw_desc)
                                except ValueError:
                                    discount_pct = 0.0
                                
                                # Calc Net
                                final_price = base_price * (1 - discount_pct/100)
                                total_line = final_price * qty
                                
                                sales_to_register.append({
                                    "Cliente": global_cliente,
                                    "Vendedor": global_vendedor,
                                    "Codigo_Big": code,
                                    "Cantidad": qty,
                                    "Precio_Total": total_line,
                                    "Plazo_Dias": row.get('Plazo', 30)
                                })
                            else:
                                errors.append(f"Fila {idx}: Producto {code} no encontrado.")
                        
                        if errors:
                            st.warning("Se encontraron errores:")
                            for e in errors:
                                st.write(e)
                            if st.button("Continuar ignorando errores"):
                                pass # Logic to continue? Better safe stop.
                                st.stop()
                        
                        if sales_to_register:
                            dm.register_sale(sales_to_register)
                            st.success(f"✅ Se procesaron {len(sales_to_register)} ventas correctamente.")
                            st.balloons()
                            st.rerun()

            except Exception as e:
                st.error(f"Error procesando archivo: {e}")

