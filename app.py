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

# --- FUNÇÃO PARA O SOM ---
def tocar_alerta():
    audio_html = """<audio autoplay><source src="https://raw.githubusercontent.com/rafaelpernil2/beat-detector/master/resources/sounds/bell.mp3" type="audio/mp3"></audio>"""
    st.markdown(audio_html, unsafe_allow_html=True)

# --- BASE DE DADOS ---
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"]).to_csv(DB_FILE, index=False)

def carregar_dados():
    try:
        df = pd.read_csv(DB_FILE)
        if "Minutos" not in df.columns: df["Minutos"] = 0
        return df
    except:
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"])

def salvar_chamado(celula, motivo, desc):
    df = carregar_dados()
    agora = datetime.now()
    novo = {
        "ID": len(df) + 1, "Célula": celula, "Motivo": motivo, "Descrição": desc,
        "Início": agora.strftime("%H:%M:%S"), "Fim": "-", "Status": "🔴 Aberto",
        "Data": agora.strftime("%Y-%m-%d"), "Ação": "-", "Minutos": 0
    }
    pd.concat([df, pd.DataFrame([novo])], ignore_index=True).to_csv(DB_FILE, index=False)

def finalizar_chamado(id_chamado, acao_desc):
    df = carregar_dados()
    idx = df[df['ID'] == id_chamado].index
    if not idx.empty:
        agora = datetime.now()
        hora_fim = agora.strftime("%H:%M:%S")
        # Cálculo do Lead Time (Minutos)
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
    [data-testid="stMetricValue"] { font-size: 40px; }
    </style>
    """, unsafe_allow_html=True)

# --- INTERFACE ---
dados_completos = carregar_dados()
hoje = datetime.now().strftime("%Y-%m-%d")
ativos = dados_completos[dados_completos['Status'] == "🔴 Aberto"]
resolvidos_hoje = dados_completos[(dados_completos['Status'] == "🟢 Finalizado") & (dados_completos['Data'] == hoje)]

# --- SEMÁFORO (KPIs) ---
st.title("🚨 Andon Digital NHS - Tecnologia de Processos")
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("🔴 PARADAS AGORA", len(ativos))
with c2:
    st.metric("🟢 RESOLVIDOS HOJE", len(resolvidos_hoje))
with c3:
    media_tempo = resolvidos_hoje['Minutos'].mean() if not resolvidos_hoje.empty else 0
    st.metric("⏱️ LEAD TIME MÉDIO (MIN)", f"{media_tempo:.1f}")

aba_op, aba_as, aba_ind = st.tabs(["📲 Terminal Operador", "💻 Painel Assistente", "📊 Indicadores"])

# --- ABA 1: OPERADOR ---
with aba_op:
    st.subheader("Registrar Nova Parada")
    col_a, col_b = st.columns(2)
    sel_ups = col_a.selectbox("Célula", ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"])
    sel_motivo = col_b.selectbox("Motivo", ["Falta de Material", "Qualidade", "Manutenção", "Processo", "Outros"])
    desc = st.text_area("Descrição do problema")
    
    if not ativos[ativos['Célula'] == sel_ups].empty:
        st.markdown('<div class="piscante"><h1>⏳ AGUARDANDO ASSISTENTE...</h1></div>', unsafe_allow_html=True)
    else:
        if st.button("🔔 CHAMAR AGORA", type="primary"):
            if desc: salvar_chamado(sel_ups, sel_motivo, desc); st.rerun()

# --- ABA 2: ASSISTENTE ---
with aba_as:
    if not ativos.empty:
        tocar_alerta()
        st.markdown('<div class="piscante"><h2>⚠️ HÁ CHAMADOS EM ABERTO!</h2></div>', unsafe_allow_html=True)
        for i, row in ativos.iterrows():
            with st.expander(f"🚨 {row['Célula']} ({row['Início']})", expanded=True):
                st.write(f"**Problema:** {row['Descrição']}")
                txt_acao = st.text_input(f"O que foi feito? (ID {row['ID']})", key=f"ac_{row['ID']}")
                if st.button(f"✅ Finalizar {row['ID']}", key=f"bt_{row['ID']}"):
                    if txt_acao: finalizar_chamado(row['ID'], txt_acao); st.rerun()
    else: st.info("✅ Nenhuma pendência.")
    st.divider()
    st.dataframe(dados_completos.sort_values(by="ID", ascending=False), use_container_width=True, hide_index=True)

# --- ABA 3: INDICADORES ---
with aba_ind:
    if not dados_completos.empty:
        df_f = dados_completos[dados_completos['Data'] == hoje]
        st.subheader(f"Análise do Dia: {hoje}")
        
        g1, g2 = st.columns(2)
        with g1:
            st.plotly_chart(px.bar(df_f, x='Célula', y='Minutos', title='Lead Time por Célula (Minutos)', color='Motivo'), use_container_width=True)
        with g2:
            st.plotly_chart(px.pie(df_f, names='Motivo', title='Volume por Motivo', hole=0.4), use_container_width=True)
        
        st.divider()
        with st.expander("🛠️ Administração"):
            if st.text_input("Senha Admin", type="password") == SENHA_ADMIN:
                if st.button("⚠️ RESETAR BANCO DE DADOS"):
                    pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"]).to_csv(DB_FILE, index=False)
                    st.rerun()
