import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÃO DINÂMICA DA ABA (RESOLVE SEU PEDIDO) ---
DB_FILE = "registro_paradas.csv"

def carregar_dados_simples():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["Status"])

df_temp = carregar_dados_simples()
tem_chamado = not df_temp[df_temp['Status'] == "🔴 Aberto"].empty

# Se tiver chamado, o título da aba do navegador vai piscar/mudar
titulo_aba = "🚨 CHAMADO! - Andon NHS" if tem_chamado else "Andon Digital - NHS"

st.set_page_config(page_title=titulo_aba, page_icon="🚨", layout="wide")
st_autorefresh(interval=30000, key="datarefresh")

# --- RESTANTE DO CÓDIGO ---
SENHA_ACESSO = "12345"
LISTA_MOTIVOS = ["Falta de Material", "Qualidade", "Manutenção", "Processo", "Problemas com EP", "Outros"]

if 'logado' not in st.session_state:
    st.session_state.logado = False

def get_brasil_time():
    return datetime.utcnow() - timedelta(hours=3)

# --- SOM DE ALERTA ---
if tem_chamado:
    st.markdown("""
        <audio autoplay>
            <source src="https://raw.githubusercontent.com/rafaelpernil2/beat-detector/master/resources/sounds/bell.mp3" type="audio/mp3">
        </audio>
        """, unsafe_allow_html=True)

# --- CSS PISCANTE NO PAINEL ---
st.markdown("""
    <style>
    @keyframes piscar { 0% { background-color: #ff4b4b; } 50% { background-color: #7d0000; } 100% { background-color: #ff4b4b; } }
    .piscante { animation: piscar 1s infinite; padding: 20px; border-radius: 10px; color: white; text-align: center; font-weight: bold; margin-bottom: 20px; }
    div.stButton > button:first-child { width: 100%; height: 50px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

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

dados_completos = carregar_dados()
hoje_br = get_brasil_time().strftime("%d/%m/%Y")
ativos = dados_completos[dados_completos['Status'] == "🔴 Aberto"]
resolvidos_hoje = dados_completos[(dados_completos['Status'] == "🟢 Finalizado") & (dados_completos['Data'] == hoje_br)]

st.title("🚨 Andon Digital - NHS")
aba_op, aba_as, aba_ind, aba_rel = st.tabs(["📲 Terminal Operador", "💻 Painel Assistente", "📊 Indicadores", "📂 Relatórios"])

# --- ABA 1: OPERADOR ---
with aba_op:
    st.subheader("Registrar Nova Parada")
    col1, col2 = st.columns(2)
    sel_ups = col1.selectbox("Célula", ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"])
    chamado_aberto = ativos[ativos['Célula'] == sel_ups]
    if chamado_aberto.empty:
        motivo = col2.selectbox("Motivo", LISTA_MOTIVOS)
        desc = st.text_area("Descreva o problema")
        if st.button("🔔 CHAMAR AGORA", type="primary"):
            if desc:
                novo = pd.DataFrame([{"ID": len(dados_completos)+1, "Célula": sel_ups, "Motivo": motivo, "Descrição": desc, "Início": get_brasil_time().strftime("%H:%M:%S"), "Fim": "-", "Status": "🔴 Aberto", "Data": hoje_br, "Ação": "-", "Minutos": 0.0}])
                pd.concat([dados_completos, novo], ignore_index=True).to_csv(DB_FILE, index=False)
                st.rerun()
    else:
        st.markdown(f'<div class="piscante"><h1>⏳ AGUARDANDO ASSISTENTE...</h1><p>Célula: {sel_ups}</p></div>', unsafe_allow_html=True)

# --- ABA 2: ASSISTENTE ---
with aba_as:
    if not st.session_state.logado:
        senha_in = st.text_input("Senha do Painel", type="password")
        if st.button("Acessar Painel"):
            if senha_in == SENHA_ACESSO:
                st.session_state.logado = True
                st.rerun()
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("🔴 PARADAS AGORA", len(ativos))
        m2.metric("🟢 RESOLVIDOS HOJE", len(resolvidos_hoje))
        m3.metric("⏱️ MÉDIA (MIN)", f"{resolvidos_hoje['Minutos'].mean():.1f}" if not resolvidos_hoje.empty else "0.0")

        if not ativos.empty:
            st.markdown('<div class="piscante"><h2>⚠️ HÁ CHAMADOS EM ABERTO!</h2></div>', unsafe_allow_html=True)
            for i, row in ativos.iterrows():
                with st.expander(f"🚨 {row['Célula']} ({row['Início']})", expanded=True):
                    st.write(f"Problema: {row['Descrição']}")
                    acao = st.text_input("Ação Tomada", key=f"re_{row['ID']}")
                    if st.button(f"Finalizar {row['ID']}", key=f"f_{row['ID']}"):
                        if acao:
                            df_f = carregar_dados()
                            idx = df_f[df_f['ID'] == row['ID']].index
                            df_f.at[idx[0], 'Status'] = "🟢 Finalizado"
                            df_f.at[idx[0], 'Fim'] = get_brasil_time().strftime("%H:%M:%S")
                            df_f.at[idx[0], 'Ação'] = acao
                            h1 = datetime.strptime(df_f.at[idx[0], 'Início'], "%H:%M:%S")
                            h2 = datetime.strptime(df_f.at[idx[0], 'Fim'], "%H:%M:%S")
                            df_f.at[idx[0], 'Minutos'] = round((h2 - h1).total_seconds() / 60, 1)
                            df_f.to_csv(DB_FILE, index=False)
                            st.rerun()
        
        with st.expander("🗑️ Limpeza de Turno"):
            if st.checkbox("Confirmar limpeza visual?"):
                if st.button("Zerar Hoje"):
                    df_reset = dados_completos[dados_completos['Data'] != hoje_br]
                    df_reset.to_csv(DB_FILE, index=False)
                    st.rerun()

# --- ABA 3 E 4 (INDICADORES E RELATÓRIOS) ---
# [Código permanece igual ao anterior para filtros e download]
with aba_ind:
    if st.session_state.logado and not dados_completos.empty:
        datas = sorted(list(set(dados_completos['Data'].unique())), reverse=True)
        sel_d = st.multiselect("Datas:", datas, default=[hoje_br] if hoje_br in datas else [])
        df_ind = dados_completos[dados_completos['Data'].isin(sel_d)]
        if not df_ind.empty:
            st.plotly_chart(px.bar(df_ind['Célula'].value_counts().reset_index(), x='index', y='Célula', title="UPS Paradas", color_discrete_sequence=['#ff4b4b']), use_container_width=True)

with aba_rel:
    if st.session_state.logado:
        st.subheader("📂 Relatórios")
        st.dataframe(dados_completos.sort_values(by="ID", ascending=False), use_container_width=True, hide_index=True)
        csv = dados_completos.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 BAIXAR EXCEL", data=csv, file_name='Andon_NHS.csv')
