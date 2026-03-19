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

# --- CSS PARA ANIMAÇÃO PISCANTE ---
st.markdown("""
    <style>
    @keyframes piscar {
        0% { background-color: #ff4b4b; opacity: 1; }
        50% { background-color: #ff8e8e; opacity: 0.8; }
        100% { background-color: #ff4b4b; opacity: 1; }
    }
    .piscante {
        animation: piscar 1s infinite;
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        font-weight: bold;
        margin-bottom: 20px;
    }
    div.stButton > button:first-child {
        width: 100%;
        height: 60px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INTERFACE ---
st.title("🚨 Sistema Andon - Tecnologia de Processos")
aba_op, aba_as, aba_ind = st.tabs(["📲 Terminal do Operador", "💻 Painel da Assistente", "📊 Indicadores"])

dados_completos = carregar_dados()
ativos_as = dados_completos[dados_completos['Status'] == "🔴 Aberto"]

# --- ABA 1: OPERADOR ---
with aba_op:
    st.subheader("Registrar Nova Parada")
    col1, col2 = st.columns(2)
    lista_ups = ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"]
    with col1: sel_ups = st.selectbox("Sua Célula", lista_ups)
    with col2: sel_motivo = st.selectbox("Motivo", ["Falta de Material", "Qualidade", "Manutenção", "Processo", "Outros"])
    
    desc = st.text_area("O que aconteceu?", key="desc_op")
    chamado_esta_celula = ativos_as[ativos_as['Célula'] == sel_ups]

    if not chamado_esta_celula.empty:
        st.markdown(f'<div class="piscante"><h1>⏳ AGUARDANDO ASSISTENTE...</h1><p>Chamado enviado às {chamado_esta_celula.iloc[0]["Início"]}</p></div>', unsafe_allow_html=True)
    else:
        if st.button("🔔 CHAMAR ASSISTENTE", type="primary"):
            if desc:
                salvar_chamado(sel_ups, sel_motivo, desc); st.rerun()
            else: st.warning("Descreva o problema.")

# --- ABA 2: ASSISTENTE (COM EFEITO PISCANTE) ---
with aba_as:
    if not ativos_as.empty:
        # Título piscante se houver chamados
        st.markdown('<div class="piscante"><h2>⚠️ ATENÇÃO: HÁ CHAMADOS EM ABERTO!</h2></div>', unsafe_allow_html=True)
        
        for i, row in ativos_as.iterrows():
            with st.expander(f"🔴 {row['Célula']} - {row['Motivo']} ({row['Início']})", expanded=True):
                st.write(f"**Descrição:** {row['Descrição']}")
                if st.button(f"✅ Finalizar Atendimento {row['ID']}", key=f"as_fin_{row['ID']}"):
                    finalizar_chamado(row['ID']); st.rerun()
    else:
        st.info("✅ Nenhuma pendência no momento.")
    
    st.divider()
    st.subheader("Histórico Recente")
    st.dataframe(dados_completos.sort_values(by="ID", ascending=False), use_container_width=True, hide_index=True)

# --- ABA 3: INDICADORES ---
with aba_ind:
    st.subheader("Análise de Dados")
    if not dados_completos.empty:
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            datas_lista = sorted(dados_completos['Data'].unique(), reverse=True)
            data_sel = st.multiselect("Datas:", datas_lista, default=[datetime.now().strftime("%Y-%m-%d")] if datetime.now().strftime("%Y-%m-%d") in datas_lista else [])
        with c_f2:
            ups_lista = sorted(dados_completos['Célula'].unique())
            ups_sel = st.multiselect("Células:", ups_lista)

        df_f = dados_completos.copy()
        if data_sel: df_f = df_f[df_f['Data'].isin(data_sel)]
        if ups_sel: df_f = df_f[df_f['Célula'].isin(ups_sel)]

        if not df_f.empty:
            c1, c2 = st.columns(2)
            with c1:
                title = f'Motivos: {ups_sel[0]}' if len(ups_sel) == 1 else 'Chamados por UPS'
                x_val = 'Motivo' if len(ups_sel) == 1 else 'Célula'
                st.plotly_chart(px.bar(df_f, x=x_val, title=title, color_discrete_sequence=['#ff4b4b']), use_container_width=True)
            with c2:
                st.plotly_chart(px.pie(df_f, names='Motivo', title='Distribuição de Motivos', hole=0.4), use_container_width=True)

        st.divider()
        with st.expander("🛠️ Administração"):
            confirma_senha = st.text_input("Senha Admin", type="password")
            if st.button("⚠️ APAGAR TUDO"):
                if confirma_senha == SENHA_ADMIN:
                    pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data"]).to_csv(DB_FILE, index=False)
                    st.rerun()
