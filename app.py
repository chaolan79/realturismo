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
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io

# Inicializar a sessão com try-except
try:
    session = Session()
except Exception as e:
    st.error(f"Erro ao conectar ao banco de dados: {e}")
    session = None

# Configurações do Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']
FILE_ID = '1YXMZJdto7Lmpv9aEGazd_3X_bzB8K2C4'  # ID do arquivo manutencoes.db
DB_FILE = 'manutencoes.db'

# Criar client_secrets.json a partir dos secrets do Streamlit
if 'CLIENT_SECRETS' in st.secrets:
    with open('client_secrets.json', 'w') as f:
        f.write(st.secrets['CLIENT_SECRETS']['content'])
else:
    # Para execução local, certifique-se de que client_secrets.json está no diretório
    if not os.path.exists('client_secrets.json'):
        st.error("Arquivo client_secrets.json não encontrado. Adicione-o ao diretório raiz ou configure os secrets no Streamlit Cloud.")
        st.stop()

# Criar token.json a partir dos secrets do Streamlit
if 'TOKEN' in st.secrets:
    with open('token.json', 'w') as f:
        f.write(st.secrets['TOKEN']['content'])

# Função para autenticar e obter o serviço do Google Drive
def get_drive_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
            creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

# Função para baixar o arquivo do Google Drive
def download_file():
    service = get_drive_service()
    request = service.files().get_media(fileId=FILE_ID)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    with open(DB_FILE, 'wb') as f:
        f.write(fh.getvalue())

# Função para enviar o arquivo atualizado ao Google Drive
def upload_file():
    service = get_drive_service()
    media = MediaFileUpload(DB_FILE)
    service.files().update(fileId=FILE_ID, media_body=media).execute()

# Baixar o arquivo do Google Drive se ele não existir localmente
if not os.path.exists(DB_FILE):
    st.write("Baixando o banco de dados do Google Drive...")
    download_file()
    st.write("Banco de dados baixado com sucesso!")

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

        # Calcular o intervalo dos últimos 30 dias
        hoje = datetime.now()
        data_inicio = hoje - timedelta(days=30)
        
        # Determinar os meses e anos envolvidos no intervalo
        meses_anos = []
        current_date = data_inicio
        while current_date <= hoje:
            meses_anos.append((current_date.month, current_date.year))
            current_date += timedelta(days=1)
        meses_anos = list(set(meses_anos))  # Remover duplicatas

        session_requests = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session_requests.mount("http://", HTTPAdapter(max_retries=retries))
        TIMEOUT = 30

        # Testar conexão com a API
        try:
            test_response = session_requests.get(api_url, headers=headers, timeout=TIMEOUT)
            test_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Erro ao conectar à API: {e}")

        hodometros_veiculos = {}
        veiculos = session_instance.query(Veiculo).all()
        veiculos_dict = {str(v.codigo): v for v in veiculos}

        # Verificar veículos com hodômetro zerado antes da sincronização
        veiculos_zerados_antes = [str(v.codigo) for v in veiculos if v.hodometro_atual == 0]
        if veiculos_zerados_antes and write_progress:
            st.warning(f"⚠️ Antes da sincronização, os seguintes veículos estão com hodômetro zerado: {', '.join(veiculos_zerados_antes)}")

        # Buscar dados para cada mês/ano no intervalo
        for mes, ano in meses_anos:
            params = {
                "EValidado": "",
                "veiculo": "",
                "month": str(mes),
                "year": str(ano),
                "page": 1,
                "perPage": 100
            }

            while True:
                try:
                    response = session_requests.get(api_url, headers=headers, params=params, timeout=TIMEOUT)
                    response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    raise Exception(f"Erro ao buscar dados da API para {mes}/{ano}: {e}")

                dados_api = response.json()
                resultados = dados_api.get("results", [])

                for item in resultados:
                    # Extrair dados do abastecimento
                    codigo = str(item.get("veiculo_detail", {}).get("codigo"))
                    hodometro = float(item.get("hodometro", 0.0))
                    abastecimento_id = item.get("id")
                    veiculo_id_api = item.get("veiculo")
                    data_abastecimento_str = item.get("horario")
                    litros = float(item.get("litros", 0.0))
                    valor = float(item.get("valor", 0.0))

                    # Converter a data do abastecimento
                    try:
                        data_abastecimento = datetime.strptime(data_abastecimento_str, "%d/%m/%Y %H:%M:%S")
                    except (ValueError, TypeError):
                        continue  # Ignorar registros com data inválida

                    # Verificar se o abastecimento já existe no banco
                    abastecimento_existente = session_instance.query(Abastecimento).filter_by(id=abastecimento_id).first()
                    if not abastecimento_existente:
                        # Encontrar o veículo correspondente no banco
                        veiculo = veiculos_dict.get(codigo)
                        if veiculo:
                            # Criar novo registro de abastecimento
                            novo_abastecimento = Abastecimento(
                                id=abastecimento_id,
                                veiculo_id=veiculo.id,
                                data_abastecimento=data_abastecimento,
                                hodometro=hodometro,
                                litros=litros,
                                valor=valor
                            )
                            session_instance.add(novo_abastecimento)
                        else:
                            continue  # Ignorar se o veículo não for encontrado

                    # Atualizar o hodômetro do veículo (apenas se válido)
                    if hodometro <= 0.0:
                        continue
                    if codigo in hodometros_veiculos:
                        if data_abastecimento > hodometros_veiculos[codigo]["data"]:
                            hodometros_veiculos[codigo] = {"hodometro": hodometro, "data": data_abastecimento}
                    else:
                        hodometros_veiculos[codigo] = {"hodometro": hodometro, "data": data_abastecimento}

                next_url = dados_api.get("next")
                if not next_url:
                    break
                params["page"] += 1

        # Atualizar o hodometro_atual apenas dos veículos que têm registros válidos na API
        veiculos_zerados = []
        veiculos_nao_atualizados = []
        for veiculo in veiculos:
            codigo = str(veiculo.codigo)
            if codigo in hodometros_veiculos:
                dados = hodometros_veiculos[codigo]
                hodometro = dados["hodometro"]
                data_abastecimento = dados["data"]
                ultimo_abastecimento = session_instance.query(Abastecimento).filter_by(veiculo_id=veiculo.id).order_by(Abastecimento.data_abastecimento.desc()).first()
                data_ultimo_abastecimento = ultimo_abastecimento.data_abastecimento if ultimo_abastecimento else datetime.min
                if data_abastecimento > data_ultimo_abastecimento:
                    # Só atualizar se o novo hodômetro for maior que 0 e maior que o atual (ou se o atual for 0)
                    if hodometro > 0 and (veiculo.hodometro_atual == 0 or hodometro > veiculo.hodometro_atual):
                        veiculo.hodometro_atual = hodometro
                    else:
                        veiculos_nao_atualizados.append(codigo)
                else:
                    veiculos_nao_atualizados.append(codigo)
            else:
                veiculos_nao_atualizados.append(codigo)

            if veiculo.hodometro_atual == 0:
                veiculos_zerados.append(codigo)

        session_instance.commit()
        if write_progress:
            st.success("✅ Sincronização concluída com sucesso!")
            if veiculos_zerados:
                st.warning(f"⚠️ Os seguintes veículos estão com hodômetro zerado após a sincronização: {', '.join(veiculos_zerados)}")
            if veiculos_nao_atualizados:
                st.info(f"ℹ️ Os seguintes veículos não foram atualizados (hodômetro inválido, não mais recente ou sem registros): {', '.join(veiculos_nao_atualizados)}")

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
                session.query(Manutencao.categoria, func.count().label('total'))
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

        st.markdown("### 📆 **Gastos nos Últimos 15 Dias**")
        try:
            if session:
                data_limite = datetime.today() - timedelta(days=15)
                df_gastos = pd.read_sql(
                    session.query(
                        func.date(Manutencao.data_manutencao).label('data'),
                        func.sum(Manutencao.valor_manutencao).label('total')
                    )
                    .filter(Manutencao.data_manutencao >= data_limite)
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
    configuracoes.exibir_configuracoes(session=session, sincronizar_dados_veiculos=sincronizar_dados_veiculos)

# Botão para enviar o banco de dados atualizado ao Google Drive
if st.button("📤 Enviar Banco de Dados para o Google Drive"):
    upload_file()
    st.success("Banco de dados enviado ao Google Drive com sucesso!")

# Fechar a sessão do banco de dados
if session:
    session.close()
