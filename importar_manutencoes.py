import streamlit as st
import requests
from database import Session, Veiculo, Categoria, Responsavel, Oficina, Manutencao
from datetime import datetime
import base64
import time

# Criar sessão com o banco de dados
session = Session()

# URL base da API
BASE_URL = "http://89.116.214.34:8000/api/manutencao/?status=all&atual=true&search=&veiculo=&categoria=&oficina=&month=&year=2025&antigo=false&perPage=10"

# Total esperado de manutenções (obtido da interface da API)
EXPECTED_TOTAL_MAINTENANCES = 532

# Função para testar a conexão com a API
def test_api_connection(token, auth_type, custom_header_name=None, custom_header_value=None, username=None, password=None):
    url = f"{BASE_URL}&page=1"
    headers = {
        "User-Agent": "PostmanRuntime/7.43.0",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }
    
    if auth_type == "Bearer":
        headers["Authorization"] = f"Bearer {token}"
    elif auth_type == "Token":
        headers["Authorization"] = f"Token {token}"
    elif auth_type == "X-API-Key":
        headers["X-API-Key"] = token
    elif auth_type == "No-Prefix":
        headers["Authorization"] = token
    elif auth_type == "Basic":
        if username and password:
            credentials = f"{username}:{password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded_credentials}"
        else:
            st.error("⚠️ Para autenticação Basic, forneça usuário e senha.")
            return False
    
    if custom_header_name and custom_header_value:
        headers[custom_header_name] = custom_header_value
    
    st.write(f"Debug: Headers enviados - {headers}")
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        st.success("✅ Conexão bem-sucedida com a API!")
        st.write("Resposta da API:", response.json())
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Falha na conexão com a API: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            st.write("Detalhes da resposta da API:", e.response.text)
        return False

