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

# Atualização do painel a cada 2 segundos
st_autorefresh(interval=2000, key="andon_refresh_v9")

def get_br_time():
    return datetime.utcnow() - timedelta(hours=3)

def disparar_alerta_2x(titulo, mensagem):
    """
    Envia 2 notificações com Prioridade 4 (Alta).
    Isso garante que o celular VIBRE e TOQUE, mas pare sozinho.
    """
    for i in range(2):
        try:
            # ID único para garantir que o segundo toque ocorra
            msg_id = f"{int(time.time())}_{i}"
            
            requests.post(
                f"https://ntfy.sh/{NTFY_TOPIC}",
                data=f"{mensagem}".encode('utf-8'),
                headers={
                    "Title": titulo.encode('utf-8'),
                    "Priority": "4",          # PRIORIDADE 4: Acorda o celular e vibra, mas não trava o som
                    "Tags": "warning,bell",
                    "X-Message-ID": msg_id
                }, 
                timeout=5
            )
            # Pequeno intervalo entre os bips
            if i == 0:
                time.sleep(1.2) 
        except:
            pass

def carregar_dados():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=["ID", "Célula", "Status", "Início", "Data", "Motivo"])
    try:
        return pd.read_csv(DB_FILE)
    except:
        return pd.DataFrame(columns=["ID", "Célula", "Status", "Início", "Data", "Motivo"])

# --- 2. ESTILO ---
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
    @keyframes pisca { 0% {background-color: red;} 50% {background-color: #800000;} 100% {background-color: red;} }
    .card-alerta {
        animation: pisca 1s infinite;
        color: white;
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        font-size: 26px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. INTERFACE ---
st.title("🚨 Andon NHS - Alerta 2x Garantido")

df = carregar_dados()
ativos = df[df['Status'] == "🔴 Aberto"]

tab1, tab2 = st.tabs(["📲 Operador", "💻 Assistente"])

with tab1:
    st.subheader("Abrir Chamado")
    ups = ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"]
    sel_ups = st.selectbox("Célula:", ups)
    
    ja_aberto = not ativos[ativos['Célula'] == sel_ups].empty

    if not ja_aberto:
        if st.button("🚨 ENVIAR CHAMADO", type="primary"):
            agora = get_br_time()
            
            # SALVAR NO CSV
            nid = df['ID'].max() + 1 if not df.empty else 1
            novo = pd.DataFrame([{
                "ID": nid, "Célula": sel_ups, "Status": "🔴 Aberto", 
                "Início": agora.strftime("%H:%M:%S"), "Data": agora.strftime("%d/%m/%Y"),
                "Motivo": "Apoio solicitado"
            }])
            pd.concat([df, novo]).to_csv(DB_FILE, index=False)
            
            # DISPARAR 2 BIPS COM VIBRAÇÃO
            disparar_alerta_2x(f"🚨 PARADA: {sel_ups}", f"Chamado às {agora.strftime('%H:%M')}")
            
            st.success("Chamado enviado! O celular vai vibrar e apitar 2 vezes.")
            st.rerun()
    else:
        st.markdown(f'<div class="card-alerta">⏳ AGUARDANDO APOIO<br>{sel_ups}</div>', unsafe_allow_html=True)

with tab2:
    st.subheader("Chamados Ativos")
    if not ativos.empty:
        for _, r in ativos.iterrows():
            st.error(f"⚠️ **{r['Célula']}** | Início: {r['Início']}")
            if st.button(f"✅ FINALIZAR {r['Célula']}", key=f"f_{r['ID']}"):
                df.loc[df['ID'] == r['ID'], 'Status'] = "🟢 Finalizado"
                df.to_csv(DB_FILE, index=False)
                st.rerun()
    else:
        st.success("✅ Nenhuma parada ativa.")
