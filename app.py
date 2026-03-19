import streamlit as st
import pandas as pd
from datetime import datetime
import os
import plotly.express as px # Biblioteca para os gráficos

# Configuração da Página
st.set_page_config(page_title="Andon Digital - NHS", page_icon="🚨", layout="wide")

DB_FILE = "registro_paradas.csv"

if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status"])
    df_init.to_csv(DB_FILE, index=False)

def carregar_dados():
    try:
        return pd.read_csv(DB_FILE)
    except:
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status"])

def salvar_chamado(celula, motivo, desc):
    df = carregar_dados()
    novo_id = len(df) + 1
    novo_registro = {
        "ID": novo_id, "Célula": celula, "Motivo": motivo, "Descrição": desc,
        "Início": datetime.now().strftime("%d/%m %H:%M:%S"),
        "Fim": "-", "Status": "🔴 Aberto"
    }
    df = pd.concat([df, pd.DataFrame([novo_registro])], ignore_index=True)
    df.to_csv(DB_FILE, index=False)

def finalizar_chamado(id_chamado):
    df = carregar_dados()
    idx = df[df['ID'] == id_chamado].index
    if not idx.empty:
        df.at[idx[0], 'Fim'] = datetime.now().strftime("%d/%m %H:%M:%S")
        df.at[idx[0], 'Status'] = "🟢 Finalizado"
        df.to_csv(DB_FILE, index=False)

# --- INTERFACE ---
st.title("🚨 Sistema Andon - Tecnologia de Processos")

aba_op, aba_as, aba_ind = st.tabs(["📲 Terminal do Operador", "💻 Painel da Assistente", "📊 Indicadores"])

dados = carregar_dados()
ativos = dados[dados['Status'] == "🔴 Aberto"]

# --- ABA 1: OPERADOR ---
with aba_op:
    st.subheader("Registrar Nova Parada")
    col1, col2 = st.columns(2)
    with col1:
        sel_ups = st.selectbox("Sua Célula", ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"])
    with col2:
        sel_motivo = st.selectbox("Motivo", ["Falta de Material", "Qualidade", "Manutenção", "Processo", "Outros"])
    
    desc = st.text_area("O que aconteceu?", placeholder="Ex: Falta de componente X")
    if st.button("🔔 CHAMAR ASSISTENTE", type="primary"):
        if desc:
            salvar_chamado(sel_ups, sel_motivo, desc)
            st.success("Chamado enviado!")
            st.rerun()

    if not ativos.empty:
        st.divider()
        st.subheader("⚠️ Chamados Pendentes")
        st.table(ativos[['Célula', 'Motivo', 'Início']])

# --- ABA 2: ASSISTENTE ---
with aba_as:
    st.subheader("Atendimentos em Aberto")
    if ativos.empty:
        st.info("✅ Tudo em ordem.")
    else:
        for i, row in ativos.iterrows():
            with st.expander(f"🔴 {row['Célula']} - {row['Motivo']}", expanded=True):
                st.write(f"**Detalhe:** {row['Descrição']}")
                if st.button(f"✅ Finalizar ID {row['ID']}", key=f"as_{row['ID']}"):
                    finalizar_chamado(row['ID'])
                    st.rerun()
    st.divider()
    st.subheader("Histórico Geral")
    st.dataframe(dados, use_container_width=True, hide_index=True)

# --- ABA 3: INDICADORES (A que você pediu!) ---
with aba_ind:
    st.subheader("Análise de Paradas")
    if dados.empty:
        st.warning("Ainda não há dados para gerar gráficos.")
    else:
        c1, c2 = st.columns(2)
        
        with c1:
            # Gráfico de Barras: Chamados por Célula
            fig_ups = px.bar(dados, x='Célula', title='Chamados por Célula (Acumulado)', 
                             color_discrete_sequence=['#ff4b4b'])
            st.plotly_chart(fig_ups, use_container_width=True)
            
        with c2:
            # Gráfico de Pizza: Motivos das Paradas
            fig_mot = px.pie(dados, names='Motivo', title='Principais Motivos de Parada',
                             hole=0.4)
            st.plotly_chart(fig_mot, use_container_width=True)

        st.divider()
        # Estatística rápida
        total_paradas = len(dados)
        st.metric("Total de Ocorrências no Período", f"{total_paradas} Chamados")

# Estilo Botão
st.markdown("""<style>div.stButton > button:first-child { width: 100%; height: 60px; font-size: 20px; }</style>""", unsafe_allow_html=True)
