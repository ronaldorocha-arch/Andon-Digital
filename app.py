import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÃO DINÂMICA DA PÁGINA ---
DB_FILE = "registro_paradas.csv"

def checar_chamados_ativos():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            if df.empty: return False
            return not df[df['Status'] == "🔴 Aberto"].empty
        except: return False
    return False

# Título da aba muda se houver chamado aberto (Notificação no Browser)
tem_parada = checar_chamados_ativos()
st.set_page_config(
    page_title="🚨 CHAMADO! - Andon NHS" if tem_parada else "Andon Digital - NHS",
    page_icon="🚨",
    layout="wide"
)

# Atualiza a página automaticamente a cada 30 segundos
st_autorefresh(interval=30000, key="datarefresh")

# --- 2. VARIÁVEIS E MEMÓRIA DE SESSÃO ---
SENHA_ACESSO = "12345"
LISTA_MOTIVOS = ["Falta de Material", "Qualidade", "Manutenção", "Processo", "Problemas com EP", "Outros"]

# Inicializa o login para não pedir senha a todo momento
if 'logado' not in st.session_state:
    st.session_state.logado = False

# Função para garantir o horário de Brasília (-3h)
def get_brasil_time():
    return datetime.utcnow() - timedelta(hours=3)

# --- 3. ESTILOS CSS (PISCANTE E BOTÕES) ---
st.markdown("""
    <style>
    @keyframes piscar { 0% { background-color: #ff4b4b; } 50% { background-color: #7d0000; } 100% { background-color: #ff4b4b; } }
    .piscante { animation: piscar 1s infinite; padding: 20px; border-radius: 10px; color: white; text-align: center; font-weight: bold; margin-bottom: 20px; }
    div.stButton > button:first-child { width: 100%; height: 50px; font-weight: bold; }
    [data-testid="stMetricValue"] { font-size: 38px; color: #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. FUNÇÕES DE DADOS ---
def carregar_dados():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"])
    try:
        df = pd.read_csv(DB_FILE)
        # Força o formato de data brasileiro para evitar erros de gráfico
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce').dt.strftime('%d/%m/%Y')
        df = df.dropna(subset=['Data'])
        if "Minutos" not in df.columns: df["Minutos"] = 0.0
        return df
    except:
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"])

# --- 5. ALERTA SONORO ---
if tem_parada:
    st.markdown("""
        <audio autoplay>
            <source src="https://raw.githubusercontent.com/rafaelpernil2/beat-detector/master/resources/sounds/bell.mp3" type="audio/mp3">
        </audio>
        """, unsafe_allow_html=True)

# Processamento inicial dos dados
dados = carregar_dados()
agora_br = get_brasil_time()
hoje = agora_br.strftime("%d/%m/%Y")

ativos = dados[dados['Status'] == "🔴 Aberto"]
# Filtro automático: Só mostra como "Resolvido Hoje" o que for da data atual
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
        desc = st.text_area("Descreva o problema (Observação)")
        if st.button("🔔 CHAMAR AGORA", type="primary"):
            if desc:
                novo_id = dados['ID'].max() + 1 if not dados.empty else 1
                novo = pd.DataFrame([{"ID": int(novo_id), "Célula": sel_ups, "Motivo": motivo, "Descrição": desc, "Início": agora_br.strftime("%H:%M:%S"), "Fim": "-", "Status": "🔴 Aberto", "Data": hoje, "Ação": "-", "Minutos": 0.0}])
                pd.concat([dados, novo], ignore_index=True).to_csv(DB_FILE, index=False)
                st.rerun()
    else:
        st.markdown(f"""
            <div class="piscante">
                <h1>⏳ AGUARDANDO ASSISTENTE...</h1>
                <p style="font-size:22px;">Célula: <b>{sel_ups}</b> | Motivo: <b>{chamado_aberto.iloc[0]['Motivo']}</b></p>
                <p style="font-size:18px;">Sua Obs: <i>"{chamado_aberto.iloc[0]['Descrição']}"</i></p>
            </div>
        """, unsafe_allow_html=True)

# --- ABA 2: ASSISTENTE (COM MÉTRICAS DIÁRIAS) ---
with tabs[1]:
    if not st.session_state.logado:
        senha = st.text_input("Senha de Acesso", type="password", key="login_as")
        if st.button("Acessar Painel"):
            if senha == SENHA_ACESSO:
                st.session_state.logado = True
                st.rerun()
    else:
        # Métricas que zeram automaticamente à meia-noite
        m1, m2, m3 = st.columns(3)
        m1.metric("🔴 EM ABERTO", len(ativos))
        m2.metric("🟢 RESOLVIDOS HOJE", len(resolvidos_hoje))
        media_min = resolvidos_hoje['Minutos'].mean() if not resolvidos_hoje.empty else 0.0
        m3.metric("⏱️ TEMPO MÉDIO (HOJE)", f"{media_min:.1f} min")
        
        st.divider()

        if not ativos.empty:
            st.markdown('<div class="piscante"><h2>⚠️ CHAMADOS PENDENTES!</h2></div>', unsafe_allow_html=True)
            for i, row in ativos.iterrows():
                with st.expander(f"🚨 {row['Célula']} - {row['Motivo']} ({row['Início']})", expanded=True):
                    st.write(f"**Relato do Operador:** {row['Descrição']}")
                    acao = st.text_input("Ação Tomada", key=f"re_{row['ID']}")
                    if st.button(f"Finalizar Chamado #{row['ID']}", key=f"f_{row['ID']}"):
                        if acao:
                            df_f = carregar_dados()
                            idx = df_f[df_f['ID'] == row['ID']].index
                            h_fim_dt = get_brasil_time()
                            h_fim_str = h_fim_dt.strftime("%H:%M:%S")
                            h_ini_dt = datetime.strptime(df_f.at[idx[0], 'Início'], "%H:%M:%S")
                            
                            df_f.at[idx[0], 'Fim'] = h_fim_str
                            df_f.at[idx[0], 'Status'] = "🟢 Finalizado"
                            df_f.at[idx[0], 'Ação'] = acao
                            df_f.at[idx[0], 'Minutos'] = round((datetime.combine(agora_br.date(), h_fim_dt.time()) - datetime.combine(agora_br.date(), h_ini_dt.time())).total_seconds() / 60, 1)
                            df_f.to_csv(DB_FILE, index=False)
                            st.rerun()
        else:
            st.success("✅ Todas as células estão operando normalmente.")

# --- ABA 3: INDICADORES (GRÁFICOS) ---
with tabs[2]:
    if st.session_state.logado:
        if not dados.empty:
            st.subheader("🔍 Filtros de Análise")
            f1, f2 = st.columns(2)
            datas_disp = sorted(list(set(dados['Data'].unique())), reverse=True)
            sel_d = f1.multiselect("Datas:", datas_disp, default=[hoje] if hoje in datas_disp else [])
            sel_u = f2.multiselect("Células:", sorted(dados['Célula'].unique()))

            df_fig = dados.copy()
            if sel_d: df_fig = df_fig[df_fig['Data'].isin(sel_d)]
            if sel_u: df_fig = df_fig[df_fig['Célula'].isin(sel_u)]

            if not df_fig.empty:
                st.divider()
                g1, g2 = st.columns(2)
                with g1:
                    cont = df_fig['Célula'].value_counts().reset_index()
                    cont.columns = ['Célula', 'Qtd']
                    st.plotly_chart(px.bar(cont, x='Célula', y='Qtd', title="Volume por UPS", color_discrete_sequence=['#ff4b4b']), use_container_width=True)
                with g2:
                    st.plotly_chart(px.pie(df_fig, names='Motivo', title="Motivos das Paradas", hole=0.4), use_container_width=True)
            else:
                st.info("ℹ️ Selecione filtros para gerar os gráficos.")
        else:
            st.warning("📭 Banco de dados vazio.")

# --- ABA 4: RELATÓRIOS E DOWNLOAD ---
with tabs[3]:
    if st.session_state.logado:
        st.subheader("📂 Histórico Geral e Exportação")
        if not dados.empty:
            st.dataframe(dados.sort_values(by="ID", ascending=False), use_container_width=True, hide_index=True)
            csv_export = dados.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 BAIXAR EXCEL COMPLETO", data=csv_export, file_name=f'Andon_NHS_Backup_{hoje}.csv', mime='text/csv')
        
        with st.expander("🛠️ ZERAR DADOS (ADMIN)"):
            if st.button("LIMPAR TODO O HISTÓRICO PERMANENTEMENTE"):
                if os.path.exists(DB_FILE): os.remove(DB_FILE)
                st.rerun()
