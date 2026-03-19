import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# Configuração e Auto-Refresh (30 segundos)
st.set_page_config(page_title="Andon Digital - NHS", page_icon="🚨", layout="wide")
st_autorefresh(interval=30000, key="datarefresh")

DB_FILE = "registro_paradas.csv"
SENHA_ADMIN = "12345"

# --- FUNÇÃO HORÁRIO BRASÍLIA ---
def get_brasil_time():
    return datetime.utcnow() - timedelta(hours=3)

# --- CSS PARA O EFEITO PISCANTE (OBRIGATÓRIO NO TOPO) ---
st.markdown("""
    <style>
    @keyframes piscar {
        0% { background-color: #ff4b4b; }
        50% { background-color: #7d0000; }
        100% { background-color: #ff4b4b; }
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
        height: 50px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CARGA E PADRONIZAÇÃO DE DADOS ---
def carregar_dados():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"])
    try:
        df = pd.read_csv(DB_FILE)
        # Padroniza Datas
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce').dt.strftime('%d/%m/%Y')
        df = df.dropna(subset=['Data'])
        if "Minutos" not in df.columns: df["Minutos"] = 0.0
        return df
    except:
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"])

dados_completos = carregar_dados()
hoje_br = get_brasil_time().strftime("%d/%m/%Y")
ativos = dados_completos[dados_completos['Status'] == "🔴 Aberto"]
resolvidos_hoje = dados_completos[(dados_completos['Status'] == "🟢 Finalizado") & (dados_completos['Data'] == hoje_br)]

st.title("🚨 Andon Digital - NHS")
aba_op, aba_as, aba_ind = st.tabs(["📲 Terminal Operador", "💻 Painel Assistente", "📊 Indicadores"])

# --- ABA 1: OPERADOR ---
with aba_op:
    st.subheader("Registrar Nova Parada")
    col1, col2 = st.columns(2)
    sel_ups = col1.selectbox("Célula", ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"])
    
    chamado_aberto = ativos[ativos['Célula'] == sel_ups]
    if chamado_aberto.empty:
        motivo = col2.selectbox("Motivo", ["Falta de Material", "Qualidade", "Manutenção", "Processo", "Problemas com EP", "Outros"])
        desc = st.text_area("O que aconteceu?")
        if st.button("🔔 CHAMAR AGORA", type="primary"):
            if desc:
                novo = pd.DataFrame([{"ID": len(dados_completos)+1, "Célula": sel_ups, "Motivo": motivo, "Descrição": desc, "Início": get_brasil_time().strftime("%H:%M:%S"), "Fim": "-", "Status": "🔴 Aberto", "Data": hoje_br, "Ação": "-", "Minutos": 0.0}])
                pd.concat([dados_completos, novo], ignore_index=True).to_csv(DB_FILE, index=False)
                st.rerun()
    else:
        # AVISO PISCANTE NO OPERADOR
        st.markdown(f"""
            <div class="piscante">
                <h1>⏳ AGUARDANDO ASSISTENTE...</h1>
                <p style='font-size: 20px;'>Motivo: {chamado_aberto.iloc[0]['Motivo']}</p>
                <p>Relato: {chamado_aberto.iloc[0]['Descrição']}</p>
            </div>
        """, unsafe_allow_html=True)

# --- ABA 2: ASSISTENTE ---
with aba_as:
    m1, m2, m3 = st.columns(3)
    m1.metric("🔴 PARADAS AGORA", len(ativos))
    m2.metric("🟢 RESOLVIDOS HOJE", len(resolvidos_hoje))
    m3.metric("⏱️ MÉDIA (MIN)", f"{resolvidos_hoje['Minutos'].mean():.1f}" if not resolvidos_hoje.empty else "0.0")

    if not ativos.empty:
        # AVISO PISCANTE NA ASSISTENTE
        st.markdown('<div class="piscante"><h2>⚠️ ATENÇÃO: HÁ CHAMADOS EM ABERTO!</h2></div>', unsafe_allow_html=True)
        for i, row in ativos.iterrows():
            with st.expander(f"🚨 {row['Célula']} ({row['Início']})", expanded=True):
                st.write(f"**Problema:** {row['Descrição']}")
                acao = st.text_input("O que foi feito?", key=f"re_{row['ID']}")
                if st.button(f"Finalizar {row['ID']}", key=f"f_{row['ID']}"):
                    if acao:
                        df_f = carregar_dados()
                        idx = df_f[df_f['ID'] == row['ID']].index
                        df_f.at[idx[0], 'Status'] = "🟢 Finalizado"
                        df_f.at[idx[0], 'Fim'] = get_brasil_time().strftime("%H:%M:%S")
                        df_f.at[idx[0], 'Ação'] = acao
                        h1 = datetime.strptime(df_f.at[idx[0], 'Início'], "%H:%M:%S")
                        h2 = datetime.strptime(df_f.at[idx[0], 'Fim'], "%H:%M:%S")
                        df_f.at[idx[0], 'Minutos'] = round((h2 - h1).total_seconds() / 60, 1)
                        df_f.to_csv(DB_FILE, index=False)
                        st.rerun()
    else:
        st.success("✅ Tudo em ordem por aqui!")

    with st.expander("🗑️ Opções de Limpeza"):
        if st.checkbox("Confirmar exclusão de hoje?", key="chk_final"):
            if st.button("ZERAR CONTRETAGEM DE HOJE"):
                df_reset = dados_completos[dados_completos['Data'] != hoje_br]
                df_reset.to_csv(DB_FILE, index=False)
                st.rerun()

# --- ABA 3: INDICADORES (FILTROS RECUPERADOS) ---
with aba_ind:
    st.subheader("Filtros e Análise")
    if not dados_completos.empty:
        f_col1, f_col2 = st.columns(2)
        
        # Filtro de Data
        lista_datas = sorted(list(set(dados_completos['Data'].unique())), reverse=True)
        sel_d = f_col1.multiselect("Filtrar Datas:", lista_datas, default=[hoje_br] if hoje_br in lista_datas else [])
        
        # Filtro de Célula
        lista_ups = sorted(dados_completos['Célula'].unique())
        sel_ups_ind = f_col2.multiselect("Filtrar Células (vazio=todas):", lista_ups)

        df_ind = dados_completos.copy()
        if sel_d:
            df_ind = df_ind[df_ind['Data'].isin(sel_d)]
        if sel_ups_ind:
            df_ind = df_ind[df_ind['Célula'].isin(sel_ups_ind)]

        if not df_ind.empty:
            g1, g2 = st.columns(2)
            with g1:
                contagem = df_ind['Célula'].value_counts().reset_index()
                contagem.columns = ['Célula', 'Qtd']
                st.plotly_chart(px.bar(contagem, x='Célula', y='Qtd', title="Quantidade por UPS", color_discrete_sequence=['#ff4b4b']), use_container_width=True)
            with g2:
                st.plotly_chart(px.pie(df_ind, names='Motivo', title="Distribuição por Motivo", hole=0.4), use_container_width=True)
            
            st.dataframe(df_ind.sort_values(by="ID", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ Selecione filtros para ver os gráficos.")
    
    with st.expander("🛠️ ADMINISTRAÇÃO"):
        if st.text_input("Senha Admin", type="password") == SENHA_ADMIN:
            if st.button("LIMPAR TODO O HISTÓRICO"):
                if os.path.exists(DB_FILE): os.remove(DB_FILE)
                st.rerun()
