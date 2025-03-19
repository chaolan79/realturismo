import streamlit as st
import pandas as pd
import sqlite3
import shutil
from datetime import datetime
import os
from database import Session, engine
from sqlalchemy import create_engine, Column, Integer, String, Float, select
from sqlalchemy.ext.declarative import declarative_base

# Obter o diretório raiz do projeto (onde app.py está localizado)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Inicializa a sessão do banco de dados
session = Session()

# Modelo para a tabela Configuracao (deve estar em database.py, mas incluído aqui para referência)
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
        # Verifica se a configuração já existe
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

def backup_banco():
    try:
        # Usar caminhos relativos para o banco de dados e backups
        DB_DIR = os.path.join(BASE_DIR, 'data')
        db_path = os.environ.get('FLEETFIX_DB_PATH', os.path.join(DB_DIR, 'manutencoes.db'))
        BACKUP_DIR = os.environ.get('FLEETFIX_BACKUP_PATH', os.path.join(BASE_DIR, 'backups'))
        
        # Criar o diretório de backups, se não existir
        os.makedirs(BACKUP_DIR, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"manutencoes_backup_{timestamp}.db")
        
        shutil.copy2(db_path, backup_path)
        st.success(f"Backup realizado com sucesso em: {backup_path}")
    except Exception as e:
        st.error(f"Erro ao realizar backup: {e}")

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
        # Usar caminho relativo para o banco de dados
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
        # Usar caminho relativo para o banco de dados
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

def configurar_alertas():
    st.subheader("⚙️ **Configurações de Alertas**")
    
    # Obter valores atuais ou usar padrões
    km_aviso = obter_configuracao("km_aviso", 1000.0)
    data_limite_dias = obter_configuracao("data_limite_dias", 30.0)

    # Campos para configuração
    with st.form(key="configuracoes_alertas", clear_on_submit=False):
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

def exibir_configuracoes():
    st.title("⚙️ **Configurações e Ferramentas**")

    menu_config = st.radio(
        "Selecione a ação",
        ["Configurações Gerais", "Backup do Banco de Dados", "Importar Dados", "Exportar Dados", "Saúde do Banco"]
    )

    if menu_config == "Configurações Gerais":
        configurar_alertas()

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