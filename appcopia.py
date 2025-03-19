import sys
import os

# Adicionar o diretório raiz ao sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

import streamlit as st
import apps.cadastros as cadastros
import apps.manutencoes as manutencoes
import apps.relatorios as relatorios
import apps.configuracoes as configuracoes
import pandas as pd
import plotly.express as px
from sqlalchemy.sql import func
from database import Session, Veiculo, Manutencao, Acessorio
from datetime import datetime, timedelta, date

# Inicializar a sessão com try-except
try:
    session = Session()
except Exception as e:
    st.error(f"Erro ao conectar ao banco de dados: {e}")
    session = None

st.set_page_config(page_title="Gestão de Manutenção", layout="wide")

st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2840/2840529.png", width=80)
st.sidebar.title("🚗 Gestão de Manutenção")
st.sidebar.markdown("---")

menu_options = ["Dashboard", "Cadastros", "Manutenções", "Relatórios", "Configurações"]
menu_principal = st.sidebar.radio("📌 **Selecione**:", menu_options, format_func=lambda x: f"🔹 {x}", label_visibility="collapsed")

st.sidebar.markdown("""
<style>
.stRadio > label > div {
    background-color: transparent !important;
    padding: 15px 20px !important;
    border-radius: 8px;
    margin: 8px 0;
    font-size: 20px !important;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
}
.stRadio > label > div:hover {
    background-color: #f0f0f0 !important;
    transform: scale(1.03);
}
.stRadio > [type="radio"]:checked + label > div {
    background-color: #e0e0e0 !important;
    font-weight: bold;
    position: relative;
}
.stRadio > [type="radio"]:checked + label > div::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    height: 100%;
    width: 5px;
    background-color: #4CAF50;
    border-radius: 8px 0 0 8px;
}
.stRadio > label > div > p {
    margin: 0 !important;
    padding-left: 10px !important;
}
</style>
""", unsafe_allow_html=True)

def formatar_valor_ptbr(valor):
    return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_valor_monetario(valor):
    valor_formatado = f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {valor_formatado}"

def adicionar_emoji_status(status):
    emoji_map = {"pendente": "⏳", "saudavel": "✅", "alerta": "⚠️", "vencido": "⏰", "concluído": "✔️", "cancelado": "❌"}
    return f"{emoji_map.get(status.lower(), '')} {status}"

def adicionar_emoji_tipo(tipo):
    emoji_map = {"Preventiva": "🛡️", "Corretiva": "🔧"}
    return f"{emoji_map.get(tipo, '')} {tipo}"

def obter_dados_manutencoes(filtro_status=None, session_instance=None):
    if not session_instance:
        return pd.DataFrame()
    try:
        manutencoes = session_instance.query(Manutencao).filter(Manutencao.tem_vencimento == True).all()
        if not manutencoes:
            return pd.DataFrame()
        dados_manutencoes = []
        hoje = datetime.now().date()
        for m in manutencoes:
            veiculo = session_instance.query(Veiculo).filter_by(id=m.veiculo_id).first()
            veiculo_nome = f"{veiculo.codigo} - {veiculo.placa} ({veiculo.modelo})" if veiculo else "Desconhecido"
            hodometro_atual = veiculo.hodometro_atual if veiculo and hasattr(veiculo, 'hodometro_atual') else m.hodometro_manutencao

            vencida = False
            alerta = False
            concluida = m.data_realizacao is not None
            motivo = ""
            if m.tem_vencimento and not concluida:
                if m.data_vencimento:
                    dias_restantes = (m.data_vencimento - hoje).days
                    if dias_restantes < 0:
                        vencida = True
                        motivo = f"Vencida por data ({m.data_vencimento})"
                    elif dias_restantes <= 30:
                        alerta = True
                        motivo = f"Alerta por data ({dias_restantes} dias restantes)"
                if m.km_vencimento and hodometro_atual > m.km_vencimento:
                    vencida = True
                    motivo = f"Vencida por KM ({hodometro_atual} > {m.km_vencimento})"
                elif m.km_vencimento and (m.km_vencimento - hodometro_atual) <= 1000:
                    alerta = True
                    motivo = f"Alerta por KM ({m.km_vencimento - hodometro_atual} KM restantes)"
            status = "Concluído" if concluida else "Vencida" if vencida else "Alerta" if alerta else "Saudável"
            dados_manutencoes.append({
                "ID": m.id, "Veículo": veiculo_nome, "Categoria": m.categoria, "Responsável": m.responsavel,
                "Oficina": m.oficina, "Tipo": adicionar_emoji_tipo(m.tipo), "KM Aviso": m.km_aviso,
                "KM Aviso (km)": f"{formatar_valor_ptbr(m.km_aviso)} km", "Data Manutenção": m.data_manutencao,
                "Hodômetro": m.hodometro_manutencao, "Hodômetro (km)": f"{formatar_valor_ptbr(m.hodometro_manutencao)} km",
                "Valor (R$)": m.valor_manutencao, "Valor Formatado (R$)": formatar_valor_monetario(m.valor_manutencao),
                "KM Vencimento": m.km_vencimento, "KM Vencimento (km)": f"{formatar_valor_ptbr(m.km_vencimento)} km",
                "Descrição": m.descricao, "Status": status, "Data Realização": m.data_realizacao,
                "Motivo": motivo
            })
        df = pd.DataFrame(dados_manutencoes)
        if filtro_status:
            df = df[df["Status"].isin(filtro_status)]
        return df
    except Exception as e:
        st.error(f"Erro ao obter dados de manutenções: {e}")
        return pd.DataFrame()

