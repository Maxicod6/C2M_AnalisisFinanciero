import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

class DataManager:
    def __init__(self):
        # Initialize GSpread Connection locally since st.connection is failing
        try:
            # Load credentials
            secrets = st.secrets["connections"]["gsheets"]["credentials"]
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = Credentials.from_service_account_info(secrets, scopes=scopes)
            self.client = gspread.authorize(creds)
            
            # Open Spreadsheet
            url = st.secrets["connections"]["gsheets"]["spreadsheet"]
            # Clean URL
            clean_url = url.split("?")[0]
            self.sh = self.client.open_by_url(clean_url)
            
        except Exception as e:
            st.error(f"Error conectando con Google Sheets: {e}")
            raise e

        # Schema Definitions
        self.SCHEMAS = {
            "Clientes": ["Nombre", "CUIT", "Telefono", "Email", "Direccion", "Localidad", "Notas"],
            "Gastos": ["Fecha", "Categoria", "Tipo_Frecuencia", "Proveedor", "Detalle", "Monto", "Periodo_Facturacion", "Metodo_Pago", "Responsable_Pago", "Estado"],
            "Productos": ["Codigo_Big", "Nombre", "Descripcion", "Costo_Unitario", "Precio_Venta", "Stock_Actual", "Stock_Minimo"],
            "Movimientos": ["Fecha", "Tipo", "Codigo_Big", "Cantidad", "Documento_Ref"],
            "Cobros": ["Fecha_Venta", "Cliente", "Monto_Total", "Plazo_Cobro", "Fecha_Vencimiento", "Estado", "Fecha_Cobro_Real", "Vendedor", "Forma_Pago"]
        }

    @st.cache_data(ttl=60)
    def _fetch_data(_self, sheet_name):
        """
        Wrapper to fetch data with caching.
        Note: _self is used to prevent hashing the entire class instance.
        """
        try:
            ws = _self.sh.worksheet(sheet_name)
            return ws.get_all_records()
        except Exception as e:
            # Simple retry logic manually or let st error handle it. 
            # For 429, wait and retry could be added here.
            import time
            time.sleep(2) # Basic wait
            try:
                ws = _self.sh.worksheet(sheet_name)
                return ws.get_all_records() 
            except Exception as e2:
                # If still failing, return None to handle in _read_sheet
                print(f"Error fetching data: {e2}")
                return None

    def _read_sheet(self, sheet_name):
        try:
            # Use cached fetch
            data = self._fetch_data(sheet_name)
            
            if data is None: # Handle failure
                 return pd.DataFrame(columns=self.SCHEMAS[sheet_name])
                 
            if not data:
                return pd.DataFrame(columns=self.SCHEMAS[sheet_name])
                
            df = pd.DataFrame(data)
            
            # Enforce numeric types
            numeric_cols = ['Monto', 'Monto_Total', 'Costo_Unitario', 'Precio_Venta', 'Stock_Actual', 'Stock_Minimo', 'Cantidad']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # Ensure all expected columns exist
            expected_cols = self.SCHEMAS.get(sheet_name)
            if expected_cols:
                 # Add missing cols
                for col in expected_cols:
                    if col not in df.columns:
                        df[col] = ""
                # Reorder and filter extras
                df = df[expected_cols]
                
            return df
        except Exception as e:
            st.error(f"Error leyendo hoja '{sheet_name}': {e}")
            return pd.DataFrame(columns=self.SCHEMAS[sheet_name])

    def _update_sheet(self, sheet_name, df):
        """
        Replaces the entire content of the sheet with the dataframe.
        """
        try:
            ws = self.sh.worksheet(sheet_name)
            ws.clear()
            # Prepare data: Header + Rows
            # Convert to list of lists, handle NaNs
            df_filled = df.fillna("")
            data = [df_filled.columns.tolist()] + df_filled.astype(str).values.tolist()
            ws.update(data)
        except Exception as e:
            st.error(f"Error guardando datos en '{sheet_name}': {e}")

    def get_clientes(self):
        return self._read_sheet("Clientes")

    def get_gastos(self):
        df = self._read_sheet("Gastos")
        if 'Fecha' in df.columns:
             df['Fecha_DT'] = pd.to_datetime(df['Fecha'], errors='coerce')
        return df

    def get_productos(self):
        df = self._read_sheet("Productos")
        # Derived column: Codigo Estanteria (Logic: Remove first 2 characters)
        if 'Codigo_Big' in df.columns:
            df['Codigo_Estanteria'] = df['Codigo_Big'].astype(str).apply(lambda x: x[2:] if len(x) > 2 else x)
        return df

    def get_cobros(self):
        df = self._read_sheet("Cobros")
        if 'Fecha_Vencimiento' in df.columns:
            df['Fecha_Vencimiento_DT'] = pd.to_datetime(df['Fecha_Vencimiento'], errors='coerce')
        return df

    def add_row(self, sheet_name, row_data):
        """
        Appends a row to the sheet.
        row_data: dict corresponding to columns
        """
        try:
            ws = self.sh.worksheet(sheet_name)
            # Ensure row matches schema order
            schema = self.SCHEMAS[sheet_name]
            row_values = [row_data.get(col, "") for col in schema]
            ws.append_row(row_values)
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Error agregando fila a '{sheet_name}': {e}")

    def update_stock_and_log_movement(self, codigo_big, quantity, movement_type, doc_ref):
        """
        Updates stock in 'Productos' and logs entry in 'Movimientos'
        quantity: positive value. Logic handles sign based on movement_type if needed, 
        but usually we pass the net change or handle logic here.
        Actually, for 'Venta' we expect quantity to be positive and we subtract.
        For 'Compra' positive and we add.
        """
        df_prod = self.get_productos()
        
        # Find product
        mask = df_prod['Codigo_Big'].astype(str) == str(codigo_big)
        if not mask.any():
            st.error(f"Producto {codigo_big} no encontrado.")
            return

        current_stock = float(df_prod.loc[mask, 'Stock_Actual'].values[0])
        
        if movement_type == "Compra":
            new_stock = current_stock + float(quantity)
        elif movement_type == "Venta":
            new_stock = current_stock - float(quantity)
        else:
            new_stock = current_stock # Should logic for adjustment
            
        # Update DF
        df_prod.loc[mask, 'Stock_Actual'] = new_stock
        
        # Save Product Update
        # Drop derived column before saving
        data_to_save = df_prod.drop(columns=['Codigo_Estanteria'], errors='ignore')
        self._update_sheet("Productos", data_to_save)

        # 2. Log Movement
        movement_row = {
            "Fecha": datetime.now().strftime("%Y-%m-%d"),
            "Tipo": movement_type,
            "Codigo_Big": codigo_big,
            "Cantidad": quantity,
            "Documento_Ref": doc_ref
        }
        self.add_row("Movimientos", movement_row)

    def register_sale(self, sale_rows):
        """
        sale_rows: list of dicts with {Cliente, Codigo_Big, Cantidad, Precio_Total, Plazo_Dias}
        """
        cobros_rows = []
        
        # Optimize Stock Updates: Read once, Update local, Write once
        df_prod = self.get_productos()
        # Ensure correct type for matching
        df_prod['Codigo_Big'] = df_prod['Codigo_Big'].astype(str).str.strip()
        
        # Track if we need to save products
        products_updated = False
        
        # Data for single Cobro aggregation
        total_sale_amount = 0
        first_item = sale_rows[0] if sale_rows else None
        
        # For movement logging, we might still need append_row which is slow if loop.
        movimientos_rows = []
        
        for item in sale_rows:
            codigo = str(item['Codigo_Big']).strip()
            qty = float(item['Cantidad'])
            price_line = float(item['Precio_Total'])
            
            # Aggregate Total
            total_sale_amount += price_line
            
            # 1. Update Stock Logic
            mask = df_prod['Codigo_Big'] == codigo
            if mask.any():
                current_stock = float(df_prod.loc[mask, 'Stock_Actual'].values[0])
                df_prod.loc[mask, 'Stock_Actual'] = current_stock - qty
                products_updated = True
                
                # Log Movement locally
                movimientos_rows.append({
                    "Fecha": datetime.now().strftime("%Y-%m-%d"),
                    "Tipo": "Venta",
                    "Codigo_Big": codigo,
                    "Cantidad": qty,
                    "Documento_Ref": f"Venta a {item['Cliente']}"
                })
            else:
                st.warning(f"Producto {codigo} no encontrado para descontar stock.")
            
        # 2. Prepare SINGLE Cobro Entry (Aggregated)
        if first_item:
            fecha_venta = datetime.now()
            try:
                days = int(first_item.get('Plazo_Dias', 30))
            except:
                days = 30
            vencimiento = fecha_venta + pd.Timedelta(days=days)
            
            cobros_rows.append({
                "Fecha_Venta": fecha_venta.strftime("%Y-%m-%d"),
                "Cliente": first_item['Cliente'],
                "Monto_Total": total_sale_amount,
                "Plazo_Cobro": days,
                "Fecha_Vencimiento": vencimiento.strftime("%Y-%m-%d"),
                "Estado": "Pendiente",
                "Fecha_Cobro_Real": "",
                "Vendedor": first_item.get('Vendedor', ''),
                "Forma_Pago": ""
            })
            
        # 3. Batch Write Ops
        try:
            # Save Products (One write)
            if products_updated:
                 # Drop derived before save
                data_to_save = df_prod.drop(columns=['Codigo_Estanteria'], errors='ignore')
                self._update_sheet("Productos", data_to_save)
            
            # Add Movimientos (One Batch Write)
            if movimientos_rows:
                ws_mov = self.sh.worksheet("Movimientos")
                schema_mov = self.SCHEMAS["Movimientos"]
                mov_values = [[row.get(col, "") for col in schema_mov] for row in movimientos_rows]
                ws_mov.append_rows(mov_values)
                
            # Add Cobros (One Batch Write - Single Row)
            if cobros_rows:
                ws_cob = self.sh.worksheet("Cobros")
                schema_cob = self.SCHEMAS["Cobros"]
                rows_values = [[row.get(col, "") for col in schema_cob] for row in cobros_rows]
                ws_cob.append_rows(rows_values)
                
            # Clear Cache
            st.cache_data.clear()
            
        except Exception as e:
            st.error(f"Error registrando ventas masivas: {e}")

    def update_cobros(self, updated_df):
        self._update_sheet("Cobros", updated_df)

    def update_gastos_sheet(self, updated_df):
        self._update_sheet("Gastos", updated_df)
