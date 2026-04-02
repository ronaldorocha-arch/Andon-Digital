import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÃO ---
DB_FILE = "registro_paradas.csv"

def get_br_time():
    # Ajuste para o fuso horário de Brasília
    return datetime.utcnow() - timedelta(hours=3)

def checar_ativos_rapido():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            return not df[df['Status'] == "🔴 Aberto"].empty
        except: return False
    return False

tem_parada = checar_ativos_rapido()

st.set_page_config(
    page_title="🚨 CHAMADO! - Andon NHS" if tem_parada else "Andon Digital - NHS",
    page_icon="🚨",
    layout="wide"
)

# Atualiza a página a cada 5 segundos
st_autorefresh(interval=5000, key="datarefresh")

if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'pagina_ativa' not in st.session_state:
    st.session_state.pagina_ativa = "📲 Terminal Operador"

SENHA = "12345"

# --- 2. ESTILO CSS E FUNÇÕES JAVASCRIPT (VIBRAÇÃO) ---
st.markdown("""
    <style>
    @keyframes piscar { 0% { background-color: #ff4b4b; } 50% { background-color: #7d0000; } 100% { background-color: #ff4b4b; } }
    .alerta-piscante { animation: piscar 1s infinite; padding: 20px; border-radius: 10px; color: white !important; text-align: center; margin-bottom: 20px; font-weight: 400 !important; }
    [data-testid="stMetricValue"] { color: #000000 !important; font-size: 38px; font-weight: 400 !important; }
    div.stButton > button:first-child { width: 100%; height: 50px; }
    </style>
    """, unsafe_allow_html=True)

def disparar_alerta_fisico():
    """Injeta JavaScript para fazer o tablet vibrar e emitir um bipe"""
    st.components.v1.html(
        """
        <script>
        // 1. Função de Vibração (Padrão: Vibra 500ms, pausa 200, vibra 500)
        if (window.navigator && window.navigator.vibrate) {
            window.navigator.vibrate([500, 200, 500]);
        }
        
        // 2. Função de Áudio (Bipe de 880Hz)
        var context = new (window.AudioContext || window.webkitAudioContext)();
        var osc = context.createOscillator();
        var gain = context.createGain();
        osc.connect(gain);
        gain.connect(context.destination);
        osc.frequency.setValueAtTime(880, context.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.5);
        osc.start();
        osc.stop(context.currentTime + 0.5);
        </script>
        """,
        height=0,
    )

# --- 3. FUNÇÕES DE DADOS ---
def carregar_dados():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"])
    try:
        df = pd.read_csv(DB_FILE)
        # Garante que a coluna Data seja tratada como string padronizada
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce').dt.strftime('%d/%m/%Y')
        return df.dropna(subset=['ID'])
    except:
        return pd.DataFrame(columns=["ID", "Célula", "Motivo", "Descrição", "Início", "Fim", "Status", "Data", "Ação", "Minutos"])

dados = carregar_dados()
hoje = get_br_time().strftime("%d/%m/%Y")

# LÓGICA CORRIGIDA: Se houver erro de data no CSV, ele tenta pegar pelo menos o status
ativos = dados[dados['Status'] == "🔴 Aberto"]
# Aqui filtramos por status finalizado e data de hoje
resolvidos_hoje = dados[(dados['Status'] == "🟢 Finalizado") & (dados['Data'] == hoje)]

# Se houver paradas ativas, dispara o alerta físico (Vibração/Som)
if not ativos.empty:
    disparar_alerta_fisico()

# --- 4. MENU DE NAVEGAÇÃO ---
menu = ["📲 Terminal Operador", "💻 Painel Assistente", "📊 Indicadores", "📂 Relatórios"]
escolha = st.radio("Selecione o Painel:", menu, horizontal=True, key="navegacao_principal")
st.session_state.pagina_ativa = escolha
st.divider()

# --- 5. LÓGICA DAS PÁGINAS ---

