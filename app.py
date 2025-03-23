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
from database import Session, Veiculo, Manutencao, Acessorio, Configuracao, Abastecimento
from datetime import datetime, timedelta, date
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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

# Estilo do menu lateral
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

# Estilo para o botão de sincronização no dashboard
st.markdown("""
<style>
.sync-button-container {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 20px;
    margin-top: 10px;
    padding-right: 20px;
}
.sync-button {
    background-color: #4CAF50 !important;
    color: white !important;
    padding: 10px 20px !important;
    border: none !important;
    border-radius: 5px !important;
    font-size: 16px !important;
    cursor: pointer !important;
    transition: background-color 0.3s ease !important;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
}
.sync-button:hover {
    background-color: #45a049 !important;
}
</style>
""", unsafe_allow_html=True)

def formatar_valor_ptbr(valor):
    return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_valor_monetario(valor):
    valor_formatado = f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {valor_formatado}"

def adicionar_emoji_status(status):
    emoji_map = {
        "concluído": "✅",
        "saudavel": "🟢",
        "alerta": "⚠️",
        "vencido": "⛔",
        "pendente": "⏳",
        "cancelado": "❌"
    }
    return f"{emoji_map.get(status.lower(), '')} {status}"

def adicionar_emoji_tipo(tipo):
    emoji_map = {"Preventiva": "🛡️", "Corretiva": "🔧"}
    return f"{emoji_map.get(tipo, '')} {tipo}"

def obter_configuracao(chave, valor_padrao, session_instance):
    try:
        config = session_instance.query(Configuracao).filter_by(chave=chave).first()
        return config.valor if config else valor_padrao
    except Exception as e:
        st.error(f"❌ Erro ao obter configuração '{chave}': {e}")
        return valor_padrao

def calcular_status(registro, veiculo, km_aviso=1000.0, data_limite_dias=30.0):
    if not registro.tem_vencimento:
        return "concluído", ""
    
    hodometro_atual = veiculo.hodometro_atual if veiculo and veiculo.hodometro_atual is not None else registro.hodometro_manutencao if hasattr(registro, 'hodometro_manutencao') else registro.km_instalacao
    hoje = datetime.now().date()
    
    vencido = False
    alerta = False
    motivo = ""
    
    if registro.data_vencimento:
        dias_restantes = (registro.data_vencimento - hoje).days
        if dias_restantes < 0:
            vencido = True
            motivo = f"Vencido por data ({registro.data_vencimento})"
        elif dias_restantes <= data_limite_dias:
            alerta = True
            motivo = f"Alerta por data ({dias_restantes} dias restantes)"
    
    if registro.km_vencimento and hodometro_atual is not None:
        if hodometro_atual > registro.km_vencimento:
            vencido = True
            motivo = f"Vencido por KM ({hodometro_atual} > {registro.km_vencimento})"
        elif (registro.km_vencimento - hodometro_atual) <= km_aviso:
            alerta = True
            motivo = f"Alerta por KM ({registro.km_vencimento - hodometro_atual} KM restantes)"
    
    status = "vencido" if vencido else "alerta" if alerta else "saudavel"
    return status, motivo

def sincronizar_dados_veiculos(session_instance, write_progress=True):
    try:
        api_url = "http://89.116.214.34:8000/api/abastecimentos/"
        headers = {"Authorization": "Token c6f5a268b3f1bc95c875a8203ad1562f47dcf0ad"}
        params = {"EValidado": "", "veiculo": "", "month": "", "year": "2025", "page": 1, "perPage": 100}

        session_requests = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session_requests.mount("http://", HTTPAdapter(max_retries=retries))
        TIMEOUT = 30

        try:
            test_response = session_requests.get(api_url, headers=headers, params=params, timeout=TIMEOUT)
            test_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Erro ao conectar à API: {e}")

        hodometros_veiculos = {}
        veiculos = session_instance.query(Veiculo).all()
        veiculos_dict = {str(v.codigo): v for v in veiculos}

        # Log: Listar veículos no banco de dados
        st.write("### Veículos no Banco de Dados")
        for v in veiculos:
            st.write(f"Código: {v.codigo}, Placa: {v.placa}, Hodômetro Atual: {v.hodometro_atual}")

        total_registros = 0
        while True:
            try:
                response = session_requests.get(api_url, headers=headers, params=params, timeout=TIMEOUT)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                raise Exception(f"Erro ao buscar dados da API: {e}")

            dados_api = response.json()
            resultados = dados_api.get("results", [])
            total_registros += len(resultados)
            st.write(f"Processados {total_registros} registros até a página {params['page']}")

            for item in resultados:
                codigo = str(item.get("veiculo_detail", {}).get("codigo"))
                hodometro = float(item.get("hodometro", 0.0))

                # Log: Exibir registros dos veículos 166, 121, 120, 115
                if codigo in ["166", "121", "120", "115"]:
                    st.write(f"Veículo {codigo}: Hodômetro = {hodometro}")

                if codigo in hodometros_veiculos:
                    if hodometro > hodometros_veiculos[codigo]["hodometro"]:
                        hodometros_veiculos[codigo] = {"hodometro": hodometro}
                else:
                    hodometros_veiculos[codigo] = {"hodometro": hodometro}

            next_url = dados_api.get("next")
            if not next_url:
                break
            params["page"] += 1

        # Atualizar o hodometro_atual dos veículos
        for codigo, dados in hodometros_veiculos.items():
            hodometro = dados["hodometro"]
            if hodometro <= 0.0:  # Ignorar valores inválidos (apenas menores ou iguais a 0)
                continue
            if codigo in veiculos_dict:
                veiculo = veiculos_dict[codigo]
                veiculo.hodometro_atual = hodometro

        session_instance.commit()
        if write_progress:
            st.success("✅ Sincronização concluída com sucesso!")

    except requests.exceptions.RequestException as e:
        session_instance.rollback()
        raise Exception(f"Erro ao sincronizar dados: {e}")
    except Exception as e:
        session_instance.rollback()
        raise Exception(f"Erro inesperado ao sincronizar dados: {e}")

