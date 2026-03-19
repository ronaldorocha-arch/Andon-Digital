import streamlit as st
import pandas as pd
from datetime import datetime
import os
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="Andon Digital - NHS", page_icon="🚨", layout="wide")

DB_FILE = "registro_paradas.csv"
SENHA_ADMIN = "12345"

if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data"])
    df_init.to_csv(DB_FILE, index=False)

def carregar_dados():
    try:
        df = pd.read_csv(DB_FILE)
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
    lista_ups = ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"]
    with col1: sel_ups = st.selectbox("Sua Célula", lista_ups)
    with col2: sel_motivo = st.selectbox("Motivo", ["Falta de Material", "Qualidade", "Manutenção", "Processo", "Outros"])
    
    desc = st.text_area("O que aconteceu?", key="desc_op")
    chamado_esta_celula = dados_completos[(dados_completos['Célula'] == sel_ups) & (dados_completos['Status'] == "🔴 Aberto")]

    if not chamado_esta_celula.empty:
        st.markdown(f"""
            <div style="background-color: #ff4b4b; padding: 20px; border-radius: 10px; text-align: center; border: 4px solid white;">
                <h1 style="color: white; margin: 0;">⏳ AGUARDANDO ASSISTENTE...</h1>
                <p style="color: white; font-size: 20px;">O chamado para {sel_ups} foi enviado às {chamado_esta_celula.iloc[0]['Início']}</p>
            </div><br>
        """, unsafe_allow_html=True)
    else:
        if st.button("🔔 CHAMAR ASSISTENTE", type="primary"):
            if desc:
                salvar_chamado(sel_ups, sel_motivo, desc); st.success("Chamado enviado!"); st.rerun()
            else: st.warning("Descreva o problema.")

# --- ABA 2: ASSISTENTE ---
with aba_as:
    st.subheader("Controle de Atendimentos")
    ativos_as = dados_completos[dados_completos['Status'] == "🔴 Aberto"]
    if ativos_as.empty: st.info("✅ Nenhuma pendência.")
    else:
        for i, row in ativos_as.iterrows():
            with st.expander(f"🔴 {row['Célula']} - {row['Motivo']} ({row['Início']})", expanded=True):
                st.write(f"**Descrição:** {row['Descrição']}")
                if st.button(f"✅ Finalizar ID {row['ID']}", key=f"as_fin_{row['ID']}"):
                    finalizar_chamado(row['ID']); st.rerun()
    st.divider()
    st.subheader("Histórico Recente")
    st.dataframe(dados_completos.sort_values(by="ID", ascending=False), use_container_width=True, hide_index=True)

# --- ABA 3: INDICADORES COM FILTRO DE UPS ---
with aba_ind:
    st.subheader("Filtros de Análise")
    if dados_completos.empty:
        st.warning("Sem dados.")
    else:
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            hoje = datetime.now().strftime("%Y-%m-%d")
            datas_lista = sorted(dados_completos['Data'].unique(), reverse=True)
            data_sel = st.multiselect("1. Filtrar Datas:", datas_lista, default=[hoje] if hoje in datas_lista else [])
        
        with c_f2:
            ups_lista = sorted(dados_completos['Célula'].unique())
            ups_sel = st.multiselect("2. Filtrar Células (vazio = todas):", ups_lista)

        # Aplicando os filtros
        df_f = dados_completos.copy()
        if data_sel: df_f = df_f[df_f['Data'].isin(data_sel)]
        if ups_sel: df_f = df_f[df_f['Célula'].isin(ups_sel)]

        if df_f.empty:
            st.info("Nenhum dado encontrado para os filtros selecionados.")
        else:
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                # Se filtrar uma UPS só, o gráfico de barras mostra os motivos
                if len(ups_sel) == 1:
                    fig1 = px.bar(df_f, x='Motivo', title=f'Motivos de Parada: {ups_sel[0]}', color_discrete_sequence=['#ff4b4b'])
                else:
                    fig1 = px.bar(df_f, x='Célula', title='Ocorrências por UPS', color_discrete_sequence=['#ff4b4b'])
                st.plotly_chart(fig1, use_container_width=True)
            
            with c2:
                fig2 = px.pie(df_f, names='Motivo', title='Distribuição Geral de Motivos', hole=0.4)
                st.plotly_chart(fig2, use_container_width=True)
            
            st.metric("Total de Chamados no Filtro", len(df_f))

        # Administração
        st.divider()
        with st.expander("🛠️ Administração"):
            confirma_senha = st.text_input("Senha Admin", type="password")
            if st.button("⚠️ APAGAR TUDO"):
                if confirma_senha == SENHA_ADMIN:
                    pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data"]).to_csv(DB_FILE, index=False)
                    st.rerun()

st.markdown("""<style>div.stButton > button:first-child { width: 100%; height: 60px; font-weight: bold; }</style>""", unsafe_allow_html=True)
