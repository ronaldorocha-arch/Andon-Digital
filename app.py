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
st_autorefresh(interval=2000, key="andon_refresh_v10")

def get_br_time():
    return datetime.utcnow() - timedelta(hours=3)

def disparar_alerta_2x(titulo, mensagem):
    """
    Envia 2 bips com prioridade 4.
    Adicionado 'X-Priority' e 'Tags' específicos para forçar o som.
    """
    for i in range(2):
        try:
            msg_id = f"{int(time.time())}_{i}"
            requests.post(
                f"https://ntfy.sh/{NTFY_TOPIC}",
                data=f"{mensagem}".encode('utf-8'),
                headers={
                    "Title": titulo.encode('utf-8'),
                    "Priority": "high",       # Prioridade Alta (4)
                    "Tags": "bell,warning",   # Tags que forçam o som de sino/alerta
                    "X-Message-ID": msg_id
                }, 
                timeout=5
            )
            if i == 0:
                time.sleep(1.5) # Espaço entre os dois bips
        except:
            pass

# --- 2. BANCO DE DADOS ---
def carregar_dados():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=["ID", "Célula", "Status", "Início", "Data", "Motivo"])
    return pd.read_csv(DB_FILE)

df = carregar_dados()
ativos = df[df['Status'] == "🔴 Aberto"]

# --- 3. INTERFACE ---
st.title("🚨 Andon NHS - Teste de Som 2x")

tab1, tab2 = st.tabs(["📲 Operador", "💻 Assistente"])

with tab1:
    ups = ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"]
    sel_ups = st.selectbox("Célula:", ups)
    
    if st.button("🚨 ENVIAR CHAMADO", type="primary"):
        agora = get_br_time()
        # Salva
        nid = df['ID'].max() + 1 if not df.empty else 1
        novo = pd.DataFrame([{"ID": nid, "Célula": sel_ups, "Status": "🔴 Aberto", "Início": agora.strftime("%H:%M:%S"), "Data": agora.strftime("%d/%m/%Y"), "Motivo": "Apoio"}])
        pd.concat([df, novo]).to_csv(DB_FILE, index=False)
        # Toca 2 vezes
        disparar_alerta_2x(f"PARADA: {sel_ups}", f"Acionado às {agora.strftime('%H:%M')}")
        st.rerun()

with tab2:
    if not ativos.empty:
        for _, r in ativos.iterrows():
            st.error(f"⚠️ {r['Célula']} | {r['Início']}")
            if st.button(f"✅ FINALIZAR {r['Célula']}", key=f"f_{r['ID']}"):
                df.loc[df['ID'] == r['ID'], 'Status'] = "🟢 Finalizado"
                df.to_csv(DB_FILE, index=False)
                st.rerun()
    else:
        st.success("Tudo em ordem.")
