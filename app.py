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
    # Ajuste preciso para o servidor
    return datetime.utcnow() - timedelta(hours=3)

# --- INICIALIZAÇÃO E PADRONIZAÇÃO ---
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"]).to_csv(DB_FILE, index=False)

def carregar_dados():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"])
    try:
        df = pd.read_csv(DB_FILE)
        # Força a coluna Data a ser string para evitar erros de formato
        df['Data'] = df['Data'].astype(str)
        if "Minutos" not in df.columns: df["Minutos"] = 0.0
        return df
    except:
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"])

# --- INTERFACE ---
dados_completos = carregar_dados()
agora_br = get_brasil_time()
hoje_br = agora_br.strftime("%d/%m/%Y")
# Pega também o formato americano caso tenha sobrado no CSV
hoje_usa = agora_br.strftime("%Y-%m-%d")

st.title("🚨 Andon Digital - NHS")
aba_op, aba_as, aba_ind = st.tabs(["📲 Terminal Operador", "💻 Painel Assistente", "📊 Indicadores"])

# --- ABA 2: ASSISTENTE (ONDE ESTÁ O PROBLEMA DO ZERAR) ---
with aba_as:
    # Filtrando ativos e resolvidos HOJE
    ativos = dados_completos[dados_completos['Status'] == "🔴 Aberto"]
    # Aqui a correção: ele busca os dois formatos de data para garantir a limpeza
    resolvidos_hoje = dados_completos[(dados_completos['Status'] == "🟢 Finalizado") & 
                                     ((dados_completos['Data'] == hoje_br) | (dados_completos['Data'] == hoje_usa))]

    c1, c2, c3 = st.columns(3)
    c1.metric("🔴 PARADAS AGORA", len(ativos))
    c2.metric("🟢 RESOLVIDOS HOJE", len(resolvidos_hoje))
    media_tempo = resolvidos_hoje['Minutos'].mean() if not resolvidos_hoje.empty else 0.0
    c3.metric("⏱️ MÉDIA (MIN)", f"{media_tempo:.1f}")
    
    with st.expander("🗑️ Opções de Limpeza"):
        # Checkbox que sempre começa falso
        confirma_hoje = st.checkbox("Confirmar: Apagar todos os registros de hoje?", value=False, key="reset_check")
        if st.button("ZERAR CONTRETAGEM DE HOJE"):
            if confirma_hoje:
                # Remove TUDO que for data de hoje (nos dois formatos possíveis)
                df_restante = dados_completos[~((dados_completos['Data'] == hoje_br) | (dados_completos['Data'] == hoje_usa))]
                df_restante.to_csv(DB_FILE, index=False)
                st.success("Dados de hoje limpos com sucesso!")
                st.rerun() # O Rerun aqui é obrigatório para sumir da tela
            else:
                st.error("Marque a confirmação para habilitar a limpeza.")

    st.divider()
    if not ativos.empty:
        st.markdown('<div style="background-color: #ff4b4b; padding: 10px; border-radius: 5px; text-align: center; color: white; font-weight: bold;">⚠️ CHAMADOS EM ABERTO</div>', unsafe_allow_html=True)
        for i, row in ativos.iterrows():
            with st.expander(f"🚨 {row['Célula']} - {row['Motivo']}", expanded=True):
                st.write(f"**Desc:** {row['Descrição']}")
                acao = st.text_input("O que foi feito?", key=f"acao_{row['ID']}")
                if st.button(f"Finalizar {row['ID']}", key=f"f_{row['ID']}"):
                    if acao:
                        # Lógica de finalizar (simplificada aqui para o post)
                        df_f = carregar_dados()
                        idx = df_f[df_f['ID'] == row['ID']].index
                        df_f.at[idx[0], 'Status'] = "🟢 Finalizado"
                        df_f.at[idx[0], 'Fim'] = get_brasil_time().strftime("%H:%M:%S")
                        df_f.at[idx[0], 'Ação'] = acao
                        df_f.to_csv(DB_FILE, index=False)
                        st.rerun()
    
    st.subheader("Histórico Recente")
    st.dataframe(dados_completos.sort_values(by="ID", ascending=False), 
                 use_container_width=True, hide_index=True,
                 column_config={"ID": st.column_config.Column(width="small"), "Célula": st.column_config.Column(width="small")})

# --- ABA 1: OPERADOR ---
with aba_op:
    # (Mantive a lógica anterior de chamado por célula...)
    sel_ups = st.selectbox("Célula", ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"])
    if ativos[ativos['Célula'] == sel_ups].empty:
        m_op = st.selectbox("Motivo", LISTA_MOTIVOS)
        d_op = st.text_area("Descrição")
        if st.button("🔔 CHAMAR"):
            if d_op:
                salvar_chamado = pd.concat([dados_completos, pd.DataFrame([{
                    "ID": len(dados_completos)+1, "Célula": sel_ups, "Motivo": m_op, "Descrição": d_op,
                    "Início": get_brasil_time().strftime("%H:%M:%S"), "Fim": "-", "Status": "🔴 Aberto",
                    "Data": hoje_br, "Ação": "-", "Minutos": 0.0
                }])], ignore_index=True).to_csv(DB_FILE, index=False)
                st.rerun()
    else:
        st.warning(f"Aguardando Assistente para {sel_ups}")

# --- ABA 3: INDICADORES ---
with aba_ind:
    # Filtro que limpa as datas duplicadas para você
    datas_unicas = sorted(list(set(dados_completos['Data'].unique())), reverse=True)
    sel_data = st.multiselect("Filtrar Datas:", datas_unicas, default=[hoje_br] if hoje_br in datas_unicas else [])
    
    df_ind = dados_completos[dados_completos['Data'].isin(sel_data)] if sel_data else dados_completos
    if not df_ind.empty:
        st.plotly_chart(px.bar(df_ind['Célula'].value_counts().reset_index(), x='index', y='Célula', title="Quantidade por UPS"), use_container_width=True)

    st.divider()
    with st.expander("🛠️ ADMINISTRAÇÃO TOTAL"):
        if st.text_input("Senha para APAGAR TUDO", type="password") == SENHA_ADMIN:
            if st.button("LIMPAR TODO O HISTÓRICO"):
                os.remove(DB_FILE)
                st.rerun()
