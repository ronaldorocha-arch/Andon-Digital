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

# Atualiza a cada 5 segundos para resposta rápida
st_autorefresh(interval=5000, key="datarefresh")

# --- 2. CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'pagina_ativa' not in st.session_state:
    st.session_state.pagina_ativa = "📲 Terminal Operador"

SENHA = "12345"

def get_br_time():
    return datetime.utcnow() - timedelta(hours=3)

# --- 3. ESTILO CSS (PISCANTE REFORÇADO E SEM NEGRITO) ---
st.markdown("""
    <style>
    @keyframes piscar { 
        0% { background-color: #ff4b4b; opacity: 1; } 
        50% { background-color: #7d0000; opacity: 0.8; } 
        100% { background-color: #ff4b4b; opacity: 1; } 
    }
    .alerta-piscante { 
        animation: piscar 1s infinite; 
        padding: 25px; 
        border-radius: 15px; 
        color: white !important; 
        text-align: center; 
        margin-bottom: 25px; 
        font-size: 24px;
        font-weight: 400 !important;
    }
    
    /* REMOVE NEGRITO DE TUDO */
    html, body, [class*="css"], p, span, label { font-weight: 400 !important; }
    
    /* NÚMEROS PRETOS */
    [data-testid="stMetricValue"] { color: #000000 !important; font-size: 38px; font-weight: 400 !important; }
    
    /* BOTÕES */
    div.stButton > button:first-child { width: 100%; height: 50px; font-weight: 400 !important; }
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

# --- 5. MENU DE NAVEGAÇÃO ---
menu = ["📲 Terminal Operador", "💻 Painel Assistente", "📊 Indicadores", "📂 Relatórios"]
escolha = st.radio("Selecione o Painel:", menu, horizontal=True, index=menu.index(st.session_state.pagina_ativa))
st.session_state.pagina_ativa = escolha
st.divider()

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
        st.markdown(f'<div class="alerta-piscante"><h1>⏳ AGUARDANDO ASSISTENTE...</h1><p>Célula: {sel_ups} | Motivo: {chamado_aberto.iloc[0]["Motivo"]}</p><p>Obs: {chamado_aberto.iloc[0]["Descrição"]}</p></div>', unsafe_allow_html=True)

# --- PÁGINA 2: ASSISTENTE ---
elif st.session_state.pagina_ativa == "💻 Painel Assistente":
    if not st.session_state.logado:
        senha_c = st.text_input("Senha de Acesso", type="password")
        if st.button("Entrar"):
            if senha_c == SENHA:
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Senha incorreta")
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("EM ABERTO", len(ativos))
        m2.metric("RESOLVIDOS HOJE", len(resolvidos_hoje))
        media = resolvidos_hoje['Minutos'].astype(float).mean() if not resolvidos_hoje.empty else 0.0
        m3.metric("TEMPO MÉDIO", f"{media:.1f} min")
        
        st.divider()
        if not ativos.empty:
            # ALERTA PISCANTE NA ASSISTENTE VOLTOU!
            st.markdown('<div class="alerta-piscante">⚠️ ATENÇÃO: HÁ CHAMADOS PENDENTES!</div>', unsafe_allow_html=True)
            for i, row in ativos.iterrows():
                with st.expander(f"Chamado: {row['Célula']} - {row['Motivo']}", expanded=True):
                    st.write(f"Relato: {row['Descrição']}")
                    acao = st.text_input("Ação Tomada", key=f"re_{row['ID']}")
                    if st.button(f"Finalizar #{row['ID']}", key=f"f_{row['ID']}"):
                        if acao:
                            df_f = pd.read_csv(DB_FILE)
                            idx = df_f[df_f['ID'] == row['ID']].index
                            agora = get_br_time()
                            h_ini = datetime.strptime(df_f.at[idx[0], 'Início'], "%H:%M:%S")
                            df_f.at[idx[0], 'Fim'] = agora.strftime("%H:%M:%S")
                            df_f.at[idx[0], 'Status'] = "🟢 Finalizado"
                            df_f.at[idx[0], 'Ação'] = acao
                            df_f.at[idx[0], 'Minutos'] = round((agora - datetime.combine(agora.date(), h_ini.time())).total_seconds() / 60, 1)
                            df_f.to_csv(DB_FILE, index=False)
                            st.rerun()
        else:
            st.success("✅ Tudo em ordem!")

# --- PÁGINAS DE INDICADORES E RELATÓRIOS (PERMANECEM IGUAIS) ---
elif st.session_state.pagina_ativa == "📊 Indicadores":
    if st.session_state.logado:
        if not dados.empty:
            sel_d = st.multiselect("Datas:", sorted(dados['Data'].unique(), reverse=True), default=[hoje] if hoje in dados['Data'].values else [])
            df_fig = dados[dados['Data'].isin(sel_d)]
            if not df_fig.empty:
                g1, g2 = st.columns(2)
                with g1: st.plotly_chart(px.bar(df_fig['Célula'].value_counts().reset_index(), x='Célula', y='count', title="Paradas por UPS", color_discrete_sequence=['#ff4b4b']), use_container_width=True)
                with g2: st.plotly_chart(px.pie(df_fig, names='Motivo', title="Distribuição", hole=0.4), use_container_width=True)
    else: st.warning("🔒 Faça login no Painel Assistente.")

elif st.session_state.pagina_ativa == "📂 Relatórios":
    if st.session_state.logado:
        st.dataframe(dados.sort_values(by="ID", ascending=False), use_container_width=True, hide_index=True)
        st.download_button("📥 EXPORTAR CSV", data=dados.to_csv(index=False).encode('utf-8-sig'), file_name=f'Andon_NHS_{hoje}.csv')
