import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Control Moto", page_icon="🛵", layout="centered")

# --- VARIABLES Y PORCENTAJES ---
SII_PCT = 0.1375
BENCINA_PCT = 0.15
MANT_PCT = 0.15
AHORRO_PCT = 0.10

# --- INICIALIZAR BASE DE DATOS TEMPORAL (MEMORIA) ---
# Nota: Para una versión final, esto se conecta a Google Sheets.
if 'turnos' not in st.session_state:
    st.session_state.turnos = pd.DataFrame(columns=[
        'Fecha', 'App', 'KM_Inicial', 'KM_Final', 'Base', 'Promo', 'Propina', 
        'SII', 'Fondo_Bencina', 'Fondo_Mant', 'Fondo_Ahorro', 'Para_Mi'
    ])
if 'gastos' not in st.session_state:
    st.session_state.gastos = pd.DataFrame(columns=['Fecha', 'Tipo', 'Monto'])
if 'turno_activo' not in st.session_state:
    st.session_state.turno_activo = False
if 'km_inicio_temp' not in st.session_state:
    st.session_state.km_inicio_temp = 0

# --- LÓGICA DE CÁLCULO ---
def calcular_reparticion(base, promo, propina):
    imponible = base + promo
    sii = imponible * SII_PCT
    neto_app = imponible - sii
    
    # Fondos solo de lo que paga la app (sin propina)
    bencina = neto_app * BENCINA_PCT
    mantencion = neto_app * MANT_PCT
    
    # Ahorro de todo lo ganado
    neto_total = neto_app + propina
    ahorro = neto_total * AHORRO_PCT
    
    # Bolsillo libre
    para_mi = neto_total - bencina - mantencion - ahorro
    
    return sii, bencina, mantencion, ahorro, para_mi

# --- INTERFAZ DE USUARIO (PESTAÑAS) ---
tab1, tab2, tab3 = st.tabs(["📊 Panel Principal", "🛵 Mi Turno", "💸 Registrar Gasto"])

# === PESTAÑA 1: PANEL PRINCIPAL (DASHBOARD) ===
with tab1:
    st.title("Mi Panel Financiero")
    
    # Calcular totales
    totales = st.session_state.turnos.sum(numeric_only=True)
    gastos_bencina = st.session_state.gastos[st.session_state.gastos['Tipo'] == 'Bencina']['Monto'].sum()
    gastos_mant = st.session_state.gastos[st.session_state.gastos['Tipo'] == 'Mantención']['Monto'].sum()
    
    disp_bencina = totales.get('Fondo_Bencina', 0) - gastos_bencina
    disp_mant = totales.get('Fondo_Mant', 0) - gastos_mant
    total_ahorro = totales.get('Fondo_Ahorro', 0)
    total_bolsillo = totales.get('Para_Mi', 0)
    
    st.subheader("Estado de tus Fondos")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("🤑 Libre Para Mí", f"${total_bolsillo:,.0f}".replace(",", "."))
        st.metric("⛽ Fondo Bencina (15%)", f"${disp_bencina:,.0f}".replace(",", "."))
    with col2:
        st.metric("🏦 Mi Ahorro (10%)", f"${total_ahorro:,.0f}".replace(",", "."))
        st.metric("🔧 Fondo Mantención (15%)", f"${disp_mant:,.0f}".replace(",", "."))
    
    st.divider()
    st.write("Últimos turnos registrados:")
    st.dataframe(st.session_state.turnos[['Fecha', 'App', 'Base', 'Propina', 'Para_Mi']].tail(3))

# === PESTAÑA 2: REGISTRAR TURNO ===
with tab2:
    st.header("Control de Turno Diario")
    
    if not st.session_state.turno_activo:
        st.info("No tienes ningún turno activo. Ingresa tu kilometraje para empezar.")
        km_in = st.number_input("Kilometraje al INICIAR el turno:", min_value=0, step=1)
        if st.button("🚀 Iniciar Turno", use_container_width=True):
            st.session_state.km_inicio_temp = km_in
            st.session_state.turno_activo = True
            st.rerun()
    
    else:
        st.success(f"Turno en curso. Iniciaste con: {st.session_state.km_inicio_temp} KM")
        
        with st.form("form_finalizar_turno"):
            app_usada = st.selectbox("Aplicación", ["PedidosYa", "Uber Eats", "Ambas"])
            km_out = st.number_input("Kilometraje al FINALIZAR:", min_value=st.session_state.km_inicio_temp, step=1)
            
            st.write("--- Ingresos del Turno ---")
            col1, col2, col3 = st.columns(3)
            with col1: base = st.number_input("Ingreso Base ($)", min_value=0, step=100)
            with col2: promo = st.number_input("Promociones ($)", min_value=0, step=100)
            with col3: propina = st.number_input("Propinas ($)", min_value=0, step=100)
            
            submit = st.form_submit_button("🏁 Finalizar y Guardar Turno", use_container_width=True)
            
            if submit:
                # Calcular repartición
                sii, benc, mant, aho, p_mi = calcular_reparticion(base, promo, propina)
                
                # Guardar en DataFrame
                nuevo_turno = pd.DataFrame([{
                    'Fecha': datetime.now().strftime("%Y-%m-%d"),
                    'App': app_usada,
                    'KM_Inicial': st.session_state.km_inicio_temp,
                    'KM_Final': km_out,
                    'Base': base,
                    'Promo': promo,
                    'Propina': propina,
                    'SII': sii,
                    'Fondo_Bencina': benc,
                    'Fondo_Mant': mant,
                    'Fondo_Ahorro': aho,
                    'Para_Mi': p_mi
                }])
                
                st.session_state.turnos = pd.concat([st.session_state.turnos, nuevo_turno], ignore_index=True)
                
                # Resetear estado
                st.session_state.turno_activo = False
                st.session_state.km_inicio_temp = 0
                st.success("¡Turno guardado con éxito! Revisa tus fondos en el panel principal.")
                st.rerun()

# === PESTAÑA 3: REGISTRAR GASTO ===
with tab3:
    st.header("Registrar Gasto de Moto")
    
    with st.form("form_gastos"):
        tipo_gasto = st.selectbox("¿Qué pagaste?", ["Bencina", "Mantención"])
        monto_gasto = st.number_input("Monto total pagado ($):", min_value=1, step=500)
        
        btn_gasto = st.form_submit_button("💸 Registrar Pago", use_container_width=True)
        
        if btn_gasto:
            nuevo_gasto = pd.DataFrame([{
                'Fecha': datetime.now().strftime("%Y-%m-%d"),
                'Tipo': tipo_gasto,
                'Monto': monto_gasto
            }])
            st.session_state.gastos = pd.concat([st.session_state.gastos, nuevo_gasto], ignore_index=True)
            st.success(f"Descontado ${monto_gasto} de tu fondo de {tipo_gasto}.")
            st.rerun()