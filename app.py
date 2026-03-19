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

# Atualiza a cada 5 segundos
st_autorefresh(interval=5000, key="datarefresh")

if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'pagina_ativa' not in st.session_state:
    st.session_state.pagina_ativa = "📲 Terminal Operador"

SENHA = "12345"

def get_br_time():
    return datetime.utcnow() - timedelta(hours=3)

# --- 2. ESTILO CSS ---
st.markdown("""
    <style>
    @keyframes piscar { 0% { background-color: #ff4b4b; } 50% { background-color: #7d0000; } 100% { background-color: #ff4b4b; } }
    .alerta-piscante { animation: piscar 1s infinite; padding: 20px; border-radius: 10px; color: white !important; text-align: center; margin-bottom: 20px; font-weight: 400 !important; }
    html, body, [class*="css"], p, span, label { font-weight: 400 !important; }
    [data-testid="stMetricValue"] { color: #000000 !important; font-size: 38px; font-weight: 400 !important; }
    div.stButton > button:first-child { width: 100%; height: 50px; font-weight: 400 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNÇÕES DE DADOS ---
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

# --- 4. LÓGICA DO SOM (NOVO LINK E TESTE) ---
if tem_parada:
    # Som de campainha de balcão (curto e nítido)
    url_som = "https://www.soundjay.com/buttons/sounds/button-3.mp3"
    st.markdown(f"""
        <audio autoplay>
            <source src="{url_som}" type="audio/mp3">
        </audio>
        """, unsafe_allow_html=True)

dados = carregar_dados()
hoje = get_br_time().strftime("%d/%m/%Y")
ativos = dados[dados['Status'] == "🔴 Aberto"]
resolvidos_hoje = dados[(dados['Status'] == "🟢 Finalizado") & (dados['Data'] == hoje)]

# --- 5. MENU ---
menu = ["📲 Terminal Operador", "💻 Painel Assistente", "📊 Indicadores", "📂 Relatórios"]
escolha = st.radio("Selecione o Painel:", menu, horizontal=True, index=menu.index(st.session_state.pagina_ativa))
st.session_state.pagina_ativa = escolha
st.divider()

# --- PÁGINA OPERADOR ---
if st.session_state.pagina_ativa == "📲 Terminal Operador":
    st.subheader("Registrar Nova Parada")
    c1, c2 = st.columns(2)
    ups = ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"]
    sel_ups = c1.selectbox("Célula", ups)
    aberto = ativos[ativos['Célula'] == sel_ups]
    if aberto.empty:
        motivo = c2.selectbox("Motivo", ["Falta de Material", "Qualidade", "Manutenção", "Processo", "Problemas com EP", "Outros"])
        desc = st.text_area("O que aconteceu?")
        if st.button("🔔 CHAMAR AGORA", type="primary"):
            if desc:
                nid = dados['ID'].max() + 1 if not dados.empty else 1
                novo = pd.DataFrame([{"ID": int(nid), "Célula": sel_ups, "Motivo": motivo, "Descrição": desc, "Início": get_br_time().strftime("%H:%M:%S"), "Fim": "-", "Status": "🔴 Aberto", "Data": hoje, "Ação": "-", "Minutos": 0.0}])
                pd.concat([dados, novo], ignore_index=True).to_csv(DB_FILE, index=False)
                st.rerun()
    else:
        st.markdown(f'<div class="alerta-piscante"><h1>⏳ AGUARDANDO ASSISTENTE...</h1><p>Célula: {sel_ups}</p></div>', unsafe_allow_html=True)

# --- PÁGINA ASSISTENTE ---
elif st.session_state.pagina_ativa == "💻 Painel Assistente":
    if not st.session_state.logado:
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if senha == SENHA: st.session_state.logado = True; st.rerun()
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("EM ABERTO", len(ativos))
        m2.metric("RESOLVIDOS HOJE", len(resolvidos_hoje))
        med = resolvidos_hoje['Minutos'].astype(float).mean() if not resolvidos_hoje.empty else 0.0
        m3.metric("TEMPO MÉDIO", f"{med:.1f} min")
        st.divider()
        if not ativos.empty:
            # BOTÃO DE SEGURANÇA PARA "ACORDAR" O ÁUDIO
            st.button("📢 CLIQUE AQUI PARA OUVIR O ALERTA (Se estiver mudo)")
            st.markdown('<div class="alerta-piscante">⚠️ ATENÇÃO: HÁ CHAMADOS PENDENTES!</div>', unsafe_allow_html=True)
            for i, r in ativos.iterrows():
                with st.expander(f"Chamado: {r['Célula']} - {r['Motivo']}", expanded=True):
                    st.write(f"Relato: {r['Descrição']}")
                    ac = st.text_input("Ação Tomada", key=f"ac_{r['ID']}")
                    if st.button(f"Finalizar #{r['ID']}", key=f"f_{r['ID']}"):
                        if ac:
                            df_f = pd.read_csv(DB_FILE)
                            idx = df_f[df_f['ID'] == r['ID']].index
                            ag = get_br_time()
                            h_ini = datetime.strptime(df_f.at[idx[0], 'Início'], "%H:%M:%S")
                            df_f.at[idx[0], 'Fim'] = ag.strftime("%H:%M:%S")
                            df_f.at[idx[0], 'Status'] = "🟢 Finalizado"; df_f.at[idx[0], 'Ação'] = ac
                            df_f.at[idx[0], 'Minutos'] = round((ag - datetime.combine(ag.date(), h_ini.time())).total_seconds() / 60, 1)
                            df_f.to_csv(DB_FILE, index=False); st.rerun()
        else: st.success("✅ Tudo em ordem!")

# --- INDICADORES ---
elif st.session_state.pagina_ativa == "📊 Indicadores":
    if st.session_state.logado:
        st.subheader("🔍 Filtros de Análise")
        d_list = sorted(list(set(dados['Data'].unique())), reverse=True)
        s_d = st.multiselect("Datas:", d_list, default=[hoje] if hoje in d_list else [])
        df_i = dados[dados['Data'].isin(s_d)] if s_d else dados
        if not df_i.empty:
            st.plotly_chart(px.bar(df_i['Célula'].value_counts().reset_index(), x='Célula', y='count', title="Por UPS"), use_container_width=True)

# --- RELATÓRIOS ---
elif st.session_state.pagina_ativa == "📂 Relatórios":
    if st.session_state.logado:
        st.dataframe(dados.sort_values(by="ID", ascending=False), use_container_width=True, hide_index=True)
        st.download_button("📥 EXPORTAR CSV", data=dados.to_csv(index=False).encode('utf-8-sig'), file_name=f'Andon_NHS_{hoje}.csv')
