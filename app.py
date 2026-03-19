import streamlit as st
import pandas as pd
from datetime import datetime
import os
import plotly.express as px

st.set_page_config(page_title="Andon Digital - NHS", page_icon="🚨", layout="wide")

DB_FILE = "registro_paradas.csv"

# Senha para limpar dados (Altere aqui se desejar)
SENHA_ADMIN = "1234"

if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data"])
    df_init.to_csv(DB_FILE, index=False)

def carregar_dados():
    try:
        df = pd.read_csv(DB_FILE)
        # Garante que a coluna Data existe para os filtros funcionarem
        if "Data" not in df.columns:
            df["Data"] = datetime.now().strftime("%Y-%m-%d")
        return df
    except:
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data"])

def salvar_chamado(celula, motivo, desc):
    df = carregar_dados()
    novo_id = len(df) + 1
    agora = datetime.now()
    novo_registro = {
        "ID": novo_id, "Célula": celula, "Motivo": motivo, "Descrição": desc,
        "Início": agora.strftime("%H:%M:%S"),
        "Fim": "-", "Status": "🔴 Aberto",
        "Data": agora.strftime("%Y-%m-%d")
    }
    df = pd.concat([df, pd.DataFrame([novo_registro])], ignore_index=True)
    df.to_csv(DB_FILE, index=False)

def finalizar_chamado(id_chamado):
    df = carregar_dados()
    idx = df[df['ID'] == id_chamado].index
    if not idx.empty:
        df.at[idx[0], 'Fim'] = datetime.now().strftime("%H:%M:%S")
        df.at[idx[0], 'Status'] = "🟢 Finalizado"
        df.to_csv(DB_FILE, index=False)

# --- INTERFACE ---
st.title("🚨 Sistema Andon - Tecnologia de Processos")
aba_op, aba_as, aba_ind = st.tabs(["📲 Terminal do Operador", "💻 Painel da Assistente", "📊 Indicadores"])

dados_completos = carregar_dados()

# --- ABA 1: OPERADOR ---
with aba_op:
    st.subheader("Registrar Nova Parada")
    col1, col2 = st.columns(2)
    with col1:
        sel_ups = st.selectbox("Sua Célula", ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"])
    with col2:
        sel_motivo = st.selectbox("Motivo", ["Falta de Material", "Qualidade", "Manutenção", "Processo", "Outros"])
    
    desc = st.text_area("O que aconteceu?", key="desc_op")
    if st.button("🔔 CHAMAR ASSISTENTE", type="primary"):
        if desc:
            salvar_chamado(sel_ups, sel_motivo, desc)
            st.success("Chamado enviado!")
            st.rerun()

    ativos = dados_completos[dados_completos['Status'] == "🔴 Aberto"]
    if not ativos.empty:
        st.divider()
        st.subheader("⚠️ Chamados Pendentes")
        st.table(ativos[['Célula', 'Motivo', 'Início']])

# --- ABA 2: ASSISTENTE ---
with aba_as:
    st.subheader("Atendimentos em Aberto")
    ativos_as = dados_completos[dados_completos['Status'] == "🔴 Aberto"]
    if ativos_as.empty:
        st.info("✅ Tudo em ordem.")
    else:
        for i, row in ativos_as.iterrows():
            with st.expander(f"🔴 {row['Célula']} - {row['Motivo']}", expanded=True):
                st.write(f"**Detalhe:** {row['Descrição']}")
                if st.button(f"✅ Finalizar ID {row['ID']}", key=f"as_{row['ID']}"):
                    finalizar_chamado(row['ID'])
                    st.rerun()
    st.divider()
    st.subheader("Histórico Geral")
    st.dataframe(dados_completos, use_container_width=True, hide_index=True)

# --- ABA 3: INDICADORES COM FILTRO ---
with aba_ind:
    st.subheader("Análise de Performance")
    
    if dados_completos.empty:
        st.warning("Sem dados.")
    else:
        # Filtro de Data
        datas_disponiveis = sorted(dados_completos['Data'].unique(), reverse=True)
        data_sel = st.multiselect("Filtrar por Data (Deixe vazio para ver TUDO)", datas_disponiveis, default=[datetime.now().strftime("%Y-%m-%d")])
        
        df_filtrado = dados_completos[dados_completos['Data'].isin(data_sel)] if data_sel else dados_completos

        if df_filtrado.empty:
            st.info("Nenhum chamado nesta data.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                fig_ups = px.bar(df_filtrado, x='Célula', title='Chamados por Célula', color_discrete_sequence=['#ff4b4b'])
                st.plotly_chart(fig_ups, use_container_width=True)
            with c2:
                fig_mot = px.pie(df_filtrado, names='Motivo', title='Motivos de Parada', hole=0.4)
                st.plotly_chart(fig_mot, use_container_width=True)

        # --- FUNÇÃO PARA LIMPAR TUDO ---
        st.divider()
        with st.expander("⚙️ Configurações Avançadas"):
            st.warning("Atenção: Limpar o histórico apagará todos os registros permanentemente.")
            senha = st.text_input("Digite a senha para resetar o banco de dados", type="password")
            if st.button("🗑️ APAGAR TODO O HISTÓRICO"):
                if senha == SENHA_ADMIN:
                    df_reset = pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data"])
                    df_reset.to_csv(DB_FILE, index=False)
                    st.success("Histórico apagado com sucesso!")
                    st.rerun()
                else:
                    st.error("Senha incorreta!")

st.markdown("""<style>div.stButton > button:first-child { width: 100%; height: 60px; font-size: 20px; }</style>""", unsafe_allow_html=True)