def obter_dados_manutencoes(filtro_status=None, session_instance=None):
    if not session_instance:
        return pd.DataFrame()
    try:
        km_aviso = float(obter_configuracao("km_aviso", 1000.0, session_instance))
        data_limite_dias = float(obter_configuracao("data_limite_dias", 30.0, session_instance))

        manutencoes = session_instance.query(Manutencao).all()
        if not manutencoes:
            return pd.DataFrame()
        dados_manutencoes = []
        for m in manutencoes:
            veiculo = session_instance.query(Veiculo).filter_by(id=m.veiculo_id).first()
            veiculo_nome = f"{veiculo.codigo} - {veiculo.placa} ({veiculo.modelo})" if veiculo else "Desconhecido"
            hodometro_atual = veiculo.hodometro_atual if veiculo else 0.0

            if not veiculo:
                continue
            if hodometro_atual == 0.0:
                continue

            categoria = getattr(m, 'categoria', 'N/A') if m.categoria else 'N/A'
            responsavel = getattr(m, 'responsavel', 'N/A') if m.responsavel else 'N/A'
            oficina = getattr(m, 'oficina', 'N/A') if m.oficina else 'N/A'

            status, motivo = calcular_status(m, veiculo, km_aviso, data_limite_dias)
            dados_manutencoes.append({
                "ID": m.id,
                "Tipo de Registro": "Manutenção",
                "Veículo": veiculo_nome,
                "Categoria": categoria,
                "Responsável": responsavel,
                "Oficina": oficina,
                "Tipo": adicionar_emoji_tipo(m.tipo) if m.tipo else "N/A",
                "KM Aviso": m.km_aviso,
                "KM Aviso (km)": f"{formatar_valor_ptbr(m.km_aviso)} km" if m.km_aviso else "N/A",
                "Data Manutenção": m.data_manutencao,
                "Hodômetro Atual (km)": f"{formatar_valor_ptbr(hodometro_atual)} km",
                "Valor (R$)": m.valor_manutencao if m.valor_manutencao else 0.0,
                "Valor Formatado (R$)": formatar_valor_monetario(m.valor_manutencao) if m.valor_manutencao else "N/A",
                "KM Vencimento": m.km_vencimento,
                "KM Vencimento (km)": f"{formatar_valor_ptbr(m.km_vencimento)} km" if m.km_vencimento else "N/A",
                "Data Vencimento": m.data_vencimento if m.data_vencimento else "N/A",
                "Descrição": m.descricao,
                "Status": status,
                "Status Raw": status,
                "Data Realização": m.data_realizacao,
                "Motivo": motivo
            })
        df = pd.DataFrame(dados_manutencoes)
        if filtro_status:
            df = df[df["Status Raw"].isin(filtro_status)]
        return df
    except Exception as e:
        st.error(f"Erro ao obter dados de manutenções: {e}")
        return pd.DataFrame()

