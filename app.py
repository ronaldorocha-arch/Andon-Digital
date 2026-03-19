import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÃO ---
DB_FILE = "registro_paradas.csv"

def checar_ativos_rapido():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            return not df[df['Status'] == "🔴 Aberto"].empty
        except: return False
    return False

tem_parada = checar_ativos_rapido()
st.set_page_config(
    page_title="🚨 CHAMADO! - Andon NHS" if tem_parada else "Andon Digital - NHS",
    page_icon="🚨",
    layout="wide"
)

st_autorefresh(interval=30000, key="datarefresh")

# --- 2. CONTROLE DE NAVEGAÇÃO (ESTRUTURA RÍGIDA) ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

# Se a aba não estiver definida, começa no Operador
if 'pagina_ativa' not in st.session_state:
    st.session_state.pagina_ativa = "📲 Terminal Operador"

SENHA = "12345"

def get_br_time():
    return datetime.utcnow() - timedelta(hours=3)

# --- 3. ESTILO CSS (SEM NEGRITO E NÚMEROS PRETOS) ---
st.markdown("""
    <style>
    @keyframes piscar { 0% { background-color: #ff4b4b; } 50% { background-color: #7d0000; } 100% { background-color: #ff4b4b; } }
    .piscante { animation: piscar 1s infinite; padding: 20px; border-radius: 10px; color: white; text-align: center; margin-bottom: 20px; }
    
    /* REMOVE NEGRITO */
    [data-testid="stMetricValue"] { color: #000000 !important; font-size: 38px; font-weight: 400 !important; }
    [data-testid="stMetricLabel"] p { font-weight: 400 !important; }
    
    div.stButton > button:first-child { width: 100%; height: 50px; font-weight: 400; }
    
    /* Estilo do Menu Superior */
    .stSelectbox label { display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. FUNÇÕES DE DADOS ---
def carregar_dados():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"])
    try:
        df = pd.read_csv(DB_FILE)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce').dt.strftime('%d/%m/%Y')
        df = df.dropna(subset=['Data'])
        return df
    except:
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"])

if tem_parada:
    st.markdown("<audio autoplay><source src='https://raw.githubusercontent.com/rafaelpernil2/beat-detector/master/resources/sounds/bell.mp3' type='audio/mp3'></audio>", unsafe_allow_html=True)

dados = carregar_dados()
hoje = get_br_time().strftime("%d/%m/%Y")
ativos = dados[dados['Status'] == "🔴 Aberto"]
resolvidos_hoje = dados[(dados['Status'] == "🟢 Finalizado") & (dados['Data'] == hoje)]

# --- 5. MENU DE NAVEGAÇÃO (SUBSTITUI AS ABAS) ---
# Usamos um rádio horizontal para simular as abas, mas ele guarda o estado no session_state
menu_opcoes = ["📲 Terminal Operador", "💻 Painel Assistente", "📊 Indicadores", "📂 Relatórios"]
escolha = st.radio("Selecione o Painel:", menu_opcoes, horizontal=True, key="navegacao_manual")

# Atualiza a página ativa na memória
st.session_state.pagina_ativa = escolha

# --- PÁGINA 1: OPERADOR ---
if st.session_state.pagina_ativa == "📲 Terminal Operador":
    st.subheader("Registrar Nova Parada")
    c1, c2 = st.columns(2)
    ups = ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"]
    sel_ups = c1.selectbox("Célula", ups)
    chamado_aberto = ativos[ativos['Célula'] == sel_ups]
    
    if chamado_aberto.empty:
        motivo = c2.selectbox("Motivo", ["Falta de Material", "Qualidade", "Manutenção", "Processo", "Problemas com EP", "Outros"])
        desc = st.text_area("O que aconteceu?")
        if st.button("🔔 CHAMAR AGORA", type="primary"):
            if desc:
                novo_id = dados['ID'].max() + 1 if not dados.empty else 1
                novo = pd.DataFrame([{"ID": int(novo_id), "Célula": sel_ups, "Motivo": motivo, "Descrição": desc, "Início": get_br_time().strftime("%H:%M:%S"), "Fim": "-", "Status": "🔴 Aberto", "Data": hoje, "Ação": "-", "Minutos": 0.0}])
                pd.concat([dados, novo], ignore_index=True).to_csv(DB_FILE, index=False)
                st.rerun()
    else:
        st.markdown(f'<div class="piscante"><h1>⏳ AGUARDANDO ASSISTENTE...</h1><p>Célula: {sel_ups} | Motivo: {chamado_aberto.iloc[0]["Motivo"]}</p><p>Obs: {chamado_aberto.iloc[0]["Descrição"]}</p></div>', unsafe_allow_html=True)

# --- PÁGINA 2: ASSISTENTE ---
elif st.session_state.pagina_ativa == "💻 Painel Assistente":
    if not st.session_state.logado:
        senha_in = st.text_input("Senha de Acesso", type="password")
        if st.button("Entrar"):
            if senha_in == SENHA:
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Senha incorreta")
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("🔴 EM ABERTO", len(ativos))
        m2.metric("🟢 RESOLVIDOS HOJE", len(resolvidos_hoje))
        media = resolvidos_hoje['Minutos'].astype(float).mean() if not resolvidos_hoje.empty else 0.0
        m3.metric("⏱️ TEMPO MÉDIO", f"{media:.1f} min")
        
        st.divider()
        if not ativos.empty:
            st.markdown('<div class="piscante"><h2>⚠️ CHAMADOS PENDENTES!</h2></div>', unsafe_allow_html=True)
            for i, row in ativos.iterrows():
                with st.expander(f"🚨 {row['Célula']} - {row['Motivo']} ({row['Início']})", expanded=True):
                    st.write(f"Observação: {row['Descrição']}")
                    acao = st.text_input("Ação Tomada", key=f"re_{row['ID']}")
                    if st.button(f"Finalizar #{row['ID']}", key=f"f_{row['ID']}"):
                        if acao:
                            df_f = pd.read_csv(DB_FILE)
                            idx = df_f[df_f['ID'] == row['ID']].index
                            h_fim = get_br_time()
                            h_ini = datetime.strptime(df_f.at[idx[0], 'Início'], "%H:%M:%S")
                            df_f.at[idx[0], 'Fim'] = h_fim.strftime("%H:%M:%S")
                            df_f.at[idx[0], 'Status'] = "🟢 Finalizado"
                            df_f.at[idx[0], 'Ação'] = acao
                            df_f.at[idx[0], 'Minutos'] = round((h_fim - datetime.combine(h_fim.date(), h_ini.time())).total_seconds() / 60, 1)
                            df_f.to_csv(DB_FILE, index=False)
                            # Agora o rerun volta para esta MESMA página porque o st.radio está salvo
                            st.rerun()
        else:
            st.success("✅ Tudo em ordem!")

# --- PÁGINA 3: INDICADORES ---
elif st.session_state.pagina_ativa == "📊 Indicadores":
    if st.session_state.logado:
        if not dados.empty:
            datas = sorted(list(set(dados['Data'].unique())), reverse=True)
            sel_d = st.multiselect("Filtrar Datas:", datas, default=[hoje] if hoje in datas else [])
            df_fig = dados[dados['Data'].isin(sel_d)]
            if not df_fig.empty:
                g1, g2 = st.columns(2)
                with g1:
                    st.plotly_chart(px.bar(df_fig['Célula'].value_counts().reset_index(), x='Célula', y='count', title="Paradas por UPS", color_discrete_sequence=['#ff4b4b']), use_container_width=True)
                with g2:
                    st.plotly_chart(px.pie(df_fig, names='Motivo', title="Motivos", hole=0.4), use_container_width=True)
    else:
        st.warning("🔒 Faça login no Painel Assistente.")

# --- PÁGINA 4: RELATÓRIOS ---
elif st.session_state.pagina_ativa == "📂 Relatórios":
    if st.session_state.logado:
        st.dataframe(dados.sort_values(by="ID", ascending=False), use_container_width=True, hide_index=True)
        st.download_button("📥 BAIXAR EXCEL", data=dados.to_csv(index=False).encode('utf-8-sig'), file_name=f'Andon_NHS_{hoje}.csv')
        with st.expander("ADMIN"):
            if st.button("LIMPAR TODO O HISTÓRICO"):
                if os.path.exists(DB_FILE): os.remove(DB_FILE)
                st.rerun()
    else:
        st.warning("🔒 Faça login no Painel Assistente.")
