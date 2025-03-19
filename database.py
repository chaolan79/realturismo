import sys
import os

# Adicionar o diretório raiz ao sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship  # Adicionado relationship
import os
import sys

def check_directory_writable(directory):
    try:
        test_file = os.path.join(directory, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        return True
    except Exception as e:
        print(f"Erro: O diretório {directory} não é gravável. Detalhes: {e}")
        return False

# Usar variável de ambiente para o caminho do banco
DB_PATH = os.environ.get('FLEETFIX_DB_PATH', os.path.join(BASE_DIR, 'data', 'manutencoes.db'))

# Criar o diretório 'data', se não existir
DB_DIR = os.path.dirname(DB_PATH)
if not os.path.exists(DB_DIR):
    try:
        os.makedirs(DB_DIR)
        print(f"Diretório {DB_DIR} criado com sucesso.")
    except Exception as e:
        print(f"Erro ao criar o diretório {DB_DIR}: {e}")
        sys.exit(1)

# Verificar se o diretório é gravável
if not check_directory_writable(DB_DIR):
    print(f"Erro: Não é possível escrever no diretório {DB_DIR}. Verifique as permissões.")
    sys.exit(1)

# Verificar se o arquivo do banco de dados pode ser criado
try:
    with open(DB_PATH, 'a') as f:
        pass
    print(f"Caminho do banco de dados: {DB_PATH}")
except Exception as e:
    print(f"Erro ao acessar ou criar o arquivo do banco de dados {DB_PATH}: {e}")
    sys.exit(1)

# Criar o engine do SQLAlchemy
try:
    engine = create_engine(f'sqlite:///{DB_PATH}')
    print("Engine do SQLAlchemy criado com sucesso.")
except Exception as e:
    print(f"Erro ao criar o engine do SQLAlchemy: {e}")
    sys.exit(1)

Base = declarative_base()  # Atualizado para usar sqlalchemy.orm.declarative_base()

# Tabela de Veículos
class Veiculo(Base):
    __tablename__ = 'Veiculo'
    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(Integer, unique=True, nullable=False)
    placa = Column(String, unique=True, nullable=False)
    modelo = Column(String, nullable=False)
    fabricante = Column(String, nullable=False)
    hodometro_atual = Column(Float, nullable=False)
    abastecimentos = relationship("Abastecimento", back_populates="veiculo")

# Tabela de Categorias
class Categoria(Base):
    __tablename__ = 'Categoria'
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String, unique=True, nullable=False)

# Tabela de Responsáveis
class Responsavel(Base):
    __tablename__ = 'Responsavel'
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String, unique=True, nullable=False)

# Tabela de Oficinas
class Oficina(Base):
    __tablename__ = 'Oficina'
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String, unique=True, nullable=False)
    endereco = Column(String, nullable=True)
    telefone = Column(String, nullable=True)

# Tabela de Acessórios
class Acessorio(Base):
    __tablename__ = 'Acessorio'
    id = Column(Integer, primary_key=True, autoincrement=True)
    veiculo_id = Column(Integer, ForeignKey('Veiculo.id'), nullable=False)
    nome = Column(String, nullable=False)
    km_instalacao = Column(Float, nullable=False)
    km_vencimento = Column(Float)
    data_instalacao = Column(Date, nullable=False)
    data_vencimento = Column(Date)
    tem_vencimento = Column(Boolean, default=True)
    status = Column(String, nullable=False)
    # vencido removido, já que não existe no banco
    descricao = Column(String)

# Tabela de Manutenções
class Manutencao(Base):
    __tablename__ = 'Manutencao'
    id = Column(Integer, primary_key=True, autoincrement=True)
    veiculo_id = Column(Integer, ForeignKey('Veiculo.id'), nullable=False)
    categoria = Column(String, ForeignKey('Categoria.nome'), nullable=False)
    responsavel = Column(String, ForeignKey('Responsavel.nome'), nullable=False)
    oficina = Column(String, ForeignKey('Oficina.nome'), nullable=False)
    tipo = Column(String, nullable=False)
    km_aviso = Column(Float, nullable=False)
    data_manutencao = Column(Date, nullable=False)
    hodometro_manutencao = Column(Float, nullable=False)
    valor_manutencao = Column(Float, nullable=False)
    km_vencimento = Column(Float, nullable=False)
    data_vencimento = Column(Date)
    tem_vencimento = Column(Boolean, default=True)
    # vencido removido, já que foi mapeado para tem_vencimento no banco
    descricao = Column(String, nullable=False)
    status = Column(String)  # Removida restrição NOT NULL para alinhar com o banco
    data_realizacao = Column(DateTime)  # Ajustado para DateTime, removida restrição NOT NULL

# Tabela de Configurações
class Configuracao(Base):
    __tablename__ = 'configuracoes'
    id = Column(Integer, primary_key=True, index=True)
    chave = Column(String, unique=True, nullable=False)
    valor = Column(Float, nullable=False)

# Tabela de Abastecimentos
class Abastecimento(Base):
    __tablename__ = 'abastecimentos'
    id = Column(Integer, primary_key=True, autoincrement=True)
    veiculo_id = Column(Integer, ForeignKey('Veiculo.id'), nullable=False)
    data = Column(DateTime, nullable=False)
    hodometro = Column(Float, nullable=False)
    km_rodado = Column(Float, nullable=True)
    litros_abastecido = Column(Float, nullable=True)
    valor_abastecido = Column(Float, nullable=True)
    tipo_combustivel = Column(String, nullable=True)
    veiculo = relationship("Veiculo", back_populates="abastecimentos")

# Criar tabelas
try:
    Base.metadata.create_all(engine)
    print("Tabelas do banco de dados criadas com sucesso.")
except Exception as e:
    print(f"Erro ao criar tabelas no banco de dados: {e}")
    sys.exit(1)

# Criar sessão
Session = sessionmaker(bind=engine)