def obter_dados_acessorios(filtro_status=None, session_instance=None):
    if not session_instance:
        return pd.DataFrame()
    try:
        km_aviso = float(obter_configuracao("km_aviso", 1000.0, session_instance))
        data_limite_dias = float(obter_configuracao("data_limite_dias", 30.0, session_instance))

        acessorios = session_instance.query(Acessorio).all()
        if not acessorios:
            return pd.DataFrame()
        dados_acessorios = []
        for a in acessorios:
            veiculo = session_instance.query(Veiculo).filter_by(id=a.veiculo_id).first()
            veiculo_nome = f"{veiculo.codigo} - {veiculo.placa} ({veiculo.modelo})" if veiculo else "Desconhecido"
            hodometro_atual = veiculo.hodometro_atual if veiculo else a.km_instalacao

            if not veiculo:
                continue
            if hodometro_atual == 0.0:
                continue

            status, motivo = calcular_status(a, veiculo, km_aviso, data_limite_dias)
            dados_acessorios.append({
                "ID": a.id,
                "Tipo de Registro": "Acessório",
                "Veículo": veiculo_nome,
                "Nome": a.nome,
                "KM Instalação": a.km_instalacao,
                "KM Instalação (km)": f"{formatar_valor_ptbr(a.km_instalacao)} km",
                "KM Vencimento": a.km_vencimento,
                "KM Vencimento (km)": f"{formatar_valor_ptbr(a.km_vencimento)} km" if a.km_vencimento else "N/A",
                "Data Instalação": a.data_instalacao,
                "Data Vencimento": a.data_vencimento if a.data_vencimento else "N/A",
                "Status": status,
                "Status Raw": status,
                "Descrição": a.descricao,
                "Motivo": motivo,
                "Hodômetro Atual (km)": f"{formatar_valor_ptbr(hodometro_atual)} km",
                "Valor (R$)": 0.0,
                "Valor Formatado (R$)": "N/A"
            })
        df = pd.DataFrame(dados_acessorios)
        if filtro_status:
            df = df[df["Status Raw"].isin(filtro_status)]
        return df
    except Exception as e:
        st.error(f"Erro ao obter dados de acessórios: {e}")
        return pd.DataFrame()

