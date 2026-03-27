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
st_autorefresh(interval=2000, key="andon_refresh_v7")

def get_br_time():
    """Retorna o horário de Brasília"""
    return datetime.utcnow() - timedelta(hours=3)

def disparar_alerta_2x(titulo, mensagem):
    """
    Envia a notificação exatamente 2 vezes para o telemóvel.
    O intervalo de 1.5s garante que o sistema operacional processe os dois sons.
    """
    for i in range(2):
        try:
            # ID único para cada um dos 2 toques para o telemóvel não ignorar
            msg_id = f"{int(time.time())}_{i}"
            
            requests.post(
                f"https://ntfy.sh/{NTFY_TOPIC}",
                data=f"{mensagem} (Alerta {i+1}/2)".encode('utf-8'),
                headers={
                    "Title": titulo.encode('utf-8'),
                    "Priority": "5",
                    "Tags": "warning,bell",
                    "X-Message-ID": msg_id
                }, 
                timeout=5
            )
            if i == 0:
                time.sleep(1.5) # Espera 1.5 segundos antes do segundo toque
        except:
            pass

def carregar_dados():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=["ID", "Célula", "Status", "Início", "Data", "Motivo"])
    try:
        return pd.read_csv(DB_FILE)
    except:
        return pd.DataFrame(columns=["ID", "Célula", "Status", "Início", "Data", "Motivo"])

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

# --- 3. LÓGICA E INTERFACE ---
st.title("🚨 Andon NHS - Alerta Duplo")

df = carregar_dados()
ativos = df[df['Status'] == "🔴 Aberto"]

tabs = st.tabs(["📲 Operador", "💻 Assistente"])

# --- ABA OPERADOR ---
with tabs[0]:
    st.subheader("Abrir Chamado")
    ups = ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"]
    sel_ups = st.selectbox("Célula:", ups)
    
    # Verifica se já existe chamado para esta célula
    ja_aberto = not ativos[ativos['Célula'] == sel_ups].empty

    if not ja_aberto:
        if st.button("🚨 ENVIAR CHAMADO", type="primary"):
            agora = get_br_time()
            
            # 1. SALVAR NO CSV PRIMEIRO
            nid = df['ID'].max() + 1 if not df.empty else 1
            novo = pd.DataFrame([{
                "ID": nid, 
                "Célula": sel_ups, 
                "Status": "🔴 Aberto", 
                "Início": agora.strftime("%H:%M:%S"), 
                "Data": agora.strftime("%d/%m/%Y"),
                "Motivo": "Chamado de Apoio"
            }])
            pd.concat([df, novo]).to_csv(DB_FILE, index=False)
            
            # 2. DISPARAR OS 2 TOQUES NO TELEMÓVEL
            disparar_alerta_2x(f"🚨 PARADA: {sel_ups}", f"Acionado às {agora.strftime('%H:%M:%S')}")
            
            st.success("Chamado enviado! O telemóvel irá tocar 2 vezes.")
            st.rerun()
    else:
        st.markdown(f'<div class="card-alerta">⏳ AGUARDANDO APOIO<br>{sel_ups}</div>', unsafe_allow_html=True)

# --- ABA ASSISTENTE ---
with tabs[1]:
    st.subheader("Chamados Ativos")
    if not ativos.empty:
        for _, r in ativos.iterrows():
            with st.container():
                st.error(f"⚠️ **{r['Célula']}** | Início: {r['Início']}")
                if st.button(f"✅ FINALIZAR {r['Célula']}", key=f"btn_{r['ID']}"):
                    df.loc[df['ID'] == r['ID'], 'Status'] = "🟢 Finalizado"
                    df.to_csv(DB_FILE, index=False)
                    st.rerun()
    else:
        st.success("✅ Nenhuma parada ativa.")

# --- INFO LATERAL ---
st.sidebar.markdown("### ⚙️ Ajuste de Som")
st.sidebar.info(f"Tópico: **{NTFY_TOPIC}**")
st.sidebar.write("1. No App **ntfy**, escolha um som **CURTO**.")
st.sidebar.write("2. O sistema enviará 2 pulsos de som.")
