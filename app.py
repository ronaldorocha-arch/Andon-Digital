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

# Atualização rápida de 2 segundos
st_autorefresh(interval=2000, key="andon_refresh_v3")

def get_br_time():
    return datetime.utcnow() - timedelta(hours=3)

def enviar_notificacao_push(titulo, mensagem):
    """Disparo imediato para o App ntfy"""
    try:
        # Gerar ID único para cada tentativa
        msg_id = str(int(time.time()))
        # Enviar para o servidor ntfy.sh
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=mensagem.encode('utf-8'),
            headers={
                "Title": titulo.encode('utf-8'),
                "Priority": "5",
                "Tags": "rotating_light,warning,fire",
                "X-Message-ID": msg_id,
                "X-Priority": "5"
            }, 
            timeout=5 # Aumentamos o tempo de espera do envio para garantir a saída
        )
    except:
        pass

def carregar_dados():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=["ID", "Célula", "Status", "Início", "Data", "Motivo", "Minutos"])
    return pd.read_csv(DB_FILE)

# --- 2. INTERFACE E ESTILO ---
st.markdown("""
    <style>
    div.stButton > button {
        width: 100%;
        height: 85px !important;
        font-size: 22px !important;
        font-weight: bold !important;
        border-radius: 15px !important;
    }
    @keyframes pisca { 0% {background-color: #ff0000;} 50% {background-color: #800000;} 100% {background-color: #ff0000;} }
    .card-alerta { animation: pisca 1s infinite; color: white; padding: 30px; border-radius: 20px; text-align: center; font-size: 28px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚨 Andon NHS - Curitiba")

df_atual = carregar_dados()
ativos = df_atual[df_atual['Status'] == "🔴 Aberto"]

tabs = st.tabs(["📲 Operador", "💻 Assistente"])

with tabs[0]:
    st.subheader("Abrir Chamado")
    ups = ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"]
    sel_ups = st.selectbox("Célula:", ups)
    
    ja_aberto = not ativos[ativos['Célula'] == sel_ups].empty

    if not ja_aberto:
        motivos = ["Material", "Qualidade", "Equipamento", "Processo", "Outros"]
        motivo_sel = st.radio("Motivo:", motivos, horizontal=True)
        
        if st.button("🚨 ENVIAR ALERTA", type="primary"):
            agora = get_br_time()
            
            # PRIMEIRO: Envia a notificação (Mais importante)
            enviar_notificacao_push(f"🚨 CHAMADO: {sel_ups}", f"Motivo: {motivo_sel} às {agora.strftime('%H:%M')}")
            
            # SEGUNDO: Salva no Banco de Dados
            nid = df_atual['ID'].max() + 1 if not df_atual.empty else 1
            novo = pd.DataFrame([{
                "ID": nid, "Célula": sel_ups, "Status": "🔴 Aberto", 
                "Início": agora.strftime("%H:%M:%S"), 
                "Data": agora.strftime("%d/%m/%Y"),
                "Motivo": motivo_sel,
                "Minutos": 0
            }])
            pd.concat([df_atual, novo]).to_csv(DB_FILE, index=False)
            
            st.success("✅ Alerta Push enviado!")
            st.rerun()
    else:
        st.markdown(f'<div class="card-alerta">⏳ AGUARDANDO APOIO<br>{sel_ups}</div>', unsafe_allow_html=True)

with tabs[1]:
    st.subheader("Chamados em Aberto")
    if not ativos.empty:
        for _, r in ativos.iterrows():
            st.error(f"⚠️ **{r['Célula']}** | Início: {r['Início']} | Motivo: {r['Motivo']}")
            if st.button(f"✅ FINALIZAR {r['Célula']}", key=f"f_{r['ID']}"):
                ag = get_br_time()
                df_atual.loc[df_atual['ID'] == r['ID'], 'Status'] = "🟢 Finalizado"
                df_atual.to_csv(DB_FILE, index=False)
                st.rerun()
    else:
        st.success("✅ Tudo em ordem.")
