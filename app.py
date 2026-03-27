import streamlit as st
import pandas as pd
import os
import requests
import time
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÃO ---
DB_FILE = "registro_paradas.csv"
# Tópico para o app ntfy (Configure o mesmo nome no seu celular)
NTFY_TOPIC = "andon_nhs_curitiba_producao" 

st.set_page_config(page_title="Andon NHS", page_icon="🚨", layout="centered")

# ATUALIZAÇÃO RÁPIDA: 2 segundos para o painel refletir o chamado quase instantâneo
st_autorefresh(interval=2000, key="andon_refresh_final")

def get_br_time():
    return datetime.utcnow() - timedelta(hours=3)

def enviar_notificacao_push(titulo, mensagem):
    """
    Envia o alerta para o celular. 
    O 'X-Message-ID' impede que o celular agrupe e silencie as repetições.
    """
    try:
        msg_id = str(int(time.time()))
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=mensagem.encode('utf-8'),
            headers={
                "Title": titulo.encode('utf-8'),
                "Priority": "5",
                "Tags": "rotating_light,warning,loud_sound", # loud_sound força o toque
                "X-Message-ID": msg_id,
                "X-Priority": "5"
            }, 
            timeout=5
        )
    except Exception as e:
        print(f"Erro no envio: {e}")

def carregar_dados():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=["ID", "Célula", "Status", "Início", "Data", "Motivo", "Minutos"])
    try:
        return pd.read_csv(DB_FILE)
    except:
        return pd.DataFrame(columns=["ID", "Célula", "Status", "Início", "Data", "Motivo", "Minutos"])

# --- 2. ESTILO VISUAL ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Botões Grandes para Operação */
    div.stButton > button {
        width: 100%;
        height: 85px !important;
        font-size: 22px !important;
        font-weight: bold !important;
        border-radius: 15px !important;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
    }
    
    /* Card de Alerta Piscante */
    @keyframes pisca { 0% {background-color: #ff0000;} 50% {background-color: #800000;} 100% {background-color: #ff0000;} }
    .card-alerta {
        animation: pisca 0.8s infinite;
        color: white;
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 25px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LÓGICA DE DADOS ---
df_atual = carregar_dados()
ativos = df_atual[df_atual['Status'] == "🔴 Aberto"]

# --- 4. INTERFACE ---
st.title("🚨 Andon Digital NHS")

tabs = st.tabs(["📲 Operador", "💻 Painel Assistente"])

# --- ABA OPERADOR ---
with tabs[0]:
    st.subheader("Abrir Chamado de Parada")
    ups = ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"]
    sel_ups = st.selectbox("Selecione sua Célula:", ups)
    
    # Verifica se já há chamado para esta célula
    ja_aberto = not ativos[ativos['Célula'] == sel_ups].empty

    if not ja_aberto:
        motivos = ["Falta de Material", "Qualidade", "Falha Equipamento", "Processo", "Outros"]
        motivo_sel = st.radio("Motivo:", motivos, horizontal=True)
        
        if st.button("🚨 DISPARAR ALERTA", type="primary"):
            agora = get_br_time()
            
            # 1. DISPARO DO PUSH (IMEDIATO)
            enviar_notificacao_push(
                titulo=f"🚨 CHAMADO: {sel_ups}", 
                mensagem=f"Problema: {motivo_sel} às {agora.strftime('%H:%M')}"
            )
            
            # 2. SALVAMENTO NO BANCO
            nid = df_atual['ID'].max() + 1 if not df_atual.empty else 1
            novo = pd.DataFrame([{
                "ID": nid, "Célula": sel_ups, "Status": "🔴 Aberto", 
                "Início": agora.strftime("%H:%M:%S"), 
                "Data": agora.strftime("%d/%m/%Y"),
                "Motivo": motivo_sel,
                "Minutos": 0
            }])
            pd.concat([df_atual, novo]).to_csv(DB_FILE, index=False)
            
            st.success("✅ Alerta Push enviado com sucesso!")
            st.rerun()
    else:
        st.markdown(f'<div class="card-alerta">⏳ AGUARDANDO ASSISTENTE<br>{sel_ups}</div>', unsafe_allow_html=True)

# --- ABA ASSISTENTE ---
with tabs[1]:
    st.subheader("Chamados em Aberto")
    if not ativos.empty:
        for _, r in ativos.iterrows():
            with st.container():
                st.error(f"⚠️ **Célula: {r['Célula']}** | Início: {r['Início']}")
                st.write(f"Motivo: {r['Motivo']}")
                
                if st.button(f"✅ FINALIZAR {r['Célula']}", key=f"btn_fin_{r['ID']}"):
                    ag = get_br_time()
                    df_atual.loc[df_atual['ID'] == r['ID'], 'Status'] = "🟢 Finalizado"
                    
                    # Cálculo de minutos parados
                    h_ini = datetime.strptime(r['Início'], "%H:%M:%S")
                    duracao = (ag - datetime.combine(ag.date(), h_ini.time())).total_seconds() / 60
                    df_atual.loc[df_atual['ID'] == r['ID'], 'Minutos'] = round(duracao, 1)
                    
                    df_atual.to_csv(DB_FILE, index=False)
                    st.rerun()
    else:
        st.success("✅ Nenhuma parada ativa no momento.")

# --- BARRA LATERAL (CONFIGS) ---
st.sidebar.markdown("### Configuração do Alerta")
st.sidebar.info(f"Tópico ntfy: **{NTFY_TOPIC}**")
st.sidebar.write("1. No app ntfy, clique no '+' e siga o tópico acima.")
st.sidebar.write("2. No celular, mude o som da notificação para um **Alarme longo**.")
