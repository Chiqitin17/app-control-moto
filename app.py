import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Control Moto", page_icon="🛵", layout="centered")

# --- VARIABLES Y PORCENTAJES ---
SII_PCT = 0.1375
BENCINA_PCT = 0.15
MANT_PCT = 0.15
AHORRO_PCT = 0.10

# Usamos directamente el ID de tu Excel para evitar errores de links
SHEET_ID = "1-e_-2nAwtAXE4jsTFA0jSN_eaI3uvwvNx5dsep7JP64"

# --- CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource
def conectar_gsheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    skey = dict(st.secrets["gcp_service_account"])
    credentials = Credentials.from_service_account_info(skey, scopes=scopes)
    gc = gspread.authorize(credentials)
    return gc.open_by_key(SHEET_ID)
try:
    sh = conectar_gsheets()
    ws_turnos = sh.worksheet("Turnos")
    ws_gastos = sh.worksheet("Gastos")
except Exception as e:
    st.error(f"🚨 Error técnico detectado: {e}")
    st.info("Por favor, mándame una captura de este error exacto para saber qué falta.")
    st.stop()

# --- CARGAR DATOS ---
def cargar_datos():
    # Turnos
    try:
        df_t = pd.DataFrame(ws_turnos.get_all_records())
    except:
        ws_turnos.append_row(['Fecha', 'App', 'KM_Inicial', 'KM_Final', 'Base', 'Promo', 'Propina', 'SII', 'Fondo_Bencina', 'Fondo_Mant', 'Fondo_Ahorro', 'Para_Mi'])
        df_t = pd.DataFrame(ws_turnos.get_all_records())
    
    # Gastos
    try:
        df_g = pd.DataFrame(ws_gastos.get_all_records())
    except:
        ws_gastos.append_row(['Fecha', 'Tipo', 'Monto'])
        df_g = pd.DataFrame(ws_gastos.get_all_records())
        
    return df_t, df_g

turnos_df, gastos_df = cargar_datos()

# --- VARIABLES DE SESIÓN ---
if 'turno_activo' not in st.session_state:
    st.session_state.turno_activo = False
if 'km_inicio_temp' not in st.session_state:
    st.session_state.km_inicio_temp = 0

# --- LÓGICA DE CÁLCULO ---
def calcular_reparticion(base, promo, propina):
    imponible = base + promo
    sii = imponible * SII_PCT
    neto_app = imponible - sii
    
    bencina = max(0, neto_app * BENCINA_PCT)
    mantencion = max(0, neto_app * MANT_PCT)
    
    neto_total = neto_app + propina
    ahorro = neto_total * AHORRO_PCT
    para_mi = neto_total - bencina - mantencion - ahorro
    
    return round(sii), round(bencina), round(mantencion), round(ahorro), round(para_mi)

# --- INTERFAZ ---
tab1, tab2, tab3 = st.tabs(["📊 Panel Principal", "🛵 Mi Turno", "💸 Registrar Gasto"])

# PESTAÑA 1: PANEL
with tab1:
    st.title("Mi Panel Financiero")
    
    # Convertir a números por si acaso
    if not gastos_df.empty:
        gastos_df['Monto'] = pd.to_numeric(gastos_df['Monto'], errors='coerce').fillna(0)
    if not turnos_df.empty:
        for col in ['Fondo_Bencina', 'Fondo_Mant', 'Fondo_Ahorro', 'Para_Mi']:
            turnos_df[col] = pd.to_numeric(turnos_df[col], errors='coerce').fillna(0)

    gastos_bencina = gastos_df[gastos_df['Tipo'] == 'Bencina']['Monto'].sum() if not gastos_df.empty else 0
    gastos_mant = gastos_df[gastos_df['Tipo'] == 'Mantención']['Monto'].sum() if not gastos_df.empty else 0
    
    disp_bencina = turnos_df['Fondo_Bencina'].sum() - gastos_bencina if not turnos_df.empty else 0
    disp_mant = turnos_df['Fondo_Mant'].sum() - gastos_mant if not turnos_df.empty else 0
    total_ahorro = turnos_df['Fondo_Ahorro'].sum() if not turnos_df.empty else 0
    total_bolsillo = turnos_df['Para_Mi'].sum() if not turnos_df.empty else 0
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("🤑 Libre Para Mí", f"${int(total_bolsillo):,.0f}".replace(",", "."))
        st.metric("⛽ Fondo Bencina", f"${int(disp_bencina):,.0f}".replace(",", "."))
    with col2:
        st.metric("🏦 Mi Ahorro", f"${int(total_ahorro):,.0f}".replace(",", "."))
        st.metric("🔧 Fondo Mantención", f"${int(disp_mant):,.0f}".replace(",", "."))
    
    st.divider()
    st.write("Últimos turnos (nube):")
    if not turnos_df.empty:
        st.dataframe(turnos_df[['Fecha', 'App', 'Base', 'Propina', 'Para_Mi']].tail(3))
    else:
        st.write("Aún no hay turnos registrados.")

# PESTAÑA 2: TURNO
with tab2:
    st.header("Control de Turno Diario")
    
    if not st.session_state.turno_activo:
        km_in = st.number_input("Kilometraje al INICIAR el turno:", min_value=0, step=1)
        if st.button("🚀 Iniciar Turno", use_container_width=True):
            st.session_state.km_inicio_temp = km_in
            st.session_state.turno_activo = True
            st.rerun()
    else:
        st.success(f"Turno en curso. Iniciaste con: {st.session_state.km_inicio_temp} KM")
        with st.form("form_finalizar_turno"):
            app_usada = st.selectbox("Aplicación", ["PedidosYa", "Uber Eats"])
            km_out = st.number_input("Kilometraje al FINALIZAR:", min_value=st.session_state.km_inicio_temp, step=1)
            
            col1, col2, col3 = st.columns(3)
            with col1: base = st.number_input("Base ($)", min_value=0, step=100)
            with col2: promo = st.number_input("Promo ($)", min_value=0, step=100)
            with col3: propina = st.number_input("Propinas ($)", min_value=0, step=100)
            
            submit = st.form_submit_button("🏁 Guardar en Nube", use_container_width=True)
            
            if submit:
                sii, benc, mant, aho, p_mi = calcular_reparticion(base, promo, propina)
                fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                
                # Escribir en Google Sheets
                ws_turnos.append_row([fecha_hoy, app_usada, st.session_state.km_inicio_temp, km_out, base, promo, propina, sii, benc, mant, aho, p_mi])
                
                st.session_state.turno_activo = False
                st.session_state.km_inicio_temp = 0
                st.success("¡Turno guardado en Google Sheets con éxito!")
                st.rerun()

# PESTAÑA 3: GASTOS
with tab3:
    st.header("Registrar Gasto de Moto")
    with st.form("form_gastos"):
        tipo_gasto = st.selectbox("¿Qué pagaste?", ["Bencina", "Mantención"])
        monto_gasto = st.number_input("Monto total pagado ($):", min_value=1, step=500)
        btn_gasto = st.form_submit_button("💸 Registrar Gasto en Nube", use_container_width=True)
        
        if btn_gasto:
            fecha_hoy = datetime.now().strftime("%Y-%m-%d")
            ws_gastos.append_row([fecha_hoy, tipo_gasto, monto_gasto])
            st.success(f"Gasto de ${monto_gasto} guardado correctamente.")
            st.rerun()
