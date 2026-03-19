import streamlit as st
import pandas as pd
from datetime import datetime
import os
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# Configuração da Página
st.set_page_config(page_title="Andon Digital - NHS", page_icon="🚨", layout="wide")

# Atualiza a página automaticamente a cada 30 segundos
st_autorefresh(interval=30000, key="datarefresh")

DB_FILE = "registro_paradas.csv"
SENHA_ADMIN = "12345"
LISTA_MOTIVOS = ["Falta de Material", "Qualidade", "Manutenção", "Processo", "Problemas com EP", "Outros"]

# --- FUNÇÕES DE BANCO DE DADOS ---
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"]).to_csv(DB_FILE, index=False)

def carregar_dados():
    try:
        df = pd.read_csv(DB_FILE)
        if "Minutos" not in df.columns:
            df["Minutos"] = 0.0
            df.to_csv(DB_FILE, index=False)
        return df
    except:
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"])

def salvar_chamado(celula, motivo, desc):
    df = carregar_dados()
    agora = datetime.now()
    novo = {
        "ID": len(df) + 1, "Célula": celula, "Motivo": motivo, "Descrição": desc,
        "Início": agora.strftime("%H:%M:%S"), "Fim": "-", "Status": "🔴 Aberto",
        "Data": agora.strftime("%Y-%m-%d"), "Ação": "-", "Minutos": 0.0
    }
    pd.concat([df, pd.DataFrame([novo])], ignore_index=True).to_csv(DB_FILE, index=False)

def finalizar_chamado(id_chamado, acao_desc):
    df = carregar_dados()
    idx = df[df['ID'] == id_chamado].index
    if not idx.empty:
        agora = datetime.now()
        hora_fim = agora.strftime("%H:%M:%S")
        h1 = datetime.strptime(df.at[idx[0], 'Início'], "%H:%M:%S")
        h2 = datetime.strptime(hora_fim, "%H:%M:%S")
        diff_minutos = round((h2 - h1).total_seconds() / 60, 1)
        df.at[idx[0], 'Fim'] = hora_fim
        df.at[idx[0], 'Status'] = "🟢 Finalizado"
        df.at[idx[0], 'Ação'] = acao_desc
        df.at[idx[0], 'Minutos'] = diff_minutos
        df.to_csv(DB_FILE, index=False)