if st.session_state.pagina_ativa == "📲 Terminal Operador":
    st.subheader("Registrar Nova Parada")
    c1, c2 = st.columns(2)
    ups = ["UPS - 1", "UPS - 2", "UPS - 3", "UPS - 4", "UPS - 6", "UPS - 7", "UPS - 8", "ACS - 01"]
    sel_ups = c1.selectbox("Célula", ups)
    aberto = ativos[ativos['Célula'] == sel_ups]
    
    if aberto.empty:
        lista_problemas = ["Falta de Matéria-prima", "Qualidade", "Composer", "Abastecimento", "Processo", "Manutenção", "Outros"]
        motivo_selecionado = c2.selectbox("Qual o problema?", lista_problemas)
        obs_op = st.text_input("Observação Adicional (Opcional):")
        
        if st.button("🔔 ENVIAR CHAMADO", type="primary"):
            final_desc = f"{motivo_selecionado} - {obs_op}" if obs_op else motivo_selecionado
            nid = int(dados['ID'].max() + 1) if not dados.empty else 1
            
            novo = pd.DataFrame([{
                "ID": nid, "Célula": sel_ups, "Motivo": motivo_selecionado, 
                "Descrição": final_desc, "Início": get_br_time().strftime("%H:%M:%S"), 
                "Fim": "-", "Status": "🔴 Aberto", "Data": hoje, "Ação": "-", "Minutos": 0.0
            }])
            pd.concat([dados, novo], ignore_index=True).to_csv(DB_FILE, index=False)
            st.rerun()
    else:
        st.markdown(f'<div class="alerta-piscante"><h1>⏳ AGUARDANDO ASSISTENTE...</h1><p>Célula: {sel_ups} | {aberto.iloc[0]["Descrição"]}</p></div>', unsafe_allow_html=True)

elif st.session_state.pagina_ativa == "💻 Painel Assistente":
    if not st.session_state.logado:
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if senha == SENHA: 
                st.session_state.logado = True
                st.rerun()
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("EM ABERTO", len(ativos))
        m2.metric("RESOLVIDOS HOJE", len(resolvidos_hoje))
        med = resolvidos_hoje['Minutos'].astype(float).mean() if not resolvidos_hoje.empty else 0.0
        m3.metric("TEMPO MÉDIO", f"{med:.1f} min")
        
        st.divider()
        if not ativos.empty:
            for i, r in ativos.iterrows():
                with st.expander(f"🔴 Célula: {r['Célula']} - {r['Início']}", expanded=True):
                    ac = st.text_input("Ação Tomada:", key=f"ac_{r['ID']}")
                    if st.button(f"Concluir #{r['ID']}", key=f"f_{r['ID']}"):
                        df_f = pd.read_csv(DB_FILE)
                        idx = df_f[df_f['ID'] == r['ID']].index
                        ag = get_br_time()
                        h_ini = datetime.strptime(df_f.at[idx[0], 'Início'], "%H:%M:%S")
                        
                        df_f.at[idx[0], 'Fim'] = ag.strftime("%H:%M:%S")
                        df_f.at[idx[0], 'Status'] = "🟢 Finalizado"
                        df_f.at[idx[0], 'Ação'] = ac if ac else "Atendimento Concluído"
                        duracao = (ag - datetime.combine(ag.date(), h_ini.time())).total_seconds() / 60
                        df_f.at[idx[0], 'Minutos'] = round(max(0, duracao), 1)
                        
                        df_f.to_csv(DB_FILE, index=False)
                        st.rerun()
        else:
            st.success("✅ Tudo em ordem!")

elif st.session_state.pagina_ativa == "📊 Indicadores":
    if st.session_state.logado:
        if not dados.empty:
            df_i = dados[dados['Status'] == "🟢 Finalizado"].copy()
            st.plotly_chart(px.bar(df_i['Célula'].value_counts().reset_index(), x='Célula', y='count', title="Chamados por Célula"), use_container_width=True)

elif st.session_state.pagina_ativa == "📂 Relatórios":
    if st.session_state.logado:
        st.dataframe(dados.sort_values(by="ID", ascending=False), use_container_width=True, hide_index=True)
        st.download_button("📥 EXPORTAR CSV", data=dados.to_csv(index=False).encode('utf-8-sig'), file_name=f'Andon_NHS_{hoje}.csv')
