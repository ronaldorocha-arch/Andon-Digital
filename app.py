import streamlit as st
import pandas as pd
import os
import requests
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÃO ---
DB_FILE = "registro_paradas.csv"
NTFY_TOPIC = "andon_nhs_curitiba"  # <--- Use este nome no App ntfy do celular

st.set_page_config(page_title="Andon NHS", page_icon="🚨", layout="centered")
st_autorefresh(interval=5000, key="andon_refresh")

def get_br_time():
    return datetime.utcnow() - timedelta(hours=3)

def enviar_notificacao_push(titulo, mensagem):
    """Envia o alerta real para o celular via NTFY"""
    try:
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}",
            data=mensagem.encode('utf-8'),
            headers={
                "Title": titulo,
                "Priority": "high",
                "Tags": "warning,rotating_light"
            }, timeout=5)
    except:
        pass

# --- 2. ESTILO APP ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    div.stButton > button {
        width: 100%;
        height: 80px !important;
        font-size: 20px !important;
        font-weight: bold !important;
        border-radius: 15px !important;
    }
    .alerta-card {
        background-color: #ff4b4b;
        color: white;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. INTERFACE ---
st.title("🚨 Andon NHS - Alerta Push")

st.info(f"📲 Para receber alertas no bolso:\n1. Baixe o app 'ntfy' no celular.\n2. Inscreva-se no tópico: **{NTFY_TOPIC}**")

tabs = st.tabs(["📲 Operador", "💻 Assistente"])

# --- ABA OPERADOR ---
with tabs[0]:
    st.subheader("Registrar Parada")
    ups = ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"]
    sel_ups = st.selectbox("Célula:", ups)
    
    motivos = ["Material", "Qualidade", "Processo", "Manutenção", "Outros"]
    motivo = st.radio("Motivo:", motivos, horizontal=True)
    
    if st.button("🚨 ENVIAR CHAMADO", type="primary"):
        agora = get_br_time()
        
        # Salva no Banco de Dados CSV
        df = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame(columns=["ID", "Célula", "Status", "Início", "Data", "Descrição"])
        nid = df['ID'].max() + 1 if not df.empty else 1
        novo = pd.DataFrame([{"ID": nid, "Célula": sel_ups, "Status": "🔴 Aberto", "Início": agora.strftime("%H:%M:%S"), "Data": agora.strftime("%d/%m/%Y"), "Descrição": motivo}])
        pd.concat([df, novo]).to_csv(DB_FILE, index=False)
        
        # DISPARA A NOTIFICAÇÃO QUE VIBRA O CELULAR
        enviar_notificacao_push(
            titulo=f"PARADA NA {sel_ups}",
            mensagem=f"Motivo: {motivo} às {agora.strftime('%H:%M')}"
        )
        
        st.success("Chamado enviado e celular notificado!")
        st.rerun()

# --- ABA ASSISTENTE ---
with tabs[1]:
    st.subheader("Chamados Ativos")
    if os.path.exists(DB_FILE):
        df_p = pd.read_csv(DB_FILE)
        abertos = df_p[df_p['Status'] == "🔴 Aberto"]
        
        if abertos.empty:
            st.success("✅ Nenhuma parada.")
        else:
            for _, r in abertos.iterrows():
                st.markdown(f'<div class="alerta-card"><h2>{r["Célula"]}</h2><p>{r["Descrição"]}</p></div>', unsafe_allow_html=True)
                if st.button(f"✅ FINALIZAR {r['Célula']}", key=f"f_{r['ID']}"):
                    df_p.loc[df_p['ID'] == r['ID'], 'Status'] = "🟢 Finalizado"
                    df_p.to_csv(DB_FILE, index=False)
                    st.rerun()
