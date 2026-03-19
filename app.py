import streamlit as st
import pandas as pd
from datetime import datetime
import os
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="Andon Digital - NHS", page_icon="🚨", layout="wide")

DB_FILE = "registro_paradas.csv"

# NOVA SENHA DEFINIDA: 12345
SENHA_ADMIN = "12345"

# Inicializar o arquivo com a coluna Data se não existir
if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data"])
    df_init.to_csv(DB_FILE, index=False)

def carregar_dados():
    try:
        df = pd.read_csv(DB_FILE)
        # Garante que registros antigos sem data recebam a data de hoje para não quebrar o filtro
        if not df.empty and "Data" not in df.columns:
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
    
    desc = st.text_area("O que aconteceu?", key="desc_op", placeholder="Descreva o problema detalhadamente...")
    if st.button("🔔 CHAMAR ASSISTENTE", type="primary"):
        if desc:
            salvar_chamado(sel_ups, sel_motivo, desc)
            st.success("Chamado enviado com sucesso!")
            st.rerun()
        else:
            st.warning("Por favor, descreva o problema.")

    # Visualização de chamados em aberto para o operador saber que foi registrado
    ativos_op = dados_completos[dados_completos['Status'] == "🔴 Aberto"]
    if not ativos_op.empty:
        st.divider()
        st.subheader("⚠️ Chamados em Espera")
        st.table(ativos_op[['Célula', 'Motivo', 'Início']])

# --- ABA 2: ASSISTENTE ---
with aba_as:
    st.subheader("Controle de Atendimentos")
    ativos_as = dados_completos[dados_completos['Status'] == "🔴 Aberto"]
    
    if ativos_as.empty:
        st.info("✅ Nenhuma pendência. Linhas operando normalmente.")
    else:
        for i, row in ativos_as.iterrows():
            with st.expander(f"🔴 {row['Célula']} - {row['Motivo']} ({row['Início']})", expanded=True):
                st.write(f"**Descrição:** {row['Descrição']}")
                if st.button(f"✅ Finalizar ID {row['ID']}", key=f"as_fin_{row['ID']}"):
                    finalizar_chamado(row['ID'])
                    st.rerun()
    
    st.divider()
    st.subheader("Histórico Recente")
    st.dataframe(dados_completos.sort_values(by="ID", ascending=False), use_container_width=True, hide_index=True)

# --- ABA 3: INDICADORES ---
with aba_ind:
    st.subheader("Dashboard de Performance")
    
    if dados_completos.empty:
        st.warning("Aguardando os primeiros registros para gerar indicadores.")
    else:
        # Filtro de Data (Inicia focado no dia de hoje)
        hoje = datetime.now().strftime("%Y-%m-%d")
        datas_lista = sorted(dados_completos['Data'].unique(), reverse=True)
        
        # Se hoje não tiver dados, ele não trava o filtro
        default_filtro = [hoje] if hoje in datas_lista else []
        
        data_sel = st.multiselect("Selecione a(s) data(s) para análise:", datas_lista, default=default_filtro)
        
        df_grafico = dados_completos[dados_completos['Data'].isin(data_sel)] if data_sel else dados_completos

        if df_grafico.empty:
            st.info("Nenhuma ocorrência registrada nas datas selecionadas.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                fig1 = px.bar(df_grafico, x='Célula', title='Ocorrências por UPS', color_discrete_sequence=['#ff4b4b'])
                st.plotly_chart(fig1, use_container_width=True)
            with c2:
                fig2 = px.pie(df_grafico, names='Motivo', title='Distribuição por Motivo', hole=0.4)
                st.plotly_chart(fig2, use_container_width=True)
            
            st.metric("Total de Paradas no período selecionado", len(df_grafico))

        # --- ÁREA DE ADMINISTRAÇÃO ---
        st.divider()
        with st.expander("🛠️ Administração do Sistema"):
            st.write("Para apagar o banco de dados e zerar o sistema, digite a senha:")
            confirma_senha = st.text_input("Senha de Administrador", type="password")
            if st.button("⚠️ APAGAR TUDO PERMANENTEMENTE"):
                if confirma_senha == SENHA_ADMIN:
                    df_reset = pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data"])
                    df_reset.to_csv(DB_FILE, index=False)
                    st.success("Histórico reiniciado!")
                    st.rerun()
                else:
                    st.error("Senha incorreta. Ação negada.")

# CSS para botões de ação rápida
st.markdown("""
    <style>
    div.stButton > button:first-child {
        width: 100%;
        height: 60px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