def obter_dados_acessorios(filtro_status=None, session_instance=None):
    if not session_instance:
        return pd.DataFrame()
    try:
        acessorios = session_instance.query(Acessorio).filter(Acessorio.tem_vencimento == True).all()
        if not acessorios:
            return pd.DataFrame()
        dados_acessorios = []
        hoje = datetime.now().date()
        for a in acessorios:
            veiculo = session_instance.query(Veiculo).filter_by(id=a.veiculo_id).first()
            veiculo_nome = f"{veiculo.codigo} - {veiculo.placa} ({veiculo.modelo})" if veiculo else "Desconhecido"
            hodometro_atual = veiculo.hodometro_atual if veiculo and hasattr(veiculo, 'hodometro_atual') else a.km_instalacao

            vencido = False
            alerta = False
            motivo = ""
            if a.tem_vencimento:
                if a.data_vencimento:
                    dias_restantes = (a.data_vencimento - hoje).days
                    if dias_restantes < 0:
                        vencido = True
                        motivo = f"Vencido por data ({a.data_vencimento})"
                    elif dias_restantes <= 30:
                        alerta = True
                        motivo = f"Alerta por data ({dias_restantes} dias restantes)"
                if a.km_vencimento and hodometro_atual > a.km_vencimento:
                    vencido = True
                    motivo = f"Vencido por KM ({hodometro_atual} > {a.km_vencimento})"
                elif a.km_vencimento and (a.km_vencimento - hodometro_atual) <= 1000:
                    alerta = True
                    motivo = f"Alerta por KM ({a.km_vencimento - hodometro_atual} KM restantes)"
            status = "Vencida" if vencido else "Alerta" if alerta else "Saudável"
            dados_acessorios.append({
                "ID": a.id, "Veículo": veiculo_nome, "Nome": a.nome, "KM Instalação": a.km_instalacao,
                "KM Instalação (km)": f"{formatar_valor_ptbr(a.km_instalacao)} km",
                "KM Vencimento": a.km_vencimento, "KM Vencimento (km)": f"{formatar_valor_ptbr(a.km_vencimento)} km" if a.km_vencimento else "N/A",
                "Data Instalação": a.data_instalacao, "Data Vencimento": a.data_vencimento if a.data_vencimento else "N/A",
                "Status": status, "Descrição": a.descricao, "Motivo": motivo
            })
        df = pd.DataFrame(dados_acessorios)
        if filtro_status:
            df = df[df["Status"].isin(filtro_status)]
        return df
    except Exception as e:
        st.error(f"Erro ao obter dados de acessórios: {e}")
        return pd.DataFrame()

