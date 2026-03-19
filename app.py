import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# 1. Configuração e Auto-Refresh (30 segundos)
st.set_page_config(page_title="Andon Digital - NHS", page_icon="🚨", layout="wide")
st_autorefresh(interval=30000, key="datarefresh")

DB_FILE = "registro_paradas.csv"
SENHA_ACESSO = "12345"
LISTA_MOTIVOS = ["Falta de Material", "Qualidade", "Manutenção", "Processo", "Problemas com EP", "Outros"]

# --- MEMÓRIA DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

def get_brasil_time():
    return datetime.utcnow() - timedelta(hours=3)

# --- CSS PISCANTE ---
st.markdown("""
    <style>
    @keyframes piscar { 0% { background-color: #ff4b4b; } 50% { background-color: #7d0000; } 100% { background-color: #ff4b4b; } }
    .piscante { animation: piscar 1s infinite; padding: 20px; border-radius: 10px; color: white; text-align: center; font-weight: bold; margin-bottom: 20px; }
    div.stButton > button:first-child { width: 100%; height: 50px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

def carregar_dados():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"])
    try:
        df = pd.read_csv(DB_FILE)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce').dt.strftime('%d/%m/%Y')
        df = df.dropna(subset=['Data'])
        if "Minutos" not in df.columns: df["Minutos"] = 0.0
        return df
    except:
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"])

# --- PROCESSAMENTO ---
dados_completos = carregar_dados()
hoje_br = get_brasil_time().strftime("%d/%m/%Y")
ativos = dados_completos[dados_completos['Status'] == "🔴 Aberto"]
resolvidos_hoje = dados_completos[(dados_completos['Status'] == "🟢 Finalizado") & (dados_completos['Data'] == hoje_br)]

st.title("🚨 Andon Digital - NHS")
# Adicionada a aba "Relatórios"
aba_op, aba_as, aba_ind, aba_rel = st.tabs(["📲 Terminal Operador", "💻 Painel Assistente", "📊 Indicadores", "📂 Relatórios"])

# --- ABA 1: OPERADOR ---
with aba_op:
    st.subheader("Registrar Nova Parada")
    col1, col2 = st.columns(2)
    sel_ups = col1.selectbox("Célula", ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"])
    
    chamado_aberto = ativos[ativos['Célula'] == sel_ups]
    if chamado_aberto.empty:
        motivo = col2.selectbox("Motivo", LISTA_MOTIVOS)
        desc = st.text_area("Descreva o problema detalhadamente", key="desc_op")
        if st.button("🔔 CHAMAR AGORA", type="primary"):
            if desc:
                novo = pd.DataFrame([{"ID": len(dados_completos)+1, "Célula": sel_ups, "Motivo": motivo, "Descrição": desc, "Início": get_brasil_time().strftime("%H:%M:%S"), "Fim": "-", "Status": "🔴 Aberto", "Data": hoje_br, "Ação": "-", "Minutos": 0.0}])
                pd.concat([dados_completos, novo], ignore_index=True).to_csv(DB_FILE, index=False)
                st.rerun()
    else:
        st.markdown(f'<div class="piscante"><h1>⏳ AGUARDANDO ASSISTENTE...</h1><p style="font-size: 20px;">Célula: <b>{sel_ups}</b> | Motivo: <b>{chamado_aberto.iloc[0]["Motivo"]}</b></p></div>', unsafe_allow_html=True)

# --- ABA 2: ASSISTENTE ---
with aba_as:
    if not st.session_state.logado:
        senha_in = st.text_input("Senha do Painel", type="password", key="pwd_as")
        if st.button("Acessar Painel"):
            if senha_in == SENHA_ACESSO:
                st.session_state.logado = True
                st.rerun()
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("🔴 PARADAS AGORA", len(ativos))
        m2.metric("🟢 RESOLVIDOS HOJE", len(resolvidos_hoje))
        m3.metric("⏱️ MÉDIA (MIN)", f"{resolvidos_hoje['Minutos'].mean():.1f}" if not resolvidos_hoje.empty else "0.0")

        if not ativos.empty:
            st.markdown('<div class="piscante"><h2>⚠️ ATENÇÃO: HÁ CHAMADOS EM ABERTO!</h2></div>', unsafe_allow_html=True)
            for i, row in ativos.iterrows():
                with st.expander(f"🚨 {row['Célula']} ({row['Início']})", expanded=True):
                    st.write(f"**Problema:** {row['Descrição']}")
                    acao = st.text_input("Ação Tomada", key=f"re_{row['ID']}")
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
            st.success("✅ Nenhuma parada ativa no momento.")

        st.divider()
        with st.expander("🗑️ Limpeza de Turno"):
            st.warning("Isso limpa a tela da Assistente, mas os dados ficam salvos na aba 'Relatórios' se você não 'Zerar Tudo'.")
            if st.checkbox("Zerar visualização de hoje?"):
                if st.button("Limpar Tela Agora"):
                    df_reset = dados_completos[dados_completos['Data'] != hoje_br]
                    df_reset.to_csv(DB_FILE, index=False)
                    st.rerun()

# --- ABA 3: INDICADORES ---
with aba_ind:
    if st.session_state.logado:
        if not dados_completos.empty:
            datas_lista = sorted(list(set(dados_completos['Data'].unique())), reverse=True)
            sel_d = st.multiselect("Filtrar Datas:", datas_lista, default=[hoje_br] if hoje_br in datas_lista else [])
            df_ind = dados_completos[dados_completos['Data'].isin(sel_d)]

            if not df_ind.empty:
                g1, g2 = st.columns(2)
                with g1:
                    cont = df_ind['Célula'].value_counts().reset_index()
                    cont.columns = ['Célula', 'Qtd']
                    st.plotly_chart(px.bar(cont, x='Célula', y='Qtd', title="Volume de Paradas por UPS", color_discrete_sequence=['#ff4b4b']), use_container_width=True)
                with g2:
                    st.plotly_chart(px.pie(df_ind, names='Motivo', title="Principais Motivos", hole=0.4), use_container_width=True)
            else:
                st.info("ℹ️ Selecione uma data para gerar os gráficos.")
        else:
            st.info("ℹ️ Banco de dados vazio.")

# --- ABA 4: RELATÓRIOS (A NOVA!) ---
with aba_rel:
    if st.session_state.logado:
        st.subheader("📁 Histórico Geral de Chamados")
        
        # Filtros exclusivos para o relatório
        col_rel1, col_rel2 = st.columns(2)
        rel_ups = col_rel1.multiselect("Filtrar UPS:", sorted(dados_completos['Célula'].unique()), key="rel_ups")
        rel_mot = col_rel2.multiselect("Filtrar Motivo:", LISTA_MOTIVOS, key="rel_mot")
        
        df_relatorio = dados_completos.copy()
        if rel_ups: df_relatorio = df_relatorio[df_relatorio['Célula'].isin(rel_ups)]
        if rel_mot: df_relatorio = df_relatorio[df_relatorio['Motivo'].isin(rel_mot)]
        
        st.dataframe(df_relatorio.sort_values(by="ID", ascending=False), use_container_width=True, hide_index=True,
                     column_config={"ID": st.column_config.Column(width="small"), "Minutos": st.column_config.Column(width="small")})
        
        st.divider()
        csv = df_relatorio.to_csv(index=False).encode('utf-8-sig')
        st.download_button(label="📥 BAIXAR ESTA CONSULTA (EXCEL)", data=csv, file_name='Relatorio_Andon_NHS.csv', mime='text/csv')

        with st.expander("🛠️ ADMINISTRAÇÃO TOTAL (PERIGO)"):
            if st.text_input("Senha Admin para RESET TOTAL", type="password") == SENHA_ACESSO:
                if st.button("APAGAR TUDO PERMANENTEMENTE"):
                    if os.path.exists(DB_FILE): os.remove(DB_FILE)
                    st.rerun()
    else:
        st.warning("🔒 Faça login no 'Painel Assistente' para acessar os relatórios.")
