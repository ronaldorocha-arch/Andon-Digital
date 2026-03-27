import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÃO ---
DB_FILE = "registro_paradas.csv"
st.set_page_config(page_title="Andon NHS", page_icon="🚨", layout="centered")

# Atualiza a tela a cada 5 segundos
st_autorefresh(interval=5000, key="andon_refresh")

def get_br_time():
    return datetime.utcnow() - timedelta(hours=3)

def checar_chamados_ativos():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            return not df[df['Status'] == "🔴 Aberto"].empty
        except: return False
    return False

tem_chamado = checar_chamados_ativos()

# --- 2. ESTILO E ANIMAÇÃO ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    div.stButton > button {
        width: 100%;
        height: 70px !important;
        font-size: 18px !important;
        font-weight: bold !important;
        border-radius: 12px !important;
    }
    @keyframes alerta { 0% {background-color: #ff0000;} 50% {background-color: #660000;} 100% {background-color: #ff0000;} }
    .card-chamado {
        animation: alerta 0.8s infinite;
        color: white;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. JAVASCRIPT PARA SOM E VIBRAÇÃO ---
# Se houver chamado, este script roda no navegador do celular
if tem_chamado:
    st.markdown("""
        <script>
            // Função para vibrar (padrão SOS ou contínuo)
            if (navigator.vibrate) {
                navigator.vibrate([500, 200, 500, 200, 500]);
            }
            
            // Função para tocar o som
            var audio = new Audio('https://www.soundjay.com/buttons/beep-01a.mp3');
            audio.loop = true;
            audio.play().catch(function(error) {
                console.log("O navegador bloqueou o som. Clique no botão de ativação.");
            });
        </script>
        """, unsafe_allow_html=True)

# --- 4. INTERFACE ---
st.title("🚨 Andon Digital NHS")

# IMPORTANTE: O usuário DEVE clicar aqui uma vez para o navegador permitir som/vibração
if "audio_permitido" not in st.session_state:
    st.warning("⚠️ Para receber alertas, você precisa ativar o sistema abaixo:")
    if st.button("🔊 ATIVAR ALERTAS (SOM E VIBRAÇÃO)"):
        st.session_state.audio_permitido = True
        # Pequeno teste de vibração ao clicar
        st.markdown("<script>if(navigator.vibrate){navigator.vibrate(200);}</script>", unsafe_allow_html=True)
        st.rerun()

tabs = st.tabs(["📲 Operador", "💻 Assistente"])

with tabs[0]:
    st.subheader("Registrar Parada")
    ups = ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"]
    sel_ups = st.selectbox("Célula:", ups)
    
    # Lógica de salvar chamado (igual ao anterior)
    if st.button("🚨 ENVIAR CHAMADO", type="primary"):
        agora = get_br_time()
        df = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame(columns=["ID", "Célula", "Status", "Início", "Data", "Descrição"])
        nid = df['ID'].max() + 1 if not df.empty else 1
        novo = pd.DataFrame([{"ID": nid, "Célula": sel_ups, "Status": "🔴 Aberto", "Início": agora.strftime("%H:%M:%S"), "Data": agora.strftime("%d/%m/%Y"), "Descrição": "Parada de Linha"}])
        pd.concat([df, novo]).to_csv(DB_FILE, index=False)
        st.rerun()

with tabs[1]:
    st.subheader("Chamados Ativos")
    if tem_chamado:
        df_p = pd.read_csv(DB_FILE)
        abertos = df_p[df_p['Status'] == "🔴 Aberto"]
        for _, r in abertos.iterrows():
            st.markdown(f'<div class="card-chamado"><h2>{r["Célula"]}</h2><p>Início: {r["Início"]}</p></div>', unsafe_allow_html=True)
            if st.button(f"✅ FINALIZAR {r['Célula']}", key=f"f_{r['ID']}"):
                df_p.loc[df_p['ID'] == r['ID'], 'Status'] = "🟢 Finalizado"
                df_p.to_csv(DB_FILE, index=False)
                st.rerun()
    else:
        st.success("✅ Nenhuma parada.")
