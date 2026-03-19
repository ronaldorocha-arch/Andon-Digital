import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÃO DINÂMICA ---
DB_FILE = "registro_paradas.csv"

def verificar_chamados_abertos():
    if os.path.exists(DB_FILE):
        try:
            df_temp = pd.read_csv(DB_FILE)
            return not df_temp[df_temp['Status'] == "🔴 Aberto"].empty
        except: return False
    return False

tem_chamado = verificar_chamados_abertos()
st.set_page_config(
    page_title="🚨 CHAMADO! - Andon NHS" if tem_chamado else "Andon Digital - NHS",
    page_icon="🚨",
    layout="wide"
)

st_autorefresh(interval=30000, key="datarefresh")

# --- 2. MEMÓRIA E VARIÁVEIS ---
SENHA_ACESSO = "12345"
LISTA_MOTIVOS = ["Falta de Material", "Qualidade", "Manutenção", "Processo", "Problemas com EP", "Outros"]

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

def get_brasil_time():
    return datetime.utcnow() - timedelta(hours=3)

# --- 3. ESTILOS CSS ---
st.markdown("""
    <style>
    @keyframes piscar { 0% { background-color: #ff4b4b; } 50% { background-color: #7d0000; } 100% { background-color: #ff4b4b; } }
    .piscante { animation: piscar 1s infinite; padding: 20px; border-radius: 10px; color: white; text-align: center; font-weight: bold; margin-bottom: 20px; }
    div.stButton > button:first-child { width: 100%; height: 50px; font-weight: bold; }
    [data-testid="stMetricValue"] { font-size: 38px; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. FUNÇÃO DE DADOS ---
def carregar_dados():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"])
    try:
        df = pd.read_csv(DB_FILE)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce').dt.strftime('%d/%m/%Y')
        df = df.dropna(subset=['Data'])
        if "Minutos" not in df.columns: df["Minutos"] = 0.0
        return df
    except:
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"])

if tem_chamado:
    st.markdown("<audio autoplay><source src='https://raw.githubusercontent.com/rafaelpernil2/beat-detector/master/resources/sounds/bell.mp3' type='audio/mp3'></audio>", unsafe_allow_html=True)

dados = carregar_dados()
hoje = get_brasil_time().strftime("%d/%m/%Y")
ativos = dados[dados['Status'] == "🔴 Aberto"]
# FILTRO PARA RESOLVIDOS DE HOJE
resolvidos_hoje = dados[(dados['Status'] == "🟢 Finalizado") & (dados['Data'] == hoje)]

st.title("🚨 Andon Digital - NHS")
tabs = st.tabs(["📲 Terminal Operador", "💻 Painel Assistente", "📊 Indicadores", "📂 Relatórios"])

# --- ABA 1: OPERADOR ---
with tabs[0]:
    st.subheader("Registrar Nova Parada")
    col1, col2 = st.columns(2)
    ups = ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"]
    sel_ups = col1.selectbox("Célula", ups)
    chamado_aberto = ativos[ativos['Célula'] == sel_ups]
    if chamado_aberto.empty:
        motivo = col2.selectbox("Motivo", LISTA_MOTIVOS)
        desc = st.text_area("Descreva o problema")
        if st.button("🔔 CHAMAR AGORA", type="primary"):
            if desc:
                novo = pd.DataFrame([{"ID": len(dados)+1, "Célula": sel_ups, "Motivo": motivo, "Descrição": desc, "Início": get_brasil_time().strftime("%H:%M:%S"), "Fim": "-", "Status": "🔴 Aberto", "Data": hoje, "Ação": "-", "Minutos": 0.0}])
                pd.concat([dados, novo], ignore_index=True).to_csv(DB_FILE, index=False)
                st.rerun()
    else:
        st.markdown(f'<div class="piscante"><h1>⏳ AGUARDANDO ASSISTENTE...</h1><p>Célula {sel_ups} | Motivo: {chamado_aberto.iloc[0]["Motivo"]}</p><p>Obs: {chamado_aberto.iloc[0]["Descrição"]}</p></div>', unsafe_allow_html=True)

# --- ABA 2: ASSISTENTE (INDICADORES DE HOJE VOLTARAM!) ---
with tabs[1]:
    if not st.session_state.autenticado:
        senha = st.text_input("Senha de Acesso", type="password")
        if st.button("Entrar"):
            if senha == SENHA_ACESSO:
                st.session_state.autenticado = True
                st.rerun()
    else:
        # --- BLOCO DE MÉTRICAS (RESOLVIDO HOJE ESTÁ AQUI) ---
        m1, m2, m3 = st.columns(3)
        m1.metric("🔴 EM ABERTO", len(ativos))
        m2.metric("🟢 RESOLVIDOS HOJE", len(resolvidos_hoje))
        
        # Média de tempo (evita erro se não houver dados)
        media_min = resolvidos_hoje['Minutos'].mean() if not resolvidos_hoje.empty else 0.0
        m3.metric("⏱️ TEMPO MÉDIO", f"{media_min:.1f} min")
        
        st.divider()

        if not ativos.empty:
            st.markdown('<div class="piscante"><h2>⚠️ ATENÇÃO: CHAMADOS PENDENTES!</h2></div>', unsafe_allow_html=True)
            for i, row in ativos.iterrows():
                with st.expander(f"🚨 {row['Célula']} - {row['Motivo']} ({row['Início']})", expanded=True):
                    st.write(f"**Observação:** {row['Descrição']}")
                    acao = st.text_input("Ação Tomada", key=f"re_{row['ID']}")
                    if st.button(f"Finalizar {row['ID']}", key=f"f_{row['ID']}"):
                        if acao:
                            df_f = carregar_dados()
                            idx = df_f[df_f['ID'] == row['ID']].index
                            h_fim = get_brasil_time().strftime("%H:%M:%S")
                            h1 = datetime.strptime(df_f.at[idx[0], 'Início'], "%H:%M:%S")
                            h2 = datetime.strptime(h_fim, "%H:%M:%S")
                            df_f.at[idx[0], 'Fim'] = h_fim
                            df_f.at[idx[0], 'Status'] = "🟢 Finalizado"
                            df_f.at[idx[0], 'Ação'] = acao
                            df_f.at[idx[0], 'Minutos'] = round((h2 - h1).total_seconds() / 60, 1)
                            df_f.to_csv(DB_FILE, index=False)
                            st.rerun()
        else:
            st.success("✅ Nenhum chamado pendente no momento.")

# --- ABA 3: INDICADORES ---
with tabs[2]:
    if st.session_state.autenticado and not dados.empty:
        datas_disp = sorted(list(set(dados['Data'].unique())), reverse=True)
        sel_d = st.multiselect("Datas:", datas_disp, default=[hoje] if hoje in datas_disp else [])
        df_fig = dados[dados['Data'].isin(sel_d)]
        if not df_fig.empty:
            g1, g2 = st.columns(2)
            with g1: st.plotly_chart(px.bar(df_fig['Célula'].value_counts().reset_index(), x='index', y='Célula', title="Paradas por UPS", color_discrete_sequence=['#ff4b4b']), use_container_width=True)
            with g2: st.plotly_chart(px.pie(df_fig, names='Motivo', title="Motivos", hole=0.4), use_container_width=True)

# --- ABA 4: RELATÓRIOS ---
with tabs[3]:
    if st.session_state.autenticado:
        st.dataframe(dados.sort_values(by="ID", ascending=False), use_container_width=True, hide_index=True)
        st.download_button("📥 BAIXAR EXCEL", data=dados.to_csv(index=False).encode('utf-8-sig'), file_name=f'Andon_NHS_{hoje}.csv')
