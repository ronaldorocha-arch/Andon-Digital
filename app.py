import streamlit as st
import pandas as pd
import os
import requests
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÃO ---
DB_FILE = "registro_paradas.csv"
# Tópico único para sua fábrica (mude se quiser mais privacidade)
NTFY_TOPIC = "andon_nhs_curitiba_producao" 

st.set_page_config(page_title="Andon NHS", page_icon="🚨", layout="centered")

# Atualiza a tela a cada 5 segundos para verificar novos chamados
st_autorefresh(interval=5000, key="andon_refresh")

def get_br_time():
    return datetime.utcnow() - timedelta(hours=3)

def enviar_notificacao_push(titulo, mensagem):
    """
    Envia alerta de alta prioridade para o App ntfy.
    Isso faz o celular vibrar e apitar mesmo bloqueado.
    """
    try:
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}",
            data=mensagem.encode('utf-8'),
            headers={
                "Title": titulo,
                "Priority": "5", # Prioridade MÁXIMA (Urgente)
                "Tags": "rotating_light,warning,fire",
                "Actions": "view, Abrir Painel, https://seu-link-do-streamlit.app"
            }, timeout=5)
    except:
        pass

def checar_ativos():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        return not df[df['Status'] == "🔴 Aberto"].empty
    return False

tem_chamado = checar_ativos()

# --- 2. ESTILO VISUAL ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Botões Grandes para Operação de Fábrica */
    div.stButton > button {
        width: 100%;
        height: 80px !important;
        font-size: 20px !important;
        font-weight: bold !important;
        border-radius: 15px !important;
        margin-bottom: 10px;
    }
    
    /* Card de Alerta Piscante */
    @keyframes pisca { 0% {background-color: #ff4b4b;} 50% {background-color: #800000;} 100% {background-color: #ff4b4b;} }
    .alerta-card {
        animation: pisca 1s infinite;
        color: white;
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 20px;
        font-size: 24px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. JAVASCRIPT PARA VIBRAÇÃO (SE ABA ABERTA) ---
if tem_chamado:
    st.markdown("""
        <script>
        if (navigator.vibrate) {
            // Vibra em padrão de alerta repetido
            navigator.vibrate([500, 300, 500, 300, 500]);
        }
        </script>
        """, unsafe_allow_html=True)

# --- 4. INTERFACE ---
st.title("🚨 Andon Digital - NHS")

# Instrução de configuração do Push
with st.expander("📲 Configurar Alerta no Bolso (Clique aqui)"):
    st.write(f"""
    1. Instale o app **ntfy** (Play Store ou App Store).
    2. Clique no '+' e digite o tópico: `{NTFY_TOPIC}`.
    3. Nas configurações do ntfy no celular, coloque a prioridade como **MÁXIMA**.
    """)

tabs = st.tabs(["📲 Operador", "💻 Painel Assistente"])

# --- ABA DO OPERADOR (LINHA DE PRODUÇÃO) ---
with tabs[0]:
    st.subheader("Registrar Nova Parada")
    ups = ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"]
    sel_ups = st.selectbox("Selecione sua Célula:", ups)
    
    # Checa se já existe chamado aberto para essa célula específica
    ja_aberto = False
    if os.path.exists(DB_FILE):
        df_check = pd.read_csv(DB_FILE)
        ja_aberto = not df_check[(df_check['Célula'] == sel_ups) & (df_check['Status'] == "🔴 Aberto")].empty

    if not ja_aberto:
        motivos = ["Material", "Qualidade", "Processo", "Manutenção", "Outros"]
        motivo = st.radio("Qual o problema?", motivos, horizontal=True)
        obs = st.text_input("Observação (Opcional):")
        
        if st.button("🔔 ENVIAR CHAMADO", type="primary"):
            agora = get_br_time()
            df = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame(columns=["ID", "Célula", "Motivo", "Início", "Status", "Data"])
            
            nid = df['ID'].max() + 1 if not df.empty else 1
            novo = pd.DataFrame([{
                "ID": nid, "Célula": sel_ups, "Motivo": motivo, 
                "Início": agora.strftime("%H:%M:%S"), "Status": "🔴 Aberto", 
                "Data": agora.strftime("%d/%m/%Y")
            }])
            
            pd.concat([df, novo]).to_csv(DB_FILE, index=False)
            
            # DISPARA O PUSH PARA O CELULAR
            enviar_notificacao_push(
                titulo=f"🚨 CHAMADO: {sel_ups}",
                mensagem=f"Problema: {motivo} | Hora: {agora.strftime('%H:%M')}"
            )
            
            st.success("Chamado enviado! O assistente foi notificado.")
            st.rerun()
    else:
        st.markdown(f'<div class="alerta-card">⏳ AGUARDANDO APOIO<br>{sel_ups}</div>', unsafe_allow_html=True)

# --- ABA DO ASSISTENTE (QUEM RESOLVE) ---
with tabs[1]:
    st.subheader("Chamados em Aberto")
    if os.path.exists(DB_FILE):
        df_painel = pd.read_csv(DB_FILE)
        ativos = df_painel[df_painel['Status'] == "🔴 Aberto"]
        
        if ativos.empty:
            st.success("✅ Tudo em ordem na produção.")
        else:
            for _, r in ativos.iterrows():
                with st.container():
                    st.error(f"**Célula: {r['Célula']}** | Início: {r['Início']}")
                    st.write(f"Motivo: {r['Motivo']}")
                    
                    if st.button(f"✅ ATENDER E FINALIZAR {r['Célula']}", key=f"fin_{r['ID']}"):
                        df_painel.loc[df_painel['ID'] == r['ID'], 'Status'] = "🟢 Finalizado"
                        df_painel.to_csv(DB_FILE, index=False)
                        st.rerun()
