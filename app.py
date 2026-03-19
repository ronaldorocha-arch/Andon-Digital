import streamlit as st
import pandas as pd
from datetime import datetime
import os
import plotly.express as px
import base64

# Configuração da Página
st.set_page_config(page_title="Andon Digital - NHS", page_icon="🚨", layout="wide")

DB_FILE = "registro_paradas.csv"
SENHA_ADMIN = "12345"

# --- FUNÇÃO PARA O SOM ---
def tocar_alerta():
    # Som de alerta (Bip curto e claro)
    audio_html = """
        <audio autoplay>
            <source src="https://raw.githubusercontent.com/rafaelpernil2/beat-detector/master/resources/sounds/bell.mp3" type="audio/mp3">
        </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)

# --- BASE DE DADOS ---
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação"]).to_csv(DB_FILE, index=False)

def carregar_dados():
    try:
        df = pd.read_csv(DB_FILE)
        if "Ação" not in df.columns: df["Ação"] = "-"
        return df
    except:
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação"])

def salvar_chamado(celula, motivo, desc):
    df = carregar_dados()
    novo_id = len(df) + 1
    agora = datetime.now()
    novo_registro = {
        "ID": novo_id, "Célula": celula, "Motivo": motivo, "Descrição": desc,
        "Início": agora.strftime("%H:%M:%S"), "Fim": "-", "Status": "🔴 Aberto",
        "Data": agora.strftime("%Y-%m-%d"), "Ação": "-"
    }
    df = pd.concat([df, pd.DataFrame([novo_registro])], ignore_index=True)
    df.to_csv(DB_FILE, index=False)

def finalizar_chamado(id_chamado, acao_desc):
    df = carregar_dados()
    idx = df[df['ID'] == id_chamado].index
    if not idx.empty:
        df.at[idx[0], 'Fim'] = datetime.now().strftime("%H:%M:%S")
        df.at[idx[0], 'Status'] = "🟢 Finalizado"
        df.at[idx[0], 'Ação'] = acao_desc
        df.to_csv(DB_FILE, index=False)

# --- CSS ---
st.markdown("""
    <style>
    @keyframes piscar { 0% { background-color: #ff4b4b; } 50% { background-color: #ff8e8e; } 100% { background-color: #ff4b4b; } }
    .piscante { animation: piscar 1s infinite; padding: 15px; border-radius: 10px; color: white; text-align: center; font-weight: bold; margin-bottom: 15px; }
    div.stButton > button:first-child { width: 100%; height: 50px; font-weight: bold; }
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
    with col1: sel_ups = st.selectbox("Sua Célula", ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"])
    with col2: sel_motivo = st.selectbox("Motivo", ["Falta de Material", "Qualidade", "Manutenção", "Processo", "Outros"])
    desc = st.text_area("O que aconteceu?", key="desc_op")
    chamado_esta_celula = ativos_as[ativos_as['Célula'] == sel_ups]

    if not chamado_esta_celula.empty:
        st.markdown(f'<div class="piscante"><h1>⏳ AGUARDANDO ASSISTENTE...</h1></div>', unsafe_allow_html=True)
    else:
        if st.button("🔔 CHAMAR ASSISTENTE", type="primary"):
            if desc: salvar_chamado(sel_ups, sel_motivo, desc); st.rerun()
            else: st.warning("Descreva o problema.")

# --- ABA 2: ASSISTENTE (COM SOM) ---
with aba_as:
    if not ativos_as.empty:
        tocar_alerta() # CHAMA A FUNÇÃO DE SOM
        st.markdown('<div class="piscante"><h2>⚠️ ATENÇÃO: HÁ CHAMADOS EM ABERTO!</h2></div>', unsafe_allow_html=True)
        for i, row in ativos_as.iterrows():
            with st.expander(f"🔴 {row['Célula']} - {row['Motivo']} ({row['Início']})", expanded=True):
                st.write(f"**Problema:** {row['Descrição']}")
                txt_acao = st.text_input(f"Ação Tomada (ID {row['ID']})", key=f"in_{row['ID']}")
                if st.button(f"✅ Concluir {row['ID']}", key=f"bt_{row['ID']}"):
                    if txt_acao: finalizar_chamado(row['ID'], txt_acao); st.rerun()
                    else: st.error("Descreva a ação.")
    else:
        st.info("✅ Nenhuma pendência.")
    st.divider()
    st.dataframe(dados_completos.sort_values(by="ID", ascending=False), use_container_width=True, hide_index=True)

# --- ABA 3: INDICADORES ---
with aba_ind:
    st.subheader("Análise de Performance")
    if not dados_completos.empty:
        datas_lista = sorted(dados_completos['Data'].unique(), reverse=True)
        data_sel = st.multiselect("Datas:", datas_lista, default=[datetime.now().strftime("%Y-%m-%d")] if datetime.now().strftime("%Y-%m-%d") in datas_lista else [])
        ups_sel = st.multiselect("Células:", sorted(dados_completos['Célula'].unique()))
        
        df_f = dados_completos.copy()
        if data_sel: df_f = df_f[df_f['Data'].isin(data_sel)]
        if ups_sel: df_f = df_f[df_f['Célula'].isin(ups_sel)]

        if not df_f.empty:
            c1, c2 = st.columns(2)
            with c1: st.plotly_chart(px.bar(df_f, x='Célula', title='Chamados por UPS', color_discrete_sequence=['#ff4b4b']), use_container_width=True)
            with c2: st.plotly_chart(px.pie(df_f, names='Motivo', title='Distribuição', hole=0.4), use_container_width=True)
            st.metric("Total de Acionamentos no Turno", len(df_f))
