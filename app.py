import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
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

# --- FUNÇÃO PARA PEGAR HORA DE BRASILIA (UTC-3) ---
def get_brasil_time():
    # O Streamlit Cloud costuma usar UTC. Subtraímos 3 horas para Brasília.
    return datetime.utcnow() - timedelta(hours=3)

# --- FUNÇÕES DE BANCO DE DADOS ---
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"]).to_csv(DB_FILE, index=False)

def carregar_dados():
    try:
        df = pd.read_csv(DB_FILE)
        if "Minutos" not in df.columns: df["Minutos"] = 0.0
        return df
    except:
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"])

def salvar_chamado(celula, motivo, desc):
    df = carregar_dados()
    agora = get_brasil_time()
    novo = {
        "ID": len(df) + 1, "Célula": celula, "Motivo": motivo, "Descrição": desc,
        "Início": agora.strftime("%H:%M:%S"), "Fim": "-", "Status": "🔴 Aberto",
        "Data": agora.strftime("%d/%m/%Y"), # Formato Brasil
        "Ação": "-", "Minutos": 0.0
    }
    pd.concat([df, pd.DataFrame([novo])], ignore_index=True).to_csv(DB_FILE, index=False)

def finalizar_chamado(id_chamado, acao_desc):
    df = carregar_dados()
    idx = df[df['ID'] == id_chamado].index
    if not idx.empty:
        agora = get_brasil_time()
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
    div.stButton > button:first-child { width: 100%; height: 50px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGICA DE RESET DE FORMULÁRIO ---
if 'form_desc' not in st.session_state: st.session_state.form_desc = ""

# --- DADOS ---
dados_completos = carregar_dados()
hoje_br = get_brasil_time().strftime("%d/%m/%Y")
ativos = dados_completos[dados_completos['Status'] == "🔴 Aberto"]
resolvidos_hoje = dados_completos[(dados_completos['Status'] == "🟢 Finalizado") & (dados_completos['Data'] == hoje_br)]

st.title("🚨 Andon Digital - NHS")
aba_op, aba_as, aba_ind = st.tabs(["📲 Terminal Operador", "💻 Painel Assistente", "📊 Indicadores"])

# --- ABA 1: OPERADOR ---
with aba_op:
    st.subheader("Registrar Nova Parada")
    col_a, col_b = st.columns(2)
    sel_ups = col_a.selectbox("Célula", ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"])
    
    # Se não houver chamado aberto para esta UPS, mostra o formulário limpo
    if ativos[ativos['Célula'] == sel_ups].empty:
        sel_motivo = col_b.selectbox("Motivo", LISTA_MOTIVOS, key="motivo_op")
        desc = st.text_area("Descrição do problema", key="desc_op")
        if st.button("🔔 CHAMAR AGORA", type="primary"):
            if desc: 
                salvar_chamado(sel_ups, sel_motivo, desc)
                st.rerun()
    else:
        st.markdown(f'<div class="piscante"><h1>⏳ AGUARDANDO ASSISTENTE...</h1><p>Célula {sel_ups} em atendimento.</p></div>', unsafe_allow_html=True)

# --- ABA 2: ASSISTENTE ---
with aba_as:
    c1, c2, c3 = st.columns(3)
    c1.metric("🔴 PARADAS AGORA", len(ativos))
    c2.metric("🟢 RESOLVIDOS HOJE", len(resolvidos_hoje))
    media_tempo = resolvidos_hoje['Minutos'].mean() if not resolvidos_hoje.empty else 0.0
    c3.metric("⏱️ MÉDIA (MIN)", f"{media_tempo:.1f}")
    
    with st.expander("🗑️ Opções de Limpeza"):
        confirma = st.checkbox("Eu quero zerar os chamados de hoje.")
        if st.button("Zerar Contagem de Hoje"):
            if confirma:
                df_limpo = dados_completos[dados_completos['Data'] != hoje_br]
                df_limpo.to_csv(DB_FILE, index=False)
                st.success("Dados de hoje limpos!")
                st.rerun()
            else:
                st.error("Marque a confirmação acima para apagar.")

    st.divider()
    
    if not ativos.empty:
        for i, row in ativos.iterrows():
            with st.expander(f"🚨 {row['Célula']} ({row['Início']})", expanded=True):
                st.write(f"**Operador:** {row['Descrição']}")
                txt_acao = st.text_input(f"Ação Tomada", key=f"ac_{row['ID']}")
                if st.button(f"✅ Finalizar ID {row['ID']}", key=f"bt_{row['ID']}"):
                    if txt_acao: finalizar_chamado(row['ID'], txt_acao); st.rerun()
    else: st.info("✅ Nenhuma pendência.")
    
    st.divider()
    # Tabela com ID menor
    st.dataframe(dados_completos.sort_values(by="ID", ascending=False), 
                 use_container_width=True, hide_index=True,
                 column_config={"ID": st.column_config.Column(width="small")})

# --- ABA 3: INDICADORES ---
with aba_ind:
    if not dados_completos.empty:
        datas_lista = sorted(dados_completos['Data'].unique(), reverse=True)
        data_sel = st.multiselect("Datas:", datas_lista, default=[hoje_br] if hoje_br in datas_lista else [])
        
        df_f = dados_completos[dados_completos['Data'].isin(data_sel)] if data_sel else dados_completos

        if not df_f.empty:
            g1, g2 = st.columns(2)
            with g1:
                df_count = df_f['Célula'].value_counts().reset_index()
                df_count.columns = ['Célula', 'Quantidade']
                st.plotly_chart(px.bar(df_count, x='Célula', y='Quantidade', title='Ocorrências por Célula', color_discrete_sequence=['#ff4b4b']), use_container_width=True)
            with g2:
                st.plotly_chart(px.pie(df_f, names='Motivo', title='Distribuição por Motivo', hole=0.4), use_container_width=True)
