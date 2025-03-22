import streamlit as st
import pandas as pd
import sqlite3
import shutil
from datetime import datetime
import os
from database import Session, engine, Veiculo, Abastecimento
from sqlalchemy import create_engine, Column, Integer, String, Float, select
from sqlalchemy.ext.declarative import declarative_base
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Obter o diretório raiz do projeto (onde app.py está localizado)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Inicializa a sessão do banco de dados
session = Session()

# Modelo para a tabela Configuracao
Base = declarative_base()

class Configuracao(Base):
    __tablename__ = "configuracoes"
    id = Column(Integer, primary_key=True, index=True)
    chave = Column(String, unique=True, nullable=False)
    valor = Column(Float, nullable=False)

# Cria a tabela se não existir
Base.metadata.create_all(engine)

def salvar_configuracao(chave, valor):
    try:
        config = session.query(Configuracao).filter_by(chave=chave).first()
        if config:
            config.valor = valor
        else:
            nova_config = Configuracao(chave=chave, valor=valor)
            session.add(nova_config)
        session.commit()
    except Exception as e:
        session.rollback()
        st.error(f"❌ Erro ao salvar configuração '{chave}': {e}")

def obter_configuracao(chave, valor_padrao):
    try:
        config = session.query(Configuracao).filter_by(chave=chave).first()
        return config.valor if config else valor_padrao
    except Exception as e:
        st.error(f"❌ Erro ao obter configuração '{chave}': {e}")
        return valor_padrao

# Função para conectar ao banco com sqlite3 (para consultar integracao_api)
def get_db_connection():
    DB_DIR = os.path.join(BASE_DIR, 'data')
    db_path = os.environ.get('FLEETFIX_DB_PATH', os.path.join(DB_DIR, 'manutencoes.db'))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Função para inicializar a tabela integracao_api