if menu_principal == "Dashboard":
    st.title("📊 **Painel de Controle**")
    if not session:
        st.error("Não foi possível carregar o Dashboard devido a um erro na conexão com o banco de dados.")
    else:
        try:
            df_manutencoes = obter_dados_manutencoes(session_instance=session)
            total_manutencoes = len(df_manutencoes)
            manutencoes_saudaveis = len(df_manutencoes[df_manutencoes["Status"] == "Saudável"])
            manutencoes_alerta = len(df_manutencoes[df_manutencoes["Status"] == "Alerta"])
            manutencoes_vencidas = len(df_manutencoes[df_manutencoes["Status"] == "Vencida"])
            manutencoes_concluidas = len(df_manutencoes[df_manutencoes["Status"] == "Concluído"])
            valor_total = df_manutencoes["Valor (R$)"].sum() or 0
        except Exception as e:
            st.error(f"Erro ao buscar dados principais: {e}")
            total_manutencoes, manutencoes_saudaveis, manutencoes_alerta, manutencoes_vencidas, manutencoes_concluidas, valor_total = 0, 0, 0, 0, 0, 0

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f"""<div style="background-color: #4CAF50; color: white; padding: 15px; border-radius: 10px; text-align: center;"><h5 style="margin: 0;">📋 Total</h5><p style="font-size: 24px; margin: 0;">{total_manutencoes}</p><p style="font-size: 14px; margin: 0;">Manutenções cadastradas</p></div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div style="background-color: #2196F3; color: white; padding: 15px; border-radius: 10px; text-align: center;"><h5 style="margin: 0;">✅ Saudáveis</h5><p style="font-size: 24px; margin: 0;">{manutencoes_saudaveis}</p><p style="font-size: 14px; margin: 0;">(Em dia)</p></div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div style="background-color: #FFC107; color: white; padding: 15px; border-radius: 10px; text-align: center;"><h5 style="margin: 0;">⚠️ Alerta</h5><p style="font-size: 24px; margin: 0;"><a href='?menu=Dashboard&filtro_status=Alerta' style='color: white; text-decoration: underline;' target='_self'>{manutencoes_alerta}</a></p><p style="font-size: 14px; margin: 0;">(Próximas)</p></div>""", unsafe_allow_html=True)
        with col4:
            st.markdown(f"""<div style="background-color: #FF5722; color: white; padding: 15px; border-radius: 10px; text-align: center;"><h5 style="margin: 0;">⏰ Vencidas</h5><p style="font-size: 24px; margin: 0;"><a href='?menu=Dashboard&filtro_status=Vencida' style='color: white; text-decoration: underline;' target='_self'>{manutencoes_vencidas}</a></p><p style="font-size: 14px; margin: 0;">(Atrasadas)</p></div>""", unsafe_allow_html=True)
        with col5:
            st.markdown(f"""<div style="background-color: #9E9E9E; color: white; padding: 15px; border-radius: 10px; text-align: center;"><h5 style="margin: 0;">✔️ Concluídas</h5><p style="font-size: 24px; margin: 0;"><a href='?menu=Dashboard&filtro_status=Concluído' style='color: white; text-decoration: underline;' target='_self'>{manutencoes_concluidas}</a></p><p style="font-size: 14px; margin: 0;">(Finalizadas)</p></div>""", unsafe_allow_html=True)

        # Controle da exibição da tabela com base no filtro
        filtro_status = st.query_params.get("filtro_status", None)
        if filtro_status in ["Vencida", "Alerta", "Concluído"]:
            if 'show_table' not in st.session_state:
                st.session_state.show_table = False
            if st.session_state.show_table or st.button(f"Mostrar Tabela de {filtro_status}"):
                st.session_state.show_table = True
                st.markdown(f"### 📋 **Manutenções {filtro_status}**")
                df = obter_dados_manutencoes(filtro_status=[filtro_status], session_instance=session)
                if df.empty:
                    st.warning(f"⚠️ Nenhuma manutenção encontrada no estado '{filtro_status}'!")
                else:
                    # Ajustar colunas por status
                    if filtro_status == "Vencida":
                        df_display = df[["ID", "Veículo", "Categoria", "Tipo", "KM Vencimento (km)", "Data Vencimento", "Status", "Motivo"]]
                    elif filtro_status == "Alerta":
                        df_display = df[["ID", "Veículo", "Categoria", "Tipo", "KM Vencimento (km)", "Data Vencimento", "Status", "Motivo"]]
                    elif filtro_status == "Concluído":
                        df_display = df[["ID", "Veículo", "Categoria", "Tipo", "Data Manutenção", "Data Realização", "Valor Formatado (R$)", "Status"]]
                    df_display["Status"] = df_display["Status"].apply(adicionar_emoji_status)
                    st.dataframe(df_display, use_container_width=True, height=300)
                    total_manutencoes = len(df)
                    total_valor = df["Valor (R$)"].sum()
                    total_valor_formatado = formatar_valor_monetario(total_valor)
                    st.markdown(f"""<div style="background-color: #2e7d32; padding: 15px; border-radius: 5px; color: white; font-size: 18px;">Total de Manutenções: {total_manutencoes}<br>Valor Total (R$): {total_valor_formatado}</div>""", unsafe_allow_html=True)
            elif st.button("Ocultar Tabela"):
                st.session_state.show_table = False

        st.markdown("### 📈 **Distribuição de Manutenções**")
        try:
            df_status = obter_dados_manutencoes(session_instance=session)
            if not df_status.empty:
                fig_status = px.pie(df_status, names="Status", values="ID", title="📊 Status das Manutenções", hole=0.3, color_discrete_sequence=['#4CAF50', '#FFC107', '#FF5722', '#9E9E9E'])
                fig_status.update_layout(height=400)
                st.plotly_chart(fig_status, use_container_width=True)
            else:
                st.warning("⚠️ Nenhum dado disponível para Distribuição por Status.")
        except Exception as e:
            st.error(f"Erro ao carregar gráfico de status: {e}")

        col5, col6 = st.columns(2)
        try:
            df_manutencao = pd.read_sql(
                session.query(Manutencao.categoria, func.count().label('total'))
                .filter(Manutencao.tem_vencimento == 1)
                .group_by(Manutencao.categoria)
                .statement,
                session.bind
            )
            if not df_manutencao.empty:
                fig_categoria = px.pie(df_manutencao, names="categoria", values="total", title="🛠 Manutenções por Categoria", hole=0.3)
                fig_categoria.update_layout(height=400)
                with col5: st.plotly_chart(fig_categoria, use_container_width=True)
            else:
                with col5: st.warning("⚠️ Nenhum dado disponível para Manutenções por Categoria.")
        except Exception as e:
            with col5: st.error(f"Erro ao carregar gráfico: {e}")

        try:
            df_tipo = pd.read_sql(
                session.query(Manutencao.tipo, func.count().label('total'))
                .filter(Manutencao.tem_vencimento == 1)
                .group_by(Manutencao.tipo)
                .statement,
                session.bind
            )
            if not df_tipo.empty:
                fig_tipo = px.pie(df_tipo, names="tipo", values="total", title="🔧 Tipo de Manutenção", hole=0.3)
                fig_tipo.update_layout(height=400)
                with col6: st.plotly_chart(fig_tipo, use_container_width=True)
            else:
                with col6: st.warning("⚠️ Nenhum dado disponível para Tipo de Manutenção.")
        except Exception as e:
            with col6: st.error(f"Erro ao carregar gráfico: {e}")

        st.markdown("### 🚙 **Próximos Veículos a Vencer KM de Manutenção**")
        try:
            if session:
                df_veiculos = obter_dados_manutencoes(filtro_status=["Alerta", "Vencida"], session_instance=session)
                if not df_veiculos.empty:
                    df_veiculos = df_veiculos[["Veículo", "Hodômetro (km)", "KM Vencimento (km)", "Tipo", "Status", "Motivo"]]
                    df_veiculos = df_veiculos.sort_values(by="Status", ascending=False)[:5]
                    st.dataframe(df_veiculos, use_container_width=True, height=200)
                else:
                    st.warning("⚠️ Nenhum veículo pendente próximo de vencer manutenção.")
        except Exception as e:
            st.error(f"Erro ao buscar veículos próximos de manutenção: {e}")

        st.markdown("### 🛠 **Próximos Acessórios a Vencer**")
        try:
            if session:
                df_acessorios = obter_dados_acessorios(filtro_status=["Alerta", "Vencida"], session_instance=session)
                if not df_acessorios.empty:
                    df_acessorios = df_acessorios[["Veículo", "Nome", "Hodômetro (km)", "KM Vencimento (km)", "Data Vencimento", "Status", "Motivo"]]
                    df_acessorios = df_acessorios.sort_values(by="Status", ascending=False)[:5]
                    st.dataframe(df_acessorios, use_container_width=True, height=200)
                else:
                    st.warning("⚠️ Nenhum acessório pendente próximo de vencer.")
        except Exception as e:
            st.error(f"Erro ao buscar acessórios próximos de vencimento: {e}")

        st.markdown("### 📆 **Gastos nos Últimos 15 Dias**")
        try:
            if session:
                data_limite = datetime.today() - timedelta(days=15)
                df_gastos = pd.read_sql(
                    session.query(
                        func.date(Manutencao.data_manutencao).label('data'),
                        func.sum(Manutencao.valor_manutencao).label('total')
                    )
                    .filter(Manutencao.data_manutencao >= data_limite, Manutencao.tem_vencimento == 1)
                    .group_by(func.date(Manutencao.data_manutencao))
                    .order_by(func.date(Manutencao.data_manutencao))
                    .statement,
                    session.bind
                )
                if not df_gastos.empty:
                    df_gastos["data"] = pd.to_datetime(df_gastos["data"])
                    fig_gastos = px.line(df_gastos, x="data", y="total", title="📉 Gastos com Manutenção nos Últimos 15 Dias", markers=True)
                    fig_gastos.update_layout(height=300)
                    st.plotly_chart(fig_gastos, use_container_width=True)
                else:
                    st.warning("⚠️ Nenhum gasto registrado nos últimos 15 dias.")
        except Exception as e:
            st.error(f"Erro ao carregar gráfico: {e}")

        st.markdown("### 📊 **Manutenções por Mês**")
        try:
            df_manutencoes = obter_dados_manutencoes(session_instance=session)
            if not df_manutencoes.empty:
                df_manutencoes['Mês'] = pd.to_datetime(df_manutencoes['Data Manutenção']).dt.strftime('%Y-%m')
                fig_barras = px.bar(df_manutencoes, x='Mês', title='📊 Manutenções por Mês', color='Status', barmode='group', color_discrete_sequence=['#4CAF50', '#FFC107', '#FF5722', '#9E9E9E'])
                fig_barras.update_layout(height=400)
                st.plotly_chart(fig_barras, use_container_width=True)
            else:
                st.warning("⚠️ Nenhum dado disponível para Manutenções por Mês.")
        except Exception as e:
            st.error(f"Erro ao carregar gráfico de barras: {e}")

        st.markdown("### 📈 **Valor Total por Mês**")
        try:
            df_manutencoes = obter_dados_manutencoes(session_instance=session)
            if not df_manutencoes.empty:
                df_manutencoes['Mês'] = pd.to_datetime(df_manutencoes['Data Manutenção']).dt.strftime('%Y-%m')
                fig_linhas = px.line(df_manutencoes.groupby('Mês')['Valor (R$)'].sum().reset_index(), x='Mês', y='Valor (R$)', title='📈 Valor Total por Mês')
                fig_linhas.update_layout(height=400)
                st.plotly_chart(fig_linhas, use_container_width=True)
            else:
                st.warning("⚠️ Nenhum dado disponível para Valor Total por Mês.")
        except Exception as e:
            st.error(f"Erro ao carregar gráfico de linhas: {e}")

elif menu_principal == "Cadastros":
    cadastros.exibir_cadastros()

elif menu_principal == "Manutenções":
    manutencoes.exibir_manutencoes()

elif menu_principal == "Relatórios":
    relatorios.exibir_relatorios()

elif menu_principal == "Configurações":
    configuracoes.exibir_configuracoes()