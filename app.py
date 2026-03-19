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

def get_brasil_time():
    return datetime.utcnow() - timedelta(hours=3)

# --- INICIALIZAÇÃO DO BANCO ---
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"]).to_csv(DB_FILE, index=False)

# Função para carregar dados SEM CACHE para não travar na limpeza
def carregar_dados():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"])
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
        "Data": agora.strftime("%d/%m/%Y"), "Ação": "-", "Minutos": 0.0
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
    @keyframes piscar { 0% { background-color: #ff4b4b; } 50% { background-color: #9e0000; } 100% { background-color: #ff4b4b; } }
    .piscante { animation: piscar 1s infinite; padding: 15px; border-radius: 10px; color: white; text-align: center; font-weight: bold; margin-bottom: 15px; }
    div.stButton > button:first-child { width: 100%; height: 50px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- CARGA DE DADOS ---
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
    chamado_aberto = ativos[ativos['Célula'] == sel_ups]
    if chamado_aberto.empty:
        sel_motivo = col_b.selectbox("Motivo", LISTA_MOTIVOS, key="mot_op")
        desc = st.text_area("Descrição do problema", key="desc_op")
        if st.button("🔔 CHAMAR AGORA", type="primary"):
            if desc: 
                salvar_chamado(sel_ups, sel_motivo, desc)
                st.rerun()
    else:
        st.markdown(f'<div class="piscante"><h1>⏳ AGUARDANDO ASSISTENTE...</h1><p>Motivo: {chamado_aberto.iloc[0]["Motivo"]}</p></div>', unsafe_allow_html=True)

# --- ABA 2: ASSISTENTE ---
with aba_as:
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("🔴 PARADAS AGORA", len(ativos))
    col_m2.metric("🟢 RESOLVIDOS HOJE", len(resolvidos_hoje))
    media_tempo = resolvidos_hoje['Minutos'].mean() if not resolvidos_hoje.empty else 0.0
    col_m3.metric("⏱️ MÉDIA (MIN)", f"{media_tempo:.1f}")
    
    # LIMPEZA EFETIVA
    with st.expander("🗑️ Opções de Limpeza"):
        confirma_hoje = st.checkbox("Confirmar: Apagar tudo de hoje?", key="check_hoje")
        if st.button("ZERAR HOJE"):
            if confirma_hoje:
                df_restante = dados_completos[dados_completos['Data'] != hoje_br]
                df_restante.to_csv(DB_FILE, index=False)
                st.success("Dados de hoje limpos!")
                st.rerun()

    st.divider()
    if not ativos.empty:
        st.markdown('<div class="piscante"><h2>⚠️ CHAMADOS EM ABERTO!</h2></div>', unsafe_allow_html=True)
        for i, row in ativos.iterrows():
            with st.expander(f"🚨 {row['Célula']} - {row['Motivo']}", expanded=True):
                st.write(f"**Descrição:** {row['Descrição']}")
                txt_acao = st.text_input("Ação Tomada", key=f"acao_{row['ID']}")
                if st.button(f"✅ Finalizar {row['ID']}", key=f"btn_f_{row['ID']}"):
                    if txt_acao: finalizar_chamado(row['ID'], txt_acao); st.rerun()
    else: st.info("✅ Tudo em ordem.")
    
    st.divider()
    st.subheader("Histórico Recente")
    st.dataframe(dados_completos.sort_values(by="ID", ascending=False), use_container_width=True, hide_index=True,
                 column_config={"ID": st.column_config.Column(width="small"), "Célula": st.column_config.Column(width="small")})

# --- ABA 3: INDICADORES ---
with aba_ind:
    if not dados_completos.empty:
        col_f1, col_f2 = st.columns(2)
        datas_lista = sorted(list(set(dados_completos['Data'].unique())), reverse=True)
        data_sel = col_f1.multiselect("Filtro Datas:", datas_lista, default=[hoje_br] if hoje_br in datas_lista else [])
        ups_sel = col_f2.multiselect("Filtro Células:", sorted(dados_completos['Célula'].unique()))
        
        df_f = dados_completos.copy()
        if data_sel: df_f = df_f[df_f['Data'].isin(data_sel)]
        if ups_sel: df_f = df_f[df_f['Célula'].isin(ups_sel)]

        if not df_f.empty:
            g1, g2 = st.columns(2)
            df_count = df_f['Célula'].value_counts().reset_index()
            df_count.columns = ['Célula', 'Quantidade']
            g1.plotly_chart(px.bar(df_count, x='Célula', y='Quantidade', title='Ocorrências', color_discrete_sequence=['#ff4b4b']), use_container_width=True)
            g2.plotly_chart(px.pie(df_f, names='Motivo', title='Motivos', hole=0.4), use_container_width=True)
        
        st.divider()
        with st.expander("🛠️ Administração Geral"):
            if st.text_input("Senha Admin", type="password") == SENHA_ADMIN:
                if st.button("🗑️ APAGAR TUDO (HISTÓRICO COMPLETO)"):
                    if os.path.exists(DB_FILE): os.remove(DB_FILE)
                    st.rerun()