def inicializar_tabela_integracao():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS integracao_api (
            id INTEGER PRIMARY KEY,
            ultimo_id_processado INTEGER DEFAULT 0,
            data_ultima_integracao TEXT DEFAULT '1970-01-01'
        )
    """)
    # Insere um registro padrão se a tabela estiver vazia
    cursor.execute("INSERT OR IGNORE INTO integracao_api (id, ultimo_id_processado, data_ultima_integracao) VALUES (1, 0, '1970-01-01')")
    conn.commit()
    conn.close()

# Função para consultar o estado da integração
def get_ultimo_id_processado():
    inicializar_tabela_integracao()  # Garante que a tabela exista antes de consultar
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ultimo_id_processado, data_ultima_integracao FROM integracao_api WHERE id = 1")
    result = cursor.fetchone()
    conn.close()
    return result if result else {"ultimo_id_processado": 0, "data_ultima_integracao": "1970-01-01"}

# Função para atualizar o estado da integração
def atualizar_estado_integracao(ultimo_id, data):
    inicializar_tabela_integracao()  # Garante que a tabela exista antes de atualizar
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO integracao_api (id, ultimo_id_processado, data_ultima_integracao) VALUES (1, ?, ?)",
        (ultimo_id, data)
    )
    conn.commit()
    conn.close()

def backup_banco():
    try:
        DB_DIR = os.path.join(BASE_DIR, 'data')
        db_path = os.environ.get('FLEETFIX_DB_PATH', os.path.join(DB_DIR, 'manutencoes.db'))
        BACKUP_DIR = os.environ.get('FLEETFIX_BACKUP_PATH', os.path.join(BASE_DIR, 'backups'))
        
        os.makedirs(BACKUP_DIR, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"manutencoes_backup_{timestamp}.db")
        
        shutil.copy2(db_path, backup_path)
        st.success(f"✅ Backup realizado com sucesso em: {backup_path}")
    except Exception as e:
        st.error(f"❌ Erro ao realizar backup: {e}")

def importar_dados():
    uploaded_file = st.file_uploader("Escolha um arquivo Excel", type="xlsx")
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            st.write("Dados Importados:", df)
            st.success("✅ Dados importados com sucesso!")
        except Exception as e:
            st.error(f"❌ Erro ao importar os dados: {e}")

def exportar_dados():
    export_file = "manutencoes_exportado.xlsx"
    try:
        DB_DIR = os.path.join(BASE_DIR, 'data')
        db_path = os.environ.get('FLEETFIX_DB_PATH', os.path.join(DB_DIR, 'manutencoes.db'))
        df = pd.read_sql("SELECT * FROM manutencoes", sqlite3.connect(db_path))
        df.to_excel(export_file, index=False)
        with open(export_file, "rb") as file:
            st.download_button("Baixar Dados em Excel", file, file_name=export_file)
    except Exception as e:
        st.error(f"❌ Erro ao exportar os dados: {e}")

def verificar_saude_bd():
    try:
        DB_DIR = os.path.join(BASE_DIR, 'data')
        db_path = os.environ.get('FLEETFIX_DB_PATH', os.path.join(DB_DIR, 'manutencoes.db'))
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            st.write(f"Tabela: {table_name} - Registros: {count}")
        conn.close()
    except Exception as e:
        st.error(f"❌ Erro ao verificar saúde do banco: {e}")

def configurar_geral():
    st.subheader("⚙️ **Configurações Gerais**")
    
    km_aviso = obter_configuracao("km_aviso", 1000.0)
    data_limite_dias = obter_configuracao("data_limite_dias", 30.0)

    with st.form(key="configuracoes_gerais", clear_on_submit=False):
        novo_km_aviso = st.number_input(
            "📏 **KM Aviso (km)** - Distância para alerta antes do vencimento por KM",
            min_value=0.0,
            step=1.0,
            format="%.2f",
            value=km_aviso
        )
        novo_data_limite_dias = st.number_input(
            "📅 **Data Limite (dias)** - Quantidade de dias para alerta antes do vencimento por data",
            min_value=0.0,
            step=1.0,
            format="%.0f",
            value=data_limite_dias
        )
        submit_button = st.form_submit_button(label="💾 **Salvar Configurações**")

        if submit_button:
            salvar_configuracao("km_aviso", novo_km_aviso)
            salvar_configuracao("data_limite_dias", novo_data_limite_dias)
            st.success("✅ Configurações salvas com sucesso!")

def configurar_sincronizacao_veiculos(session, sincronizar_dados_veiculos):
    st.subheader("🌐 **Sincronização de Dados de Veículos**")
    st.markdown("Atualize os hodômetros dos veículos manualmente clicando no botão abaixo.")
    
    # Exibir o estado atual da sincronização
    estado_sincronizacao = get_ultimo_id_processado()
    st.write(f"**Último ID Processado**: {estado_sincronizacao['ultimo_id_processado']}")
    st.write(f"**Data da Última Sincronização**: {estado_sincronizacao['data_ultima_integracao']}")
    
    if st.button("Sincronizar Dados de Veículos Manualmente"):
        try:
            # Configuração da API
            api_url = "http://89.116.214.34:8000/api/abastecimentos/"
            headers = {"Authorization": "Token c6f5a268b3f1bc95c875a8203ad1562f47dcf0ad"}
            params = {"EValidado": "", "veiculo": "", "month": "", "year": "2025", "page": 1, "perPage": 100}

            session_requests = requests.Session()
            retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
            session_requests.mount("http://", HTTPAdapter(max_retries=retries))
            TIMEOUT = 30

            # Etapa 1: Testar conexão com a API
            st.info("⏳ Etapa 1/5: Testando conexão com a API...")
            try:
                test_response = session_requests.get(api_url, headers=headers, params=params, timeout=TIMEOUT)
                test_response.raise_for_status()
                st.success("✅ Conexão com a API estabelecida com sucesso!")
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Falha ao conectar à API: {str(e)}")
                return

            # Opção de forçar sincronização
            forcar_atualizacao = st.checkbox("Forçar sincronização (sobrescrever todos os hodômetros)", value=False)

            hodometros_veiculos = {}
            total_paginas_processadas = 0
            ultimo_id_processado = 0
            registros_ignorados = 0

            # Etapa 2: Buscar dados da API
            st.info("⏳ Etapa 2/5: Buscando dados da API...")
            while True:
                st.info(f"📥 Processando página {params['page']}...")
                try:
                    response = session_requests.get(api_url, headers=headers, params=params, timeout=TIMEOUT)
                    response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    st.error(f"❌ Erro ao acessar a API na página {params['page']}: {str(e)}")
                    return

                dados_api = response.json()
                resultados = dados_api.get("results", [])

                for item in resultados:
                    codigo = str(item.get("veiculo"))
                    hodometro = float(item.get("hodometro", 0.0))
                    data_str = item.get("data")
                    id_registro = item.get("id", 0)

                    try:
                        data = datetime.fromisoformat(data_str.replace("Z", "+00:00"))
                        data = data.replace(tzinfo=None)
                    except ValueError:
                        st.warning(f"⚠️ Data inválida para o veículo {codigo}: {data_str}. Ignorando registro.")
                        registros_ignorados += 1
                        continue

                    if hodometro <= 0.0:
                        st.warning(f"⚠️ Hodômetro inválido (0.0 km) para o veículo {codigo}. Ignorando registro.")
                        registros_ignorados += 1
                        continue

                    if codigo in hodometros_veiculos:
                        if data > hodometros_veiculos[codigo]["data"]:
                            hodometros_veiculos[codigo] = {"hodometro": hodometro, "data": data, "id": id_registro}
                    else:
                        hodometros_veiculos[codigo] = {"hodometro": hodometro, "data": data, "id": id_registro}

                    if id_registro > ultimo_id_processado:
                        ultimo_id_processado = id_registro

                total_paginas_processadas += 1
                next_url = dados_api.get("next")
                if not next_url:
                    break
                params["page"] += 1

            st.success(f"✅ Etapa 2/5 concluída: {total_paginas_processadas} páginas processadas, {registros_ignorados} registros ignorados.")

            # Etapa 3: Carregar veículos do banco de dados
            st.info("⏳ Etapa 3/5: Carregando veículos do banco de dados...")
            veiculos = session.query(Veiculo).all()
            veiculos_dict = {str(v.codigo): v for v in veiculos}
            st.success(f"✅ {len(veiculos)} veículos carregados do banco.")

            # Etapa 4: Atualizar hodômetros
            atualizados = 0
            nao_encontrados = 0
            ignorados_por_data = 0

            st.info("⏳ Etapa 4/5: Atualizando hodômetros dos veículos...")
            for codigo, dados in hodometros_veiculos.items():
                hodometro = dados["hodometro"]
                if codigo in veiculos_dict:
                    veiculo = veiculos_dict[codigo]
                    if forcar_atualizacao or veiculo.hodometro_atual == 0.0:
                        veiculo.hodometro_atual = hodometro
                        atualizados += 1
                        st.info(f"🚗 Veículo {codigo} atualizado: hodômetro {hodometro} km (forçado ou hodômetro zerado)")
                    else:
                        ultimo_abastecimento = session.query(Abastecimento).filter_by(veiculo_id=veiculo.id).order_by(Abastecimento.data.desc()).first()
                        data_ultimo_abastecimento = ultimo_abastecimento.data if ultimo_abastecimento else datetime.min
                        if hasattr(data_ultimo_abastecimento, 'tzinfo') and data_ultimo_abastecimento.tzinfo is not None:
                            data_ultimo_abastecimento = data_ultimo_abastecimento.replace(tzinfo=None)
                        if dados["data"] > data_ultimo_abastecimento:
                            veiculo.hodometro_atual = hodometro
                            atualizados += 1
                            st.info(f"🚗 Veículo {codigo} atualizado: hodômetro {hodometro} km (data mais recente)")
                        else:
                            ignorados_por_data += 1
                            st.info(f"ℹ️ Veículo {codigo} não atualizado: data da API ({dados['data']}) não é mais recente que o último abastecimento ({data_ultimo_abastecimento})")
                else:
                    nao_encontrados += 1
                    st.warning(f"⚠️ Veículo com código {codigo} não encontrado no banco.")

            # Etapa 5: Salvar alterações
            st.info("⏳ Etapa 5/5: Salvando alterações no banco de dados...")
            session.commit()
            data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            atualizar_estado_integracao(ultimo_id_processado, data_atual)

            # Resumo final
            st.success(f"✅ Sincronização concluída!")
            st.markdown("### 📋 Resumo da Sincronização")
            st.write(f"**Páginas Processadas**: {total_paginas_processadas}")
            st.write(f"**Veículos Atualizados**: {atualizados}")
            st.write(f"**Veículos Não Encontrados**: {nao_encontrados}")
            st.write(f"**Veículos Ignorados (data não recente)**: {ignorados_por_data}")
            st.write(f"**Registros Ignorados (hodômetro inválido ou data inválida)**: {registros_ignorados}")
            st.write(f"**Último ID Processado**: {ultimo_id_processado}")
            st.write(f"**Data da Sincronização**: {data_atual}")

        except Exception as e:
            session.rollback()
            st.error(f"❌ Erro ao executar sincronização: {e}")

def exibir_configuracoes(session=None, sincronizar_dados_veiculos=None):
    st.title("⚙️ **Configurações e Ferramentas**")

    menu_config = st.radio(
        "Selecione a ação",
        ["Configurações Gerais", "Sincronização de Veículos", "Backup do Banco de Dados", "Importar Dados", "Exportar Dados", "Saúde do Banco"]
    )

    if menu_config == "Configurações Gerais":
        configurar_geral()

    elif menu_config == "Sincronização de Veículos":
        if session and sincronizar_dados_veiculos:
            configurar_sincronizacao_veiculos(session, sincronizar_dados_veiculos)
        else:
            st.error("❌ Erro: Sessão ou função de sincronização não fornecidas.")

    elif menu_config == "Backup do Banco de Dados":
        if st.button("Realizar Backup"):
            backup_banco()

    elif menu_config == "Importar Dados":
        importar_dados()

    elif menu_config == "Exportar Dados":
        exportar_dados()

    elif menu_config == "Saúde do Banco":
        verificar_saude_bd()

if __name__ == "__main__":
    exibir_configuracoes()