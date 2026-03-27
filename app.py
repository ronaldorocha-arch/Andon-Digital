import streamlit as st
import pandas as pd
import os
import requests
import time
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÃO ---
DB_FILE = "registro_paradas.csv"
NTFY_TOPIC = "andon_nhs_curitiba_producao" 

st.set_page_config(page_title="Andon NHS", page_icon="🚨", layout="centered")

# ATUALIZAÇÃO MAIS RÁPIDA: 2 segundos (2000ms)
st_autorefresh(interval=2000, key="andon_refresh_fast")

def get_br_time():
    return datetime.utcnow() - timedelta(hours=3)

def enviar_notificacao_push(titulo, mensagem):
    try:
        msg_id = str(int(time.time()))
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}",
            data=mensagem.encode('utf-8'),
            headers={
                "Title": titulo,
                "Priority": "5",
                "Tags": "rotating_light,warning",
                "X-Message-ID": msg_id
            }, timeout=3)
    except:
        pass

# Função de leitura otimizada para ser mais rápida
def carregar_dados_fast():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=["ID", "Célula", "Status", "Início", "Data", "Motivo", "Minutos"])
    return pd.read_csv(DB_FILE)

df_atual = carregar_dados_fast()
ativos = df_atual[df_atual['Status'] == "🔴 Aberto"]
tem_parada = not ativos.empty

# --- 2. ESTILO VISUAL ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    div.stButton > button {
        width: 100%;
        height: 85px !important;
        font-size: 22px !important;
        font-weight: bold !important;
        border-radius: 15px !important;
    }
    @keyframes pisca { 0% {background-color: #ff0000;} 50% {background-color: #800000;} 100% {background-color: #ff0000;} }
    .card-alerta {
        animation: pisca 0.8s infinite;
        color: white;
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        font-size: 28px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. INTERFACE ---
st.title("🚨 Andon NHS - Curitiba")

tabs = st.tabs(["📲 Operador", "💻 Assistente"])

with tabs[0]:
    st.subheader("Abrir Chamado")
    ups = ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"]
    sel_ups = st.selectbox("Célula:", ups)
    
    ja_aberto = not ativos[ativos['Célula'] == sel_ups].empty

    if not ja_aberto:
        motivos = ["Material", "Qualidade", "Equipamento", "Processo", "Outros"]
        motivo_sel = st.radio("Motivo:", motivos, horizontal=True)
        
        if st.button("🚨 DISPARAR ALERTA", type="primary"):
            agora = get_br_time()
            nid = df_atual['ID'].max() + 1 if not df_atual.empty else 1
            
            novo = pd.DataFrame([{
                "ID": nid, "Célula": sel_ups, "Status": "🔴 Aberto", 
                "Início": agora.strftime("%H:%M:%S"), 
                "Data": agora.strftime("%d/%m/%Y"),
                "Motivo": motivo_sel,
                "Minutos": 0
            }])
            pd.concat([df_atual, novo]).to_csv(DB_FILE, index=False)
            
            # Envia o Push imediatamente
            enviar_notificacao_push(f"🚨 {sel_ups}", f"Motivo: {motivo_sel}")
            
            st.rerun()
    else:
        st.markdown(f'<div class="card-alerta">⏳ AGUARDANDO APOIO<br>{sel_ups}</div>', unsafe_allow_html=True)

with tabs[1]:
    st.subheader("Atendimentos Ativos")
    if not ativos.empty:
        for _, r in ativos.iterrows():
            st.error(f"⚠️ **{r['Célula']}** | {r['Início']}")
            if st.button(f"✅ FINALIZAR {r['Célula']}", key=f"f_{r['ID']}"):
                ag = get_br_time()
                df_atual.loc[df_atual['ID'] == r['ID'], 'Status'] = "🟢 Finalizado"
                
                # Cálculo automático de minutos parados
                h_ini = datetime.strptime(r['Início'], "%H:%M:%S")
                delta = (ag - datetime.combine(ag.date(), h_ini.time())).total_seconds() / 60
                df_atual.loc[df_atual['ID'] == r['ID'], 'Minutos'] = round(delta, 1)
                
                df_atual.to_csv(DB_FILE, index=False)
                st.rerun()
    else:
        st.success("✅ Tudo em ordem.")