# Função para buscar dados de uma página específica da API com retentativas
def fetch_page_from_api(page, token, auth_type, custom_header_name=None, custom_header_value=None, username=None, password=None, retries=3, delay=2):
    url = f"{BASE_URL}&page={page}"
    headers = {
        "User-Agent": "PostmanRuntime/7.43.0",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }
    
    if auth_type == "Bearer":
        headers["Authorization"] = f"Bearer {token}"
    elif auth_type == "Token":
        headers["Authorization"] = f"Token {token}"
    elif auth_type == "X-API-Key":
        headers["X-API-Key"] = token
    elif auth_type == "No-Prefix":
        headers["Authorization"] = token
    elif auth_type == "Basic":
        if username and password:
            credentials = f"{username}:{password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded_credentials}"
        else:
            st.error("⚠️ Para autenticação Basic, forneça usuário e senha.")
            return []
    
    if custom_header_name and custom_header_value:
        headers[custom_header_name] = custom_header_value
    
    st.write(f"Debug: Buscando página {page} com headers - {headers}")
    
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json().get("results", [])
            if not data:
                st.warning(f"⚠️ Página {page} está vazia ou não contém resultados.")
            st.write(f"📄 Página {page} processada com sucesso: {len(data)} manutenções encontradas.")
            return data
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Erro ao buscar página {page} da API (tentativa {attempt + 1}/{retries}): {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                st.write("Detalhes da resposta da API:", e.response.text)
            if attempt < retries - 1:
                st.write(f"⏳ Aguardando {delay} segundos antes de tentar novamente...")
                time.sleep(delay)
            else:
                st.error(f"❌ Falha ao buscar página {page} após {retries} tentativas. Pulando...")
                return []

# Função para inserir ou atualizar veículo com verificações detalhadas
def upsert_veiculo(veiculo_data):
    try:
        if not all(key in veiculo_data for key in ["id", "codigo", "placa", "modelo", "hodometro_atual"]):
            st.warning(f"⚠️ Veículo ID {veiculo_data.get('id', 'Desconhecido')}: Dados obrigatórios ausentes ou inválidos.")
            return None

        if veiculo_data.get("fabricante") is None:
            st.warning(f"⚠️ Veículo ID {veiculo_data['id']}: Fabricante ausente, usando valor padrão 'Desconhecido'.")
            veiculo_data["fabricante"] = "Desconhecido"

        existing_veiculo = session.query(Veiculo).filter_by(codigo=veiculo_data["codigo"]).first()
        if existing_veiculo:
            st.warning(f"⚠️ Veículo com código {veiculo_data['codigo']} já existe (ID: {existing_veiculo.id}). Usando o veículo existente.")
            return existing_veiculo.id

        if not isinstance(veiculo_data["hodometro_atual"], (int, float)) or veiculo_data["hodometro_atual"] < 0:
            st.warning(f"⚠️ Veículo ID {veiculo_data['id']}: Hodômetro inválido ({veiculo_data['hodometro_atual']}), usando 0.")
            veiculo_data["hodometro_atual"] = 0

        veiculo = session.query(Veiculo).filter_by(id=veiculo_data["id"]).first()
        if not veiculo:
            veiculo = Veiculo(
                id=veiculo_data["id"],
                codigo=veiculo_data["codigo"],
                placa=veiculo_data["placa"],
                modelo=veiculo_data["modelo"],
                fabricante=veiculo_data["fabricante"],
                hodometro_atual=veiculo_data["hodometro_atual"]
            )
            session.add(veiculo)
        else:
            veiculo.codigo = veiculo_data["codigo"]
            veiculo.placa = veiculo_data["placa"]
            veiculo.modelo = veiculo_data["modelo"]
            veiculo.fabricante = veiculo_data["fabricante"]
            veiculo.hodometro_atual = veiculo_data["hodometro_atual"]

        session.commit()
        st.write(f"✅ Veículo ID {veiculo.id} (Código: {veiculo.codigo}) inserido/atualizado com sucesso.")
        return veiculo.id

    except Exception as e:
        session.rollback()
        st.error(f"❌ Erro ao processar veículo ID {veiculo_data.get('id', 'Desconhecido')}: {str(e)}")
        return None

# Função para inserir ou atualizar categoria
def upsert_categoria(categoria_data):
    try:
        if not categoria_data.get("nome"):
            st.warning(f"⚠️ Categoria ausente ou inválida, usando valor padrão 'Sem Categoria'.")
            categoria_data["nome"] = "Sem Categoria"
        
        categoria = session.query(Categoria).filter_by(nome=categoria_data["nome"]).first()
        if not categoria:
            categoria = Categoria(nome=categoria_data["nome"])
            session.add(categoria)
            session.commit()
        return categoria.nome
    except Exception as e:
        st.error(f"❌ Erro ao processar categoria: {str(e)}")
        return "Sem Categoria"

# Função para inserir ou atualizar responsável
def upsert_responsavel(responsavel_data):
    try:
        nome = responsavel_data["user"]["full_name"] if responsavel_data.get("user") and responsavel_data["user"].get("full_name") else "Desconhecido"
        if not nome:
            st.warning(f"⚠️ Responsável ausente ou inválido, usando valor padrão 'Desconhecido'.")
            nome = "Desconhecido"
        
        responsavel = session.query(Responsavel).filter_by(nome=nome).first()
        if not responsavel:
            responsavel = Responsavel(nome=nome)
            session.add(responsavel)
            session.commit()
        return responsavel.nome
    except Exception as e:
        st.error(f"❌ Erro ao processar responsável: {str(e)}")
        return "Desconhecido"

# Função para inserir ou atualizar oficina
def upsert_oficina(oficina_data):
    try:
        if not oficina_data.get("nome"):
            st.warning(f"⚠️ Oficina ausente ou inválida, usando valor padrão 'Sem Oficina'.")
            oficina_data["nome"] = "Sem Oficina"
        
        oficina = session.query(Oficina).filter_by(nome=oficina_data["nome"]).first()
        if not oficina:
            oficina = Oficina(
                nome=oficina_data["nome"],
                endereco=oficina_data.get("endereco", ""),
                telefone=oficina_data.get("telefone", "")
            )
            session.add(oficina)
        else:
            oficina.endereco = oficina_data.get("endereco", oficina.endereco)
            oficina.telefone = oficina_data.get("telefone", oficina.telefone)
        session.commit()
        return oficina.nome
    except Exception as e:
        st.error(f"❌ Erro ao processar oficina: {str(e)}")
        return "Sem Oficina"

# Função para importar os dados da API para o banco
def importar_manutencoes():
    st.title("📥 **Importar Manutenções da API (54 Páginas, 10 Itens por Página)**")
    
    token = st.text_input("🔑 Insira o Token da API", value="c6f5a268b3f1bc95c875a8203ad1562f47dcf0ad", help="Digite o token válido para autenticação na API.")
    
    auth_type = st.selectbox("🔒 Tipo de Autenticação", ["Bearer", "Token", "X-API-Key", "No-Prefix", "Basic"], help="Selecione o formato do header de autenticação esperado pela API.")
    
    if auth_type == "Basic":
        st.markdown("### Credenciais para Autenticação Basic")
        username = st.text_input("👤 Usuário", value="", help="Digite o nome de usuário para autenticação Basic.")
        password = st.text_input("🔒 Senha", value="", type="password", help="Digite a senha para autenticação Basic.")
    else:
        username = None
        password = None
    
    st.markdown("### Configuração de Header Personalizado (Opcional)")
    custom_header_name = st.text_input("Nome do Header Personalizado (ex.: Ocp-Apim-Subscription-Key)", value="", help="Deixe em branco se não for necessário.")
    custom_header_value = st.text_input("Valor do Header Personalizado", value="", help="Deixe em branco se não for necessário.")
    
    if st.button("🧪 Testar Conexão com a API"):
        test_api_connection(token, auth_type, custom_header_name, custom_header_value, username, password)
    
    if st.button("🔄 Iniciar Importação"):
        if not test_api_connection(token, auth_type, custom_header_name, custom_header_value, username, password):
            st.error("⚠️ Não foi possível conectar à API. Verifique o token e o tipo de autenticação antes de prosseguir.")
            return
        
        total_pages = 54
        progress_bar = st.progress(0)
        total_importados = 0
        total_erros = 0
        processed_items = 0
        items_per_page = {}

        for page in range(1, total_pages + 1):
            progress = (page - 1) / total_pages
            progress_bar.progress(progress, text=f"Processando página {page} de {total_pages}...")
            
            manutencoes_data = fetch_page_from_api(page, token, auth_type, custom_header_name, custom_header_value, username, password)
            
            if not manutencoes_data:
                items_per_page[page] = 0
                continue
            
            items_per_page[page] = len(manutencoes_data)
            
            for manutencao_data in manutencoes_data:
                processed_items += 1
                try:
                    existing_manutencao = session.query(Manutencao).filter_by(id=manutencao_data["id"]).first()
                    if existing_manutencao:
                        st.warning(f"⚠️ Manutenção ID {manutencao_data['id']} já existe na página {page}. Pulando...")
                        continue

                    required_fields = ["id", "veiculo", "categoria", "responsavel", "oficina", "data_manutencao", "data_realizacao", "hodometro_manutencao", "valor_manutencao", "status"]
                    if not all(field in manutencao_data for field in required_fields):
                        st.warning(f"⚠️ Manutenção ID {manutencao_data['id']} (Página {page}): Campos obrigatórios ausentes ou inválidos.")
                        continue

                    veiculo_id = upsert_veiculo(manutencao_data["veiculo"])
                    if veiculo_id is None:
                        st.error(f"❌ Manutenção ID {manutencao_data['id']} (Página {page}): Falha ao processar veículo associado. Pulando...")
                        continue

                    categoria_nome = upsert_categoria(manutencao_data["categoria"])
                    responsavel_nome = upsert_responsavel(manutencao_data["responsavel"])
                    oficina_nome = upsert_oficina(manutencao_data["oficina"])

                    data_manutencao = datetime.strptime(manutencao_data["data_manutencao"], "%Y-%m-%d").date()
                    data_realizacao = datetime.strptime(manutencao_data["data_realizacao"], "%Y-%m-%d").date()
                    data_vencimento = None
                    if manutencao_data.get("data_vencimento"):
                        data_vencimento = datetime.strptime(manutencao_data["data_vencimento"], "%Y-%m-%d").date()

                    km_aviso = manutencao_data.get("km_aviso") if manutencao_data.get("km_aviso") is not None else 0
                    if km_aviso is None:
                        st.warning(f"⚠️ Manutenção ID {manutencao_data['id']} (Página {page}): km_aviso ausente, usando 0.")

                    km_vencimento = manutencao_data.get("km_vencimento")

                    nova_manutencao = Manutencao(
                        id=manutencao_data["id"],
                        veiculo_id=veiculo_id,
                        categoria=categoria_nome,
                        responsavel=responsavel_nome,
                        oficina=oficina_nome,
                        tipo=manutencao_data.get("tipo", "Preventiva"),
                        km_aviso=km_aviso,
                        data_manutencao=data_manutencao,
                        hodometro_manutencao=manutencao_data["hodometro_manutencao"],
                        valor_manutencao=manutencao_data["valor_manutencao"],
                        km_vencimento=km_vencimento,
                        data_vencimento=data_vencimento,
                        vencido=manutencao_data.get("vencido", 0),
                        descricao=manutencao_data.get("descricao", ""),
                        status=manutencao_data["status"],
                        data_realizacao=data_realizacao
                    )
                    
                    session.add(nova_manutencao)
                    session.commit()
                    total_importados += 1
                    st.write(f"✅ Manutenção ID {manutencao_data['id']} da página {page} importada com sucesso!")
                
                except Exception as e:
                    session.rollback()
                    total_erros += 1
                    st.error(f"❌ Erro ao importar manutenção ID {manutencao_data.get('id', 'Desconhecido')} da página {page}: {str(e)}")
                    if "hodometro_manutencao" in str(e) and not isinstance(manutencao_data.get("hodometro_manutencao"), (int, float)):
                        st.warning(f"⚠️ Manutenção ID {manutencao_data.get('id', 'Desconhecido')} (Página {page}): Hodômetro inválido ({manutencao_data.get('hodometro_manutencao')}).")
                    if "valor_manutencao" in str(e) and not isinstance(manutencao_data.get("valor_manutencao"), (int, float)):
                        st.warning(f"⚠️ Manutenção ID {manutencao_data.get('id', 'Desconhecido')} (Página {page}): Valor inválido ({manutencao_data.get('valor_manutencao')}).")

        # Finalizar a barra de progresso
        progress_bar.progress(1.0, text="Importação concluída!")
        
        # Exibir resumo por página
        st.markdown("### Itens Processados por Página")
        for page, count in items_per_page.items():
            st.write(f"Página {page}: {count} manutenções processadas")

        # Validar total processado
        if processed_items != EXPECTED_TOTAL_MAINTENANCES:
            st.error(f"⚠️ Discrepância detectada: Foram processadas {processed_items} manutenções, mas o esperado era {EXPECTED_TOTAL_MAINTENANCES}. Verifique o log para possíveis falhas.")
        else:
            st.success(f"✅ Total de manutenções processadas ({processed_items}) corresponde ao esperado ({EXPECTED_TOTAL_MAINTENANCES}).")

        # Exibir resumo geral
        st.markdown("### Resumo da Importação")
        st.markdown(
            f"""
            <div style="background-color: #2e7d32; padding: 10px; border-radius: 5px; color: white;">
                <strong>Total de Manutenções Processadas:</strong> {processed_items}<br>
                <strong>Total de Manutenções Importadas:</strong> {total_importados}<br>
                <strong>Total de Erros:</strong> {total_erros}
            </div>
            """,
            unsafe_allow_html=True
        )

# Chamar a função principal
if __name__ == "__main__":
    importar_manutencoes()