if menu_principal == "Dashboard":
    st.title("📊 **Painel de Controle**")
    
    st.markdown('<div class="sync-button-container">', unsafe_allow_html=True)
    if st.button("🔄 Sincronizar Dados de Veículos", key="sync_button", help="Clique para sincronizar os dados dos veículos e atualizar os hodômetros"):
        if session:
            try:
                sincronizar_dados_veiculos(session, write_progress=True)
            except Exception as e:
                st.error(f"❌ Erro ao sincronizar dados: {e}")
        else:
            st.error("❌ Erro: Não foi possível conectar ao banco de dados.")
    st.markdown('</div>', unsafe_allow_html=True)

    if not session:
        st.error("Não foi possível carregar o Dashboard devido a um erro na conexão com o banco de dados.")
    else:
        try:
            df_manutencoes = obter_dados_manutencoes(session_instance=session)
            total_manutencoes = len(df_manutencoes)
            manutencoes_saudaveis = len(df_manutencoes[df_manutencoes["Status"] == "saudavel"])
            manutencoes_alerta = len(df_manutencoes[df_manutencoes["Status"] == "alerta"])
            manutencoes_vencidas = len(df_manutencoes[df_manutencoes["Status"] == "vencido"])
            manutencoes_concluidas = len(df_manutencoes[df_manutencoes["Status"] == "concluído"])
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
            st.markdown(f"""<div style="background-color: #FFC107; color: white; padding: 15px; border-radius: 10px; text-align: center;"><h5 style="margin: 0;">⚠️ Alerta</h5><p style="font-size: 24px; margin: 0;"><a href='?menu=Dashboard&filtro_status=alerta' style='color: white; text-decoration: underline;' target='_self'>{manutencoes_alerta}</a></p><p style="font-size: 14px; margin: 0;">(Próximas)</p></div>""", unsafe_allow_html=True)
        with col4:
            st.markdown(f"""<div style="background-color: #FF5722; color: white; padding: 15px; border-radius: 10px; text-align: center;"><h5 style="margin: 0;">⛔ Vencidas</h5><p style="font-size: 24px; margin: 0;"><a href='?menu=Dashboard&filtro_status=vencido' style='color: white; text-decoration: underline;' target='_self'>{manutencoes_vencidas}</a></p><p style="font-size: 14px; margin: 0;">(Atrasadas)</p></div>""", unsafe_allow_html=True)
        with col5:
            st.markdown(f"""<div style="background-color: #9E9E9E; color: white; padding: 15px; border-radius: 10px; text-align: center;"><h5 style="margin: 0;">✅ Concluídas</h5><p style="font-size: 24px; margin: 0;"><a href='?menu=Dashboard&filtro_status=concluído' style='color: white; text-decoration: underline;' target='_self'>{manutencoes_concluidas}</a></p><p style="font-size: 14px; margin: 0;">(Finalizadas)</p></div>""", unsafe_allow_html=True)

        filtro_status = st.query_params.get("filtro_status", None)
        if filtro_status in ["vencido", "alerta", "concluído"]:
            if 'show_table' not in st.session_state:
                st.session_state.show_table = True

            if st.session_state.show_table:
                st.markdown(f"### 📋 **Manutenções {filtro_status}**")
                df_manutencoes = obter_dados_manutencoes(filtro_status=[filtro_status], session_instance=session)
                df_acessorios = pd.DataFrame()
                if filtro_status == "alerta":
                    df_acessorios = obter_dados_acessorios(filtro_status=[filtro_status], session_instance=session)
                
                if filtro_status == "alerta" and not df_manutencoes.empty and not df_acessorios.empty:
                    df_combined = pd.concat([df_manutencoes, df_acessorios], ignore_index=True, sort=False)
                elif filtro_status == "alerta" and not df_manutencoes.empty:
                    df_combined = df_manutencoes
                elif filtro_status == "alerta" and not df_acessorios.empty:
                    df_combined = df_acessorios
                else:
                    df_combined = df_manutencoes if not df_manutencoes.empty else df_acessorios

                if df_combined.empty:
                    st.warning(f"⚠️ Nenhuma manutenção ou acessório encontrado no estado '{filtro_status}'!")
                else:
                    if filtro_status == "vencido":
                        df_display = df_combined[["ID", "Tipo de Registro", "Veículo", "Categoria", "Tipo", "KM Vencimento (km)", "Data Vencimento", "Status", "Motivo"]]
                    elif filtro_status == "alerta":
                        df_display = df_combined[["ID", "Tipo de Registro", "Veículo", "Hodômetro Atual (km)", "KM Vencimento (km)", "Data Vencimento", "Status", "Motivo"]]
                    elif filtro_status == "concluído":
                        df_display = df_combined[["ID", "Tipo de Registro", "Veículo", "Categoria", "Tipo", "Data Manutenção", "Data Realização", "Valor Formatado (R$)", "Status"]]
                    df_display["Status"] = df_display["Status"].apply(adicionar_emoji_status)
                    st.dataframe(df_display, use_container_width=True, height=300)
                    total_manutencoes = len(df_combined)
                    total_valor = df_combined["Valor (R$)"].sum()
                    total_valor_formatado = formatar_valor_monetario(total_valor)
                    st.markdown(f"""<div style="background-color: #2e7d32; padding: 15px; border-radius: 5px; color: white; font-size: 18px;">Total de Registros: {total_manutencoes}<br>Valor Total (R$): {total_valor_formatado}</div>""", unsafe_allow_html=True)

                if st.button("Ocultar Tabela"):
                    st.session_state.show_table = False
                    st.query_params.clear()
                    st.rerun()

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
                session.query(Manutencao).statement, session.bind
            )
            if not df_manutencao.empty:
                df_manutencao['data_manutencao'] = pd.to_datetime(df_manutencao['data_manutencao'])
                df_manutencao['mes_ano'] = df_manutencao['data_manutencao'].dt.to_period('M').astype(str)
                df_custo_mensal = df_manutencao.groupby('mes_ano')['valor_manutencao'].sum().reset_index()
                fig_custo = px.line(df_custo_mensal, x='mes_ano', y='valor_manutencao', title="📉 Custo Mensal de Manutenções", labels={'mes_ano': 'Mês/Ano', 'valor_manutencao': 'Custo (R$)'})
                fig_custo.update_layout(height=400)
                with col5:
                    st.plotly_chart(fig_custo, use_container_width=True)
            else:
                with col5:
                    st.warning("⚠️ Nenhum dado disponível para Custo Mensal.")
        except Exception as e:
            with col5:
                st.error(f"Erro ao carregar gráfico de custo: {e}")

        try:
            df_manutencao['tipo'] = df_manutencao['tipo'].fillna('Desconhecido')
            df_tipo = df_manutencao.groupby('tipo').size().reset_index(name='quantidade')
            fig_tipo = px.bar(df_tipo, x='tipo', y='quantidade', title="📊 Manutenções por Tipo", labels={'tipo': 'Tipo', 'quantidade': 'Quantidade'})
            fig_tipo.update_layout(height=400)
            with col6:
                st.plotly_chart(fig_tipo, use_container_width=True)
        except Exception as e:
            with col6:
                st.error(f"Erro ao carregar gráfico de tipo: {e}")

elif menu_principal == "Cadastros":
    cadastros.app(session)

elif menu_principal == "Manutenções":
    manutencoes.app(session)

elif menu_principal == "Relatórios":
    relatorios.app(session)

elif menu_principal == "Configurações":
    configuracoes.app(session)
