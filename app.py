import streamlit as st
import pandas as pd
import os
import requests
import time
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÃO ---
DB_FILE = "registro_paradas.csv"
# Tópico para o app ntfy (instale o app e siga este tópico)
NTFY_TOPIC = "andon_nhs_curitiba_producao" 

st.set_page_config(page_title="Andon NHS", page_icon="🚨", layout="centered")

# Atualiza a interface a cada 5 segundos
st_autorefresh(interval=5000, key="andon_refresh")

def get_br_time():
    return datetime.utcnow() - timedelta(hours=3)

def enviar_notificacao_push(titulo, mensagem):
    """
    Envia alerta de prioridade MÁXIMA.
    O uso do timestamp (time.time()) garante que o celular vibre em TODAS as tentativas.
    """
    try:
        # Gera um ID único para cada disparo
        msg_id = str(int(time.time()))
        
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}",
            data=mensagem.encode('utf-8'),
            headers={
                "Title": titulo,
                "Priority": "5", # Prioridade Urgente
                "Tags": "rotating_light,warning,fire",
                "X-Message-ID": msg_id, # Força o celular a tratar como nova mensagem
                "X-Priority": "5",
                "X-Title": titulo.encode('utf-8')
            }, timeout=5)
    except Exception as e:
        print(f"Erro ao enviar push: {e}")

def checar_chamados_ativos():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            return not df[df['Status'] == "🔴 Aberto"].empty
        except: return False
    return False

tem_parada = checar_chamados_ativos()

# --- 2. ESTILO VISUAL APP ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Botões Grandes para Uso em Fábrica */
    div.stButton > button {
        width: 100%;
        height: 85px !important;
        font-size: 22px !important;
        font-weight: bold !important;
        border-radius: 15px !important;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.2);
    }
    
    /* Alerta Visual de Chamado */
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

# --- 3. INTERFACE ---
st.title("🚨 Andon NHS - Produção")

tabs = st.tabs(["📲 Operador (Abrir)", "💻 Assistente (Atender)"])

# --- ABA OPERADOR ---
with tabs[0]:
    st.subheader("Nova Parada de Linha")
    ups = ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"]
    sel_ups = st.selectbox("Selecione sua Célula:", ups)
    
    # Verifica se a célula já está com chamado aberto
    ja_aberto = False
    if os.path.exists(DB_FILE):
        df_verificacao = pd.read_csv(DB_FILE)
        ja_aberto = not df_verificacao[(df_verificacao['Célula'] == sel_ups) & (df_verificacao['Status'] == "🔴 Aberto")].empty

    if not ja_aberto:
        motivos = ["Falta de Material", "Qualidade", "Falha Equipamento", "Problema Processo", "Outros"]
        motivo_sel = st.radio("Motivo Principal:", motivos, horizontal=True)
        detalhe = st.text_input("Breve detalhe (Opcional):")
        
        if st.button("🚨 DISPARAR ALERTA", type="primary"):
            agora = get_br_time()
            # Carrega banco de dados
            if os.path.exists(DB_FILE):
                df = pd.read_csv(DB_FILE)
                nid = df['ID'].max() + 1 if not df.empty else 1
            else:
                df = pd.DataFrame(columns=["ID", "Célula", "Status", "Início", "Data", "Motivo"])
                nid = 1
            
            # Salva o novo registro
            novo_chamado = pd.DataFrame([{
                "ID": nid, "Célula": sel_ups, "Status": "🔴 Aberto", 
                "Início": agora.strftime("%H:%M:%S"), 
                "Data": agora.strftime("%d/%m/%Y"),
                "Motivo": f"{motivo_sel}: {detalhe}"
            }])
            pd.concat([df, novo_chamado]).to_csv(DB_FILE, index=False)
            
            # ENVIA O PUSH QUE VIBRA O CELULAR
            enviar_notificacao_push(
                titulo=f"CHAMADO: {sel_ups}",
                mensagem=f"{motivo_sel} às {agora.strftime('%H:%M')}"
            )
            
            st.success("✅ Alerta enviado!")
            st.rerun()
    else:
        st.markdown(f'<div class="card-alerta">⏳ AGUARDANDO ASSISTENTE<br>{sel_ups}</div>', unsafe_allow_html=True)

# --- ABA ASSISTENTE ---
with tabs[1]:
    st.subheader("Painel de Atendimento")
    if os.path.exists(DB_FILE):
        df_painel = pd.read_csv(DB_FILE)
        ativos = df_painel[df_painel['Status'] == "🔴 Aberto"]
        
        if ativos.empty:
            st.success("✅ Nenhuma pendência na produção.")
        else:
            for _, r in ativos.iterrows():
                with st.container():
                    st.error(f"⚠️ **{r['Célula']}** | Início: {r['Início']}")
                    st.write(f"Descrição: {r['Motivo']}")
                    
                    if st.button(f"✅ FINALIZAR {r['Célula']}", key=f"btn_fin_{r['ID']}"):
                        df_painel.loc[df_painel['ID'] == r['ID'], 'Status'] = "🟢 Finalizado"
                        # Opcional: registrar tempo final
                        df_painel.to_csv(DB_FILE, index=False)
                        st.rerun()

# --- INFO DE CONFIGURAÇÃO ---
st.sidebar.divider()
st.sidebar.write("⚙️ **Configuração do Celular:**")
st.sidebar.info(f"1. Instale o app **ntfy**\n2. Siga o tópico: **{NTFY_TOPIC}**\n3. No app, mude a prioridade para **MÁXIMA**.")
