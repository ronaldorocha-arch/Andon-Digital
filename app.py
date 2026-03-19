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
    # Garante o horário de Brasília (UTC-3)
    return datetime.utcnow() - timedelta(hours=3)

# --- BANCO DE DADOS ---
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"]).to_csv(DB_FILE, index=False)

def carregar_dados():
    try:
        # Lendo o CSV e garantindo que os IDs sejam inteiros
        df = pd.read_csv(DB_FILE)
        if "Minutos" not in df.columns: 
            df["Minutos"] = 0.0
            df.to_csv(DB_FILE, index=False)
        return df
    except:
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"])

def salvar_chamado(celula, motivo, desc):
    df = carregar_dados()
    agora = get_brasil_time()
    novo = {
        "ID": len(df) + 1, "Célula": celula, "Motivo": motivo, "Descrição": desc,
        "Início": agora.strftime("%H:%M:%S"), "Fim": "-", "Status": "🔴 Aberto",
        "Data": agora.strftime("%d/%m/%Y"), # Formato BR
        "Ação": "-", "Minutos": 0.0
    }
    # Usando pd.concat para evitar alertas de depreciação de append
    pd.concat([df, pd.DataFrame([novo])], ignore_index=True).to_csv(DB_FILE, index=False)

def finalizar_chamado(id_chamado, acao_desc):
    df = carregar_dados()
    idx = df[df['ID'] == id_chamado].index
    if not idx.empty:
        agora = get_brasil_time()
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
    @keyframes piscar { 0% { background-color: #ff4b4b; } 50% { background-color: #9e0000; } 100% { background-color: #ff4b4b; } }
    .piscante { animation: piscar 1s infinite; padding: 15px; border-radius: 10px; color: white; text-align: center; font-weight: bold; margin-bottom: 15px; }
    div.stButton > button:first-child { width: 100%; height: 50px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE DADOS ---
dados_completos = carregar_dados()
hoje_br = get_brasil_time().strftime("%d/%m/%Y")
ativos = dados_completos[dados_completos['Status'] == "🔴 Aberto"]
resolvidos_hoje = dados_completos[(dados_completos['Status'] == "🟢 Finalizado") & (dados_completos['Data'] == hoje_br)]

st.title("🚨 Andon Digital - Tecnologia de Processos")
aba_op, aba_as, aba_ind = st.tabs(["📲 Terminal Operador", "💻 Painel Assistente", "📊 Indicadores"])

# --- ABA 1: OPERADOR ---
with aba_op:
    st.subheader("Registrar Nova Parada")
    col_a, col_b = st.columns(2)
    lista_ups = ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"]
    with col_a: sel_ups = st.selectbox("Sua Célula", lista_ups)
    with col_b: sel_motivo = st.selectbox("Motivo", LISTA_MOTIVOS)
    
    desc = st.text_area("O que aconteceu?", key="desc_op", placeholder="Ex: Falta de dissipador...")
    
    # Verifica se ESTA Célula específica já tem um chamado aberto
    chamado_esta_celula = ativos[ativos['Célula'] == sel_ups]

    if not chamado_esta_celula.empty:
        # Se houver chamado aberto para esta UPS, mostra o aviso gigante
        st.markdown(f'<div class="piscante"><h1>⏳ AGUARDANDO ASSISTENTE...</h1><p style="color: white; font-size: 20px;">Célula {sel_ups} parada por: {chamado_esta_celula.iloc[0]["Motivo"]}</p></div><br>', unsafe_allow_html=True)
    else:
        # Se não houver chamado, mostra o botão de chamar
        if st.button("🔔 CHAMAR ASSISTENTE", type="primary"):
            if desc:
                salvar_chamado(sel_ups, sel_motivo, desc)
                st.rerun() # Atualiza a tela imediatamente para mostrar o estado piscante

# --- ABA 2: ASSISTENTE ---
with aba_as:
    # SEMÁFORO (KPIs)
    c1, c2, c3 = st.columns(3)
    c1.metric("🔴 PARADAS AGORA", len(ativos))
    c2.metric("🟢 RESOLVIDOS HOJE", len(resolvidos_hoje))
    media_tempo = resolvidos_hoje['Minutos'].mean() if not resolvidos_hoje.empty else 0.0
    c3.metric("⏱️ LEAD TIME MÉDIO (MIN)", f"{media_tempo:.1f}")
    
    if not ativos.empty:
        # Título piscante se houver chamados
        st.markdown('<div class="piscante"><h2>⚠️ ATENÇÃO: HÁ CHAMADOS EM ABERTO!</h2></div>', unsafe_allow_html=True)
        
        for i, row in ativos.iterrows():
            with st.expander(f"🔴 {row['Célula']} - {row['Motivo']} ({row['Início']})", expanded=True):
                st.write(f"**Problema:** {row['Descrição']}")
                # Campo obrigatório para fechar o PDCA
                txt_acao = st.text_input(f"O que foi feito? (ID {row['ID']})", key=f"ac_{row['ID']}")
                if st.button(f"✅ Finalizar {row['ID']}", key=f"bt_{row['ID']}"):
                    if txt_acao:
                        finalizar_chamado(row['ID'], txt_acao)
                        st.rerun() # Atualiza para remover o chamado finalizado
                    else:
                        st.error("Por favor, descreva a ação tomada.")
    else:
        st.info("✅ Nenhuma pendência no momento.")
    
    st.divider()
    
    # --- NOVIDADE: OPÇÕES DE LIMPEZA COM RESET COMPLETO ---
    with st.expander("🗑️ Opções de Limpeza de Dados"):
        confirma = st.checkbox("Eu quero zerar os chamados de hoje (Sincronizar com Turno).")
        if st.button("Zerar Contagem de Hoje"):
            if confirma:
                # Remove apenas os registros da data de hoje (Brasil)
                df_limpo = dados_completos[dados_completos['Data'] != hoje_br]
                df_limpo.to_csv(DB_FILE, index=False)
                
                # CORREÇÃO FAIXA VERMELHA: Força o recarregamento total do script
                # Isso limpa a "memória antiga" do Pandas no Streamlit
                st.success("Dados de hoje foram removidos com sucesso!")
                st.rerun() 
            else:
                st.error("Você precisa marcar a caixa de confirmação acima.")

    st.subheader("Histórico de Registros")
    # Exibir ID e Célula compactos
    st.dataframe(dados_completos.sort_values(by="ID", ascending=False), 
                 use_container_width=True, hide_index=True,
                 column_config={
                     "ID": st.column_config.Column(width="small"),
                     "Célula": st.column_config.Column(width="small")
                 })

# --- ABA 3: INDICADORES ---
with aba_ind:
    if not dados_completos.empty:
        hoje = get_brasil_time().strftime("%d/%m/%Y")
        datas_lista = sorted(dados_completos['Data'].unique(), reverse=True)
        
        # Filtros
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            data_sel = st.multiselect("Filtro de Datas:", datas_lista, default=[hoje] if hoje in datas_lista else [])
        with c_f2:
            ups_sel = st.multiselect("Filtro de Células:", sorted(dados_completos['Célula'].unique()))
        
        # Lógica de filtro combinada
        df_grafico = dados_completos.copy()
        if data_sel:
            df_grafico = df_grafico[df_grafico['Data'].isin(data_sel)]
        if ups_sel:
            df_grafico = df_grafico[df_grafico['Célula'].isin(ups_sel)]

        if not df_grafico.empty:
            st.divider()
            c1, c2 = st.columns(2)
            # Gráfico Inteligente: Se filtrar uma só, mostra motivos. Se várias, compara UPS.
            with c1:
                title = f'Motivos: {ups_sel[0]}' if len(ups_sel) == 1 else 'Chamados por UPS'
                x_val = 'Motivo' if len(ups_sel) == 1 else 'Célula'
                fig1 = px.bar(df_grafico, x=x_val, title=title, color_discrete_sequence=['#ff4b4b'])
                st.plotly_chart(fig1, use_container_width=True)
            with c2:
                # Pareto de motivos
                st.plotly_chart(px.pie(df_grafico, names='Motivo', title='Distribuição Geral de Motivos', hole=0.4), use_container_width=True)
        
        st.divider()
        with st.expander("🛠️ Administração do Sistema"):
            st.warning("⚠️ Limpar o histórico apagará todos os registros permanentemente.")
            if st.text_input("Senha Admin", type="password") == SENHA_ADMIN:
                if st.button("🗑️ APAGAR TODO O HISTÓRICO"):
                    # Deleta o arquivo físico para zerar tudo
                    if os.path.exists(DB_FILE): os.remove(DB_FILE)
                    st.success("Histórico reiniciado!")
                    st.rerun()
