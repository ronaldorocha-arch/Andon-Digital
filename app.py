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

# --- 3. ESTILO CSS ---
st.markdown("""
    <style>
    @keyframes piscar { 0% { background-color: #ff4b4b; } 50% { background-color: #7d0000; } 100% { background-color: #ff4b4b; } }
    .alerta-piscante { animation: piscar 1s infinite; padding: 20px; border-radius: 10px; color: white !important; text-align: center; margin-bottom: 20px; font-weight: 400 !important; }
    html, body, [class*="css"], p, span, label { font-weight: 400 !important; }
    [data-testid="stMetricValue"] { color: #000000 !important; font-size: 38px; font-weight: 400 !important; }
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

# --- AJUSTE DO SOM (BIP INTERNO) ---
if tem_parada:
    st.markdown("""
        <script>
        var context = new (window.AudioContext || window.webkitAudioContext)();
        var osc = context.createOscillator();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, context.currentTime);
        osc.connect(context.destination);
        osc.start();
        setTimeout(function(){ osc.stop(); }, 500);
        </script>
        """, unsafe_allow_html=True)

dados = carregar_dados()
hoje = get_br_time().strftime("%d/%m/%Y")
ativos = dados[dados['Status'] == "🔴 Aberto"]
resolvidos_hoje = dados[(dados['Status'] == "🟢 Finalizado") & (dados['Data'] == hoje)]

# --- 5. MENU DE NAVEGAÇÃO ---
menu = ["📲 Terminal Operador", "💻 Painel Assistente", "📊 Indicadores", "📂 Relatórios"]
index_salvo = menu.index(st.session_state.pagina_ativa) if st.session_state.pagina_ativa in menu else 0
escolha = st.radio("Selecione o Painel:", menu, horizontal=True, index=index_salvo)
st.session_state.pagina_ativa = escolha
st.divider()

# --- LOGICA DAS PÁGINAS ---

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
        st.markdown(f'<div class="alerta-piscante"><h1>⏳ AGUARDANDO ASSISTENTE...</h1><p>Célula: {sel_ups} | Motivo: {aberto.iloc[0]["Motivo"]}</p><p>Obs: {aberto.iloc[0]["Descrição"]}</p></div>', unsafe_allow_html=True)

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

elif st.session_state.pagina_ativa == "📊 Indicadores":
    if st.session_state.logado:
        st.subheader("🔍 Filtros de Análise")
        if not dados.empty:
            c_f1, c_f2 = st.columns(2)
            d_list = sorted(list(set(dados['Data'].unique())), reverse=True)
            s_d = c_f1.multiselect("Datas:", d_list, default=[hoje] if hoje in d_list else [])
            s_u = c_f2.multiselect("Células:", sorted(dados['Célula'].unique()))
            
            df_i = dados.copy()
            if s_d: df_i = df_i[df_i['Data'].isin(s_d)]
            if s_u: df_i = df_i[df_i['Célula'].isin(s_u)]
            
            if not df_i.empty:
                g1, g2 = st.columns(2)
                with g1: st.plotly_chart(px.bar(df_i['Célula'].value_counts().reset_index(), x='Célula', y='count', title="Por UPS", color_discrete_sequence=['#ff4b4b']), use_container_width=True)
                with g2: st.plotly_chart(px.pie(df_i, names='Motivo', title="Por Motivo", hole=0.4), use_container_width=True)
            else: st.info("Selecione filtros para ver os gráficos.")
    else: st.warning("🔒 Faça login no Painel Assistente.")

elif st.session_state.pagina_ativa == "📂 Relatórios":
    if st.session_state.logado:
        st.dataframe(dados.sort_values(by="ID", ascending=False), use_container_width=True, hide_index=True)
        st.download_button("📥 EXPORTAR CSV", data=dados.to_csv(index=False).encode('utf-8-sig'), file_name=f'Andon_NHS_{hoje}.csv')
