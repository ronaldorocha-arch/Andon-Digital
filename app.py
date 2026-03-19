import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Configuração da Página
st.set_page_config(page_title="Andon Digital - NHS", page_icon="🚨", layout="wide")

# Nome do arquivo de banco de dados local
DB_FILE = "registro_paradas.csv"

# Inicializar o arquivo se não existir
if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status"])
    df_init.to_csv(DB_FILE, index=False)

def carregar_dados():
    try:
        # Lendo e garantindo que o ID seja tratado corretamente
        df = pd.read_csv(DB_FILE)
        return df
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

aba_op, aba_as = st.tabs(["📲 Terminal do Operador", "💻 Painel da Assistente"])

# --- LÓGICA DE DADOS COMPARTILHADA ---
dados = carregar_dados()
ativos = dados[dados['Status'] == "🔴 Aberto"]

with aba_op:
    st.subheader("Registrar Nova Parada")
    col1, col2 = st.columns(2)
    with col1:
        sel_ups = st.selectbox("Sua Célula", ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"])
    with col2:
        sel_motivo = st.selectbox("Motivo", ["Falta de Material", "Qualidade", "Manutenção", "Processo", "Outros"])
    
    desc = st.text_area("O que aconteceu?", placeholder="Descreva o problema aqui...")
    
    if st.button("🔔 CHAMAR ASSISTENTE", type="primary"):
        if desc:
            salvar_chamado(sel_ups, sel_motivo, desc)
            st.success("Chamado enviado! Aguarde o atendimento.")
            st.rerun()
        else:
            st.warning("Por favor, descreva o problema antes de chamar.")

    # --- NOVIDADE: Confirmação visual para o Operador ---
    if not ativos.empty:
        st.divider()
        st.subheader("⚠️ Chamados Pendentes no Setor")
        # Mostra apenas os dados mais importantes para o operador não se confundir
        st.table(ativos[['Célula', 'Motivo', 'Início']])

with aba_as:
    st.subheader("Painel de Controle da Assistente")
    
    if ativos.empty:
        st.info("✅ Nenhuma parada registrada. Todas as linhas operando.")
    else:
        # Exibe os chamados ativos em formato de cartões (expanders)
        for i, row in ativos.iterrows():
            with st.expander(f"🔴 AGUARDANDO: {row['Célula']} ({row['Início']})", expanded=True):
                st.write(f"**Motivo:** {row['Motivo']}")
                st.write(f"**Detalhe:** {row['Descrição']}")
                if st.button(f"✅ Finalizar Atendimento {row['ID']}", key=f"btn_as_{row['ID']}"):
                    finalizar_chamado(row['ID'])
                    st.rerun()
    
    st.divider()
    st.subheader("Histórico Completo")
    st.dataframe(dados, use_container_width=True, hide_index=True)

# Estilo visual
st.markdown("""
    <style>
    div.stButton > button:first-child {
        width: 100%;
        height: 70px;
        font-size: 24px !important;
    }
    </style>
    """, unsafe_allow_html=True)
