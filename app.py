import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Andon Digital - NHS", page_icon="🚨", layout="wide")
st_autorefresh(interval=30000, key="datarefresh")

DB_FILE = "registro_paradas.csv"
SENHA_ADMIN = "12345"

def get_brasil_time():
    return datetime.utcnow() - timedelta(hours=3)

# --- CARGA E PADRONIZAÇÃO ---
def carregar_dados():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"])
    df = pd.read_csv(DB_FILE)
    # FORÇA A PADRONIZAÇÃO: Se vier 2026-03-19, vira 19/03/2026
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce').dt.strftime('%d/%m/%Y')
    if "Minutos" not in df.columns: df["Minutos"] = 0.0
    return df

dados_completos = carregar_dados()
hoje_br = get_brasil_time().strftime("%d/%m/%Y")

st.title("🚨 Andon Digital - NHS")
aba_op, aba_as, aba_ind = st.tabs(["📲 Terminal Operador", "💻 Painel Assistente", "📊 Indicadores"])

# --- ABA 2: ASSISTENTE ---
with aba_as:
    # Filtra usando a data já padronizada
    ativos = dados_completos[dados_completos['Status'] == "🔴 Aberto"]
    resolvidos_hoje = dados_completos[(dados_completos['Status'] == "🟢 Finalizado") & (dados_completos['Data'] == hoje_br)]

    c1, c2, c3 = st.columns(3)
    c1.metric("🔴 PARADAS AGORA", len(ativos))
    c2.metric("🟢 RESOLVIDOS HOJE", len(resolvidos_hoje))
    c3.metric("⏱️ MÉDIA (MIN)", f"{resolvidos_hoje['Minutos'].mean():.1f}" if not resolvidos_hoje.empty else "0.0")
    
    with st.expander("🗑️ Opções de Limpeza"):
        # Usei um checkbox SEM chave de sessão para ele resetar no rerun
        if st.checkbox("Confirmar: Apagar tudo de hoje?", key="chk_reset_final"):
            if st.button("ZERAR AGORA"):
                # Remove tudo que for a data de hoje (já padronizada)
                df_limpo = dados_completos[dados_completos['Data'] != hoje_br]
                df_limpo.to_csv(DB_FILE, index=False)
                st.success("Limpeza realizada!")
                st.rerun()

    st.divider()
    # Histórico com colunas pequenas para ID e Célula
    st.subheader("Histórico Recente")
    st.dataframe(dados_completos.sort_values(by="ID", ascending=False), 
                 use_container_width=True, hide_index=True,
                 column_config={
                     "ID": st.column_config.Column(width="small"),
                     "Célula": st.column_config.Column(width="small")
                 })

# --- ABA 3: INDICADORES ---
with aba_ind:
    if not dados_completos.empty:
        # Filtro de data sem duplicatas
        datas_filtro = sorted(list(set(dados_completos['Data'].dropna())), reverse=True)
        sel = st.multiselect("Filtrar Datas:", datas_filtro, default=[hoje_br] if hoje_br in datas_filtro else [])
        
        df_f = dados_completos[dados_completos['Data'].isin(sel)] if sel else dados_completos
        if not df_f.empty:
            st.plotly_chart(px.bar(df_f['Célula'].value_counts().reset_index(), x='index', y='Célula', title="Qtd por UPS", color_discrete_sequence=['#ff4b4b']), use_container_width=True)

    st.divider()
    with st.expander("🛠️ RESET TOTAL (ADMIN)"):
        if st.text_input("Senha Admin", type="password") == SENHA_ADMIN:
            if st.button("APAGAR TODO O ARQUIVO CSV"):
                if os.path.exists(DB_FILE): os.remove(DB_FILE)
                st.rerun()
