import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÃO ---
DB_FILE = "registro_paradas.csv"
st.set_page_config(page_title="Andon NHS", page_icon="🚨", layout="centered")

# Atualiza a tela a cada 5 segundos para checar novos chamados
st_autorefresh(interval=5000, key="andon_refresh")

def get_br_time():
    return datetime.utcnow() - timedelta(hours=3)

def checar_chamados_ativos():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            return not df[df['Status'] == "🔴 Aberto"].empty
        except: return False
    return False

tem_chamado = checar_chamados_ativos()

# --- 2. ESTILO VISUAL (APP MOBILE) ---
st.markdown("""
    <style>
    /* Esconder elementos desnecessários do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Botões Grandes para Polegar */
    div.stButton > button {
        width: 100%;
        height: 70px !important;
        font-size: 18px !important;
        font-weight: bold !important;
        border-radius: 12px !important;
        margin-bottom: 15px;
    }
    
    /* Alerta de Chamado */
    @keyframes alerta { 0% {background-color: #ff0000;} 50% {background-color: #660000;} 100% {background-color: #ff0000;} }
    .card-chamado {
        animation: alerta 0.8s infinite;
        color: white;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SISTEMA DE ÁUDIO (SIRENE) ---
if tem_chamado:
    # Este código injeta um áudio de sirene que toca em loop
    st.markdown("""
        <audio autoplay loop id="sirene">
            <source src="https://www.soundjay.com/buttons/beep-01a.mp3" type="audio/mpeg">
        </audio>
        <script>
            var audio = document.getElementById('sirene');
            audio.volume = 1.0;
            audio.play();
        </script>
        """, unsafe_allow_html=True)

# --- 4. INTERFACE ---

st.title("🚨 Andon Digital NHS")

# Botão obrigatório para habilitar áudio no navegador
if "audio_permitido" not in st.session_state:
    if st.button("🔊 ATIVAR ALERTA SONORO (CLIQUE AQUI)"):
        st.session_state.audio_permitido = True
        st.success("Som habilitado!")
        st.rerun()

tabs = st.tabs(["📲 Operador", "💻 Assistente"])

# --- ABA OPERADOR ---
with tabs[0]:
    st.subheader("Registrar Parada")
    ups = ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"]
    sel_ups = st.selectbox("Célula:", ups)
    
    # Verifica se já tem chamado aberto para essa célula
    if os.path.exists(DB_FILE):
        df_verificar = pd.read_csv(DB_FILE)
        ja_aberto = not df_verificar[(df_verificar['Célula'] == sel_ups) & (df_verificar['Status'] == "🔴 Aberto")].empty
    else:
        ja_aberto = False

    if not ja_aberto:
        motivos = ["Material", "Qualidade", "Processo", "Manutenção", "Outros"]
        motivo = st.radio("Motivo:", motivos, horizontal=True)
        obs = st.text_input("Detalhes:")
        
        if st.button("🚨 ENVIAR CHAMADO", type="primary"):
            agora = get_br_time()
            if os.path.exists(DB_FILE):
                df = pd.read_csv(DB_FILE)
                nid = df['ID'].max() + 1
            else:
                df = pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Minutos"])
                nid = 1
            
            novo = pd.DataFrame([{"ID": nid, "Célula": sel_ups, "Motivo": motivo, "Descrição": f"{motivo}: {obs}", "Início": agora.strftime("%H:%M:%S"), "Fim": "-", "Status": "🔴 Aberto", "Data": agora.strftime("%d/%m/%Y"), "Minutos": 0}])
            pd.concat([df, novo]).to_csv(DB_FILE, index=False)
            st.rerun()
    else:
        st.markdown(f'<div class="card-chamado"><h2>⏳ AGUARDANDO APOIO</h2><p>{sel_ups}</p></div>', unsafe_allow_html=True)

# --- ABA ASSISTENTE ---
with tabs[1]:
    st.subheader("Chamados Ativos")
    if os.path.exists(DB_FILE):
        df_painel = pd.read_csv(DB_FILE)
        abertos = df_painel[df_painel['Status'] == "🔴 Aberto"]
        
        if abertos.empty:
            st.success("✅ Nenhuma parada no momento.")
        else:
            for _, r in abertos.iterrows():
                with st.container():
                    st.error(f"**{r['Célula']}** | Início: {r['Início']}")
                    st.write(f"Problema: {r['Descrição']}")
                    if st.button(f"✅ FINALIZAR {r['Célula']}", key=f"fin_{r['ID']}"):
                        ag = get_br_time()
                        df_painel.loc[df_painel['ID'] == r['ID'], 'Status'] = "🟢 Finalizado"
                        df_painel.loc[df_painel['ID'] == r['ID'], 'Fim'] = ag.strftime("%H:%M:%S")
                        # Cálculo de minutos
                        h_ini = datetime.strptime(r['Início'], "%H:%M:%S")
                        duracao = (ag - datetime.combine(ag.date(), h_ini.time())).total_seconds() / 60
                        df_painel.loc[df_painel['ID'] == r['ID'], 'Minutos'] = round(duracao, 1)
                        df_painel.to_csv(DB_FILE, index=False)
                        st.rerun()
