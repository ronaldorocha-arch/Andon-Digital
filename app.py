import streamlit as st
import pandas as pd
import os
import requests
import time
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÕES TÉCNICAS ---
DB_FILE = "registro_paradas.csv"
# IMPORTANTE: Use este mesmo nome no tópico do App ntfy no celular
NTFY_TOPIC = "andon_nhs_curitiba_producao" 

st.set_page_config(page_title="Andon NHS", page_icon="🚨", layout="centered")

# Atualização do painel a cada 2 segundos para resposta rápida
st_autorefresh(interval=2000, key="andon_refresh_final")

def get_br_time():
    """Retorna o horário atual de Brasília"""
    return datetime.utcnow() - timedelta(hours=3)

def enviar_notificacao_push(titulo, mensagem):
    """
    Envia o alerta para o celular do assistente.
    O uso de X-Message-ID com timestamp força o celular a tocar em todas as tentativas.
    """
    try:
        # Gera um ID único baseado nos milissegundos para evitar agrupamento de notificações
        msg_id = str(int(time.time() * 1000))
        
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=mensagem.encode('utf-8'),
            headers={
                "Title": titulo.encode('utf-8'),
                "Priority": "5",          # Prioridade MÁXIMA (Urgente)
                "Tags": "rotating_light,warning,fire",
                "X-Message-ID": msg_id,   # Força o toque individual
                "X-Priority": "5"
            }, 
            timeout=5
        )
    except Exception as e:
        st.error(f"Erro ao disparar alerta: {e}")

def carregar_dados():
    """Lê o banco de dados CSV com segurança"""
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=["ID", "Célula", "Status", "Início", "Data", "Motivo", "Minutos"])
    try:
        return pd.read_csv(DB_FILE)
    except:
        return pd.DataFrame(columns=["ID", "Célula", "Status", "Início", "Data", "Motivo", "Minutos"])

# --- 2. ESTILO VISUAL (LAYOUT DE FÁBRICA) ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Botões gigantes para facilitar o clique na linha de produção */
    div.stButton > button {
        width: 100%;
        height: 90px !important;
        font-size: 24px !important;
        font-weight: bold !important;
        border-radius: 15px !important;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.3);
    }
    
    /* Card de Alerta Piscante */
    @keyframes pisca_vermelho { 0% {background-color: #ff0000;} 50% {background-color: #660000;} 100% {background-color: #ff0000;} }
    .card-emergencia {
        animation: pisca_vermelho 0.8s infinite;
        color: white;
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LOGICA DO SISTEMA ---
df_atual = carregar_dados()
ativos = df_atual[df_atual['Status'] == "🔴 Aberto"]

st.title("🚨 Andon NHS - Curitiba")

tabs = st.tabs(["📲 Operador (Abrir Chamado)", "💻 Assistente (Atender)"])

# --- ABA OPERADOR (LINHA DE PRODUÇÃO) ---
with tabs[0]:
    st.subheader("Registrar Parada de Máquina/Processo")
    ups_lista = ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"]
    sel_ups = st.selectbox("Selecione sua Célula:", ups_lista)
    
    # Bloqueia novo chamado se já houver um aberto para a mesma célula
    esta_parada = not ativos[ativos['Célula'] == sel_ups].empty

    if not esta_parada:
        motivos = ["Falta de Material", "Qualidade", "Falha de Equipamento", "Dúvida de Processo", "Outros"]
        motivo_escolhido = st.radio("Qual o motivo da parada?", motivos, horizontal=True)
        
        if st.button("🔔 DISPARAR CHAMADO", type="primary"):
            agora = get_br_time()
            
            # 1. DISPARA O PUSH (Vibra e Toca no Celular)
            enviar_notificacao_push(
                titulo=f"🚨 PARADA: {sel_ups}", 
                mensagem=f"{motivo_escolhido} às {agora.strftime('%H:%M:%S')}"
            )
            
            # 2. REGISTRA NO CSV
            proximo_id = df_atual['ID'].max() + 1 if not df_atual.empty else 1
            novo_registro = pd.DataFrame([{
                "ID": proximo_id, 
                "Célula": sel_ups, 
                "Status": "🔴 Aberto", 
                "Início": agora.strftime("%H:%M:%S"), 
                "Data": agora.strftime("%d/%m/%Y"),
                "Motivo": motivo_escolhido,
                "Minutos": 0
            }])
            pd.concat([df_atual, novo_registro]).to_csv(DB_FILE, index=False)
            
            st.success("Chamado enviado! O assistente foi notificado.")
            st.rerun()
    else:
        st.markdown(f'<div class="card-emergencia">⏳ AGUARDANDO ASSISTENTE<br>{sel_ups}</div>', unsafe_allow_html=True)

# --- ABA ASSISTENTE (ATENDIMENTO) ---
with tabs[1]:
    st.subheader("Chamados Pendentes")
    if not ativos.empty:
        for index, row in ativos.iterrows():
            with st.container():
                st.error(f"⚠️ **{row['Célula']}** | Aberto às: {row['Início']}")
                st.info(f"Motivo: {row['Motivo']}")
                
                if st.button(f"✅ FINALIZAR ATENDIMENTO {row['Célula']}", key=f"btn_{row['ID']}"):
                    agora_fim = get_br_time()
                    
                    # Atualiza o CSV
                    df_atual.loc[df_atual['ID'] == row['ID'], 'Status'] = "🟢 Finalizado"
                    
                    # Cálculo de tempo de resposta (opcional)
                    h_ini = datetime.strptime(row['Início'], "%H:%M:%S")
                    duracao = (agora_fim - datetime.combine(agora_fim.date(), h_ini.time())).total_seconds() / 60
                    df_atual.loc[df_atual['ID'] == row['ID'], 'Minutos'] = round(duracao, 1)
                    
                    df_atual.to_csv(DB_FILE, index=False)
                    st.rerun()
    else:
        st.success("✅ Nenhuma pendência. Linhas em operação normal.")

# --- DICAS DE CONFIGURAÇÃO (LATERAL) ---
st.sidebar.title("⚙️ Configurações")
st.sidebar.markdown(f"**Tópico Push:** `{NTFY_TOPIC}`")
st.sidebar.write("1. No app **ntfy**, siga este tópico.")
st.sidebar.write("2. No celular, mude o som para um **Alarme longo**.")
st.sidebar.write("3. Desative a 'Otimização de Bateria' para o ntfy.")