# --- CSS ---
st.markdown("""
    <style>
    @keyframes piscar { 0% { background-color: #ff4b4b; } 50% { background-color: #ff8e8e; } 100% { background-color: #ff4b4b; } }
    .piscante { animation: piscar 1s infinite; padding: 15px; border-radius: 10px; color: white; text-align: center; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- DADOS ATUAIS ---
dados_completos = carregar_dados()
hoje = datetime.now().strftime("%Y-%m-%d")
ativos = dados_completos[dados_completos['Status'] == "🔴 Aberto"]
resolvidos_hoje = dados_completos[(dados_completos['Status'] == "🟢 Finalizado") & (dados_completos['Data'] == hoje)]

st.title("🚨 Andon Digital - Tecnologia de Processos")
aba_op, aba_as, aba_ind = st.tabs(["📲 Terminal Operador", "💻 Painel Assistente", "📊 Indicadores"])

# --- ABA 1: OPERADOR ---
with aba_op:
    st.subheader("Registrar Nova Parada")
    col_a, col_b = st.columns(2)
    sel_ups = col_a.selectbox("Célula", ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"])
    sel_motivo = col_b.selectbox("Motivo", LISTA_MOTIVOS)
    desc = st.text_area("Descrição do problema", key="op_desc")
    
    if not ativos[ativos['Célula'] == sel_ups].empty:
        st.markdown('<div class="piscante"><h1>⏳ AGUARDANDO ASSISTENTE...</h1></div>', unsafe_allow_html=True)
    else:
        if st.button("🔔 CHAMAR AGORA", type="primary"):
            if desc: 
                salvar_chamado(sel_ups, sel_motivo, desc)
                st.rerun()

# --- ABA 2: ASSISTENTE ---
with aba_as:
    col_met1, col_met2, col_met3 = st.columns(3)
    col_met1.metric("🔴 PARADAS AGORA", len(ativos))
    col_met2.metric("🟢 RESOLVIDOS HOJE", len(resolvidos_hoje))
    media_tempo = resolvidos_hoje['Minutos'].mean() if not resolvidos_hoje.empty else 0.0
    col_met3.metric("⏱️ LEAD TIME MÉDIO (MIN)", f"{media_tempo:.1f}")
    
    # BOTÃO PARA ZERAR O DIA
    if st.button("🗑️ Zerar Contagem de Hoje", help="Apaga todos os registros apenas da data de hoje"):
        df_limpo = dados_completos[dados_completos['Data'] != hoje]
        df_limpo.to_csv(DB_FILE, index=False)
        st.warning("Dados de hoje foram removidos.")
        st.rerun()

    st.divider()
    
    if not ativos.empty:
        st.markdown('<div class="piscante"><h2>⚠️ HÁ CHAMADOS EM ABERTO!</h2></div>', unsafe_allow_html=True)
        for i, row in ativos.iterrows():
            with st.expander(f"🚨 {row['Célula']} ({row['Início']})", expanded=True):
                st.write(f"**Problema:** {row['Descrição']}")
                txt_acao = st.text_input(f"Ação Tomada (ID {row['ID']})", key=f"ac_{row['ID']}")
                if st.button(f"✅ Finalizar {row['ID']}", key=f"bt_{row['ID']}"):
                    if txt_acao: 
                        finalizar_chamado(row['ID'], txt_acao)
                        st.rerun()
    else: 
        st.info("✅ Nenhuma pendência no momento.")
    
    st.divider()
    st.subheader("Histórico Recente")
    st.dataframe(dados_completos.sort_values(by="ID", ascending=False), use_container_width=True, hide_index=True)

# --- ABA 3: INDICADORES ---
with aba_ind:
    if not dados_completos.empty:
        c_f1, c_f2 = st.columns(2)
        datas_lista = sorted(dados_completos['Data'].unique(), reverse=True)
        data_sel = c_f1.multiselect("Datas:", datas_lista, default=[hoje] if hoje in datas_lista else [])
        ups_sel = c_f2.multiselect("Células:", sorted(dados_completos['Célula'].unique()))
        
        df_f = dados_completos.copy()
        if data_sel: df_f = df_f[df_f['Data'].isin(data_sel)]
        if ups_sel: df_f = df_f[df_f['Célula'].isin(ups_sel)]

        if not df_f.empty:
            g1, g2 = st.columns(2)
            with g1:
                # CONTAGEM DE PARADAS (Frequency)
                df_count = df_f['Célula'].value_counts().reset_index()
                df_count.columns = ['Célula', 'Quantidade']
                st.plotly_chart(px.bar(df_count, x='Célula', y='Quantidade', 
                                      title='Quantidade de Paradas por Célula', 
                                      color_discrete_sequence=['#ff4b4b'], text_auto=True), use_container_width=True)
            with g2:
                st.plotly_chart(px.pie(df_f, names='Motivo', title='Distribuição de Motivos', hole=0.4), use_container_width=True)
        
        st.divider()
        with st.expander("🛠️ Administração do Sistema"):
            if st.text_input("Senha Admin", type="password") == SENHA_ADMIN:
                if st.button("⚠️ APAGAR TODO O HISTÓRICO (TOTAL)"):
                    if os.path.exists(DB_FILE): os.remove(DB_FILE)
                    st.rerun()

st.markdown("""<style>div.stButton > button:first-child { width: 100%; height: 50px; font-weight: bold; }</style>""", unsafe_allow_html=True)
