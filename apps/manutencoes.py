import streamlit as st
import pandas as pd
import locale
from database import Session, Veiculo, Manutencao, Categoria, Responsavel, Oficina, Acessorio
from datetime import datetime, date

try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')

session = Session()

# Função auxiliar para formatar datas
def formatar_data(data):
    if data is None or data == "N/A":
        return "N/A"
    try:
        return pd.to_datetime(data).strftime('%d/%m/%Y')
    except:
        return "N/A"

def formatar_numero(numero):
    return locale.format_string("%.2f", numero, grouping=True)

def formatar_valor_monetario(valor):
    valor_formatado = f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {valor_formatado}"

@st.cache_data
def carregar_dados_veiculos():
    veiculos = session.query(Veiculo).all()
    veiculos_dict = {f"{v.codigo} - {v.placa} ({v.modelo})": v for v in veiculos}
    return veiculos_dict

@st.cache_data
def carregar_categorias():
    return [c.nome for c in session.query(Categoria).all()]

@st.cache_data
def carregar_responsaveis():
    return [r.nome for r in session.query(Responsavel).all()]

@st.cache_data
def carregar_oficinas():
    return [o.nome for o in session.query(Oficina).all()]

def verificar_duplicatas_veiculos():
    veiculos = session.query(Veiculo).all()
    codigos = [v.codigo for v in veiculos]
    placas = [v.placa for v in veiculos]
    if len(codigos) != len(set(codigos)):
        st.warning("⚠️ Existem veículos com códigos duplicados na tabela Veiculo!")
    if len(placas) != len(set(placas)):
        st.warning("⚠️ Existem veículos com placas duplicadas na tabela Veiculo!")

def adicionar_emoji_tipo(tipo):
    if tipo == "Preventiva":
        return f"🛡️ {tipo}"
    elif tipo == "Corretiva":
        return f"🔧 {tipo}"
    return tipo

def adicionar_emoji_status(status):
    if status == "concluído":
        return f"✅ {status}"
    elif status == "saudavel":
        return f"🟢 {status}"
    elif status == "alerta":
        return f"⚠️ {status}"
    elif status == "vencido":
        return f"⛔ {status}"
    elif status == "pendente":
        return f"⏳ {status}"
    return status

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
            motivo = f"Vencido por data ({registro.data_vencimento.strftime('%d/%m/%Y')})"
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

def exibir_manutencoes():
    st.title("🛠 **Gestão de Manutenções e Acessórios**")

    st.markdown("""
    <style>
    div[data-testid="stSelectbox"] { margin-bottom: 5px; }
    div[data-testid="stSelectbox"][data-baseweb="select"][aria-label="🚗 **Selecione o Veículo**"] { max-width: 350px !important; margin-bottom: 5px; }
    div[data-testid="stSelectbox"][data-baseweb="select"][aria-label="🔩 **Categoria**"],
    div[data-testid="stSelectbox"][data-baseweb="select"][aria-label="👤 **Responsável**"],
    div[data-testid="stSelectbox"][data-baseweb="select"][aria-label="🏢 **Oficina**"],
    div[data-testid="stSelectbox"][data-baseweb="select"][aria-label="🔧 **Tipo de Manutenção**"],
    div[data-testid="stTextInput"][data-baseweb="input"][aria-label="🛠 **Nome do Acessório** (ex.: pneu, bateria)"] { max-width: 200px !important; margin-bottom: 5px; }
    div[data-testid="stNumberInput"][data-baseweb="input"][aria-label="⏳ **Hodômetro**"],
    div[data-testid="stNumberInput"][data-baseweb="input"][aria-label="📏 **KM de Vencimento**"],
    div[data-testid="stNumberInput"][data-baseweb="input"][aria-label="💰 **Valor (R$)**"],
    div[data-testid="stNumberInput"][data-baseweb="input"][aria-label="⏳ **KM na Instalação**"] { max-width: 150px !important; margin-bottom: 5px; }
    div[data-testid="stDateInput"][data-baseweb="calendar"][aria-label="📅 **Data da Manutenção**"],
    div[data-testid="stDateInput"][data-baseweb="calendar"][aria-label="📅 **Data de Vencimento**"],
    div[data-testid="stDateInput"][data-baseweb="calendar"][aria-label="📅 **Data da Instalação**"] { max-width: 120px !important; margin-bottom: 5px; }
    div[data-testid="stTextArea"][data-baseweb="textarea"][aria-label="📝 **Descrição**"] { width: 100% !important; margin-bottom: 5px; }
    div[data-testid="stNumberInput"][data-baseweb="input"][aria-label="🔍 **ID para Alteração/Exclusão**"] { max-width: 100px !important; margin-bottom: 5px; }
    .disabled-field { background-color: #f0f0f0 !important; color: #a0a0a0 !important; opacity: 0.6; pointer-events: none; }
    div[data-testid="stForm"] > div > div { margin-bottom: 5px !important; padding-bottom: 0px !important; }
    div[data-testid="stHorizontalBlock"] { gap: 10px !important; }
    .info-tooltip { font-size: 12px; color: #666; margin-top: -5px; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

    submenu = st.sidebar.radio("🔍 Escolha:", ["Registrar", "Consultar"])
    verificar_duplicatas_veiculos()

    if submenu == "Registrar":
        st.subheader("🛠 **Registrar Manutenção ou Acessório**")
        veiculos_dict = carregar_dados_veiculos()
        categorias = carregar_categorias()
        responsaveis = carregar_responsaveis()
        oficinas = carregar_oficinas()
        tipo_manutencao = ["Preventiva", "Corretiva"]

        if not veiculos_dict:
            st.error("⚠️ Nenhum veículo cadastrado!")
        else:
            tipo_registro = st.radio("📋 **Tipo de Registro**", ["Manutenção", "Acessório"], index=0, horizontal=True)

            if tipo_registro == "Manutenção":
                if 'tem_vencimento' not in st.session_state:
                    st.session_state.tem_vencimento = True
                if 'logica_vencimento' not in st.session_state:
                    st.session_state.logica_vencimento = "Por Data"
                if 'edit_hodometro' not in st.session_state:
                    st.session_state.edit_hodometro = False

                tem_vencimento = st.checkbox(
                    "📅 **Possui Vencimento?**",
                    value=st.session_state.tem_vencimento,
                    key="tem_vencimento_checkbox",
                    on_change=lambda: st.session_state.update({"tem_vencimento": st.session_state.tem_vencimento_checkbox})
                )
                logica_vencimento = st.radio(
                    "📅 **Escolha a Lógica de Vencimento**",
                    ["Por Data", "Por KM"],
                    index=0 if st.session_state.logica_vencimento == "Por Data" else 1,
                    horizontal=True,
                    key="logica_vencimento_radio",
                    on_change=lambda: st.session_state.update({"logica_vencimento": st.session_state.logica_vencimento_radio})
                )

                col1, col2 = st.columns([1, 1])
                with col1:
                    st.write("⏳ **Hodômetro**")
                with col2:
                    if st.session_state.edit_hodometro:
                        if st.button("🔒 Bloquear Hodômetro", key="bloquear_hodometro"):
                            st.session_state.edit_hodometro = False
                            st.rerun()
                    else:
                        if st.button("✏️ Editar Hodômetro", key="editar_hodometro"):
                            st.session_state.edit_hodometro = True
                            st.rerun()

                with st.form(key="registro_manutencao"):
                    veiculo_selecionado = st.selectbox(
                        "🚗 **Selecione o Veículo**",
                        options=[""] + list(veiculos_dict.keys()),
                        index=0,
                        key="veiculo_manutencao"
                    )
                    veiculo = veiculos_dict.get(veiculo_selecionado)
                    hodometro_atual = veiculo.hodometro_atual if veiculo and veiculo.hodometro_atual is not None else 0.0

                    if veiculo_selecionado and hodometro_atual > 0.0:
                        st.write(f"⏳ **Hodômetro Atual do Veículo:** {formatar_numero(hodometro_atual)} km")
                    elif veiculo_selecionado:
                        st.warning("⚠️ O hodômetro atual do veículo não está definido ou é 0.0 km. Verifique os dados do veículo.")

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        data_manutencao = st.date_input(
                            "📅 **Data da Manutenção**",
                            value=date.today(),
                            key="data_manutencao"
                        )
                    with col2:
                        data_vencimento = st.date_input(
                            "📅 **Data de Vencimento**",
                            value=None,
                            min_value=date.today(),
                            disabled=not (tem_vencimento and logica_vencimento == "Por Data"),
                            key="data_vencimento_manutencao"
                        )

                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        categoria = st.selectbox(
                            "🔩 **Categoria**",
                            ["Selecione..."] + categorias,
                            key="categoria_manutencao"
                        )
                    with col2:
                        responsavel = st.selectbox(
                            "👤 **Responsável**",
                            ["Selecione..."] + responsaveis,
                            key="responsavel_manutencao"
                        )
                    with col3:
                        oficina = st.selectbox(
                            "🏢 **Oficina**",
                            ["Selecione..."] + oficinas,
                            key="oficina_manutencao"
                        )

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        tipo = st.selectbox(
                            "🔧 **Tipo de Manutenção**",
                            ["Selecione..."] + tipo_manutencao,
                            key="tipo_manutencao"
                        )
                    with col2:
                        hodometro_manutencao = st.number_input(
                            "⏳ **Hodômetro**",
                            min_value=0.0,
                            step=1.0,
                            format="%.2f",
                            value=hodometro_atual,
                            disabled=not st.session_state.edit_hodometro,
                            key="hodometro_manutencao"
                        )

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        valor_manutencao = st.number_input(
                            "💰 **Valor (R$)**",
                            min_value=0.0,
                            step=0.01,
                            format="%.2f",
                            key="valor_manutencao"
                        )
                    with col2:
                        km_vencimento_default = (hodometro_manutencao + 1000.0) if hodometro_manutencao > 0.0 else 1000.0
                        km_vencimento = st.number_input(
                            "📏 **KM de Vencimento**",
                            min_value=0.0,
                            step=1.0,
                            format="%.2f",
                            value=km_vencimento_default if tem_vencimento else 0.0,
                            disabled=not (tem_vencimento and logica_vencimento == "Por KM"),
                            key="km_vencimento_manutencao"
                        )
                        st.markdown('<div class="info-tooltip">*KM de Vencimento: Limite exato para realizar a manutenção.*</div>', unsafe_allow_html=True)

                    descricao = st.text_area(
                        "📝 **Descrição**",
                        height=100,
                        key="descricao_manutencao"
                    )

                    submit_button = st.form_submit_button(label="✅ Adicionar")

                    if submit_button:
                        if veiculo_selecionado not in veiculos_dict:
                            st.error("⚠️ Selecione um veículo válido!")
                        elif categoria == "Selecione..." or responsavel == "Selecione..." or oficina == "Selecione..." or tipo == "Selecione...":
                            st.error("⚠️ Preencha todos os campos obrigatórios!")
                        elif hodometro_manutencao == 0.0:
                            st.error("⚠️ O hodômetro deve ser maior que 0!")
                        elif tem_vencimento and logica_vencimento == "Por Data" and not data_vencimento:
                            st.error("⚠️ Informe a Data de Vencimento!")
                        elif tem_vencimento and logica_vencimento == "Por KM" and km_vencimento == 0.0:
                            st.error("⚠️ Informe o KM de Vencimento!")
                        else:
                            veiculo = veiculos_dict[veiculo_selecionado]
                            veiculo_id = veiculo.id
                            hodometro_atual = veiculo.hodometro_atual if veiculo.hodometro_atual is not None else 0.0
                            if hodometro_manutencao < hodometro_atual:
                                st.error(f"⚠️ O hodômetro informado ({hodometro_manutencao} km) é menor que o hodômetro atual do veículo ({hodometro_atual} km)!")
                            elif tem_vencimento and logica_vencimento == "Por KM" and km_vencimento <= hodometro_manutencao:
                                st.error(f"⚠️ O KM de Vencimento ({km_vencimento} km) deve ser maior que o hodômetro informado ({hodometro_manutencao} km)!")
                            else:
                                try:
                                    nova_manutencao = Manutencao(
                                        veiculo_id=veiculo_id,
                                        categoria=categoria,
                                        responsavel=responsavel,
                                        oficina=oficina,
                                        tipo=tipo,
                                        km_aviso=0.0,
                                        data_manutencao=data_manutencao,
                                        hodometro_manutencao=hodometro_manutencao,
                                        valor_manutencao=valor_manutencao,
                                        km_vencimento=km_vencimento if logica_vencimento == "Por KM" and tem_vencimento else None,
                                        data_vencimento=data_vencimento if logica_vencimento == "Por Data" and tem_vencimento else None,
                                        tem_vencimento=tem_vencimento,
                                        descricao=descricao,
                                        status="pendente" if tem_vencimento else "concluído",
                                        data_realizacao=datetime.today(),
                                        diferenca_hodometro=(hodometro_atual - hodometro_manutencao) if hodometro_atual is not None else None
                                    )
                                    session.add(nova_manutencao)
                                    session.commit()
                                    st.success(f"✅ Manutenção adicionada com sucesso para o veículo {veiculo_selecionado}!")
                                    st.session_state.tem_vencimento = True
                                    st.session_state.logica_vencimento = "Por Data"
                                    st.session_state.edit_hodometro = False
                                    st.rerun()
                                except Exception as e:
                                    session.rollback()
                                    st.error(f"❌ Erro ao adicionar: {str(e)}")

            else:
                if 'logica_vencimento' not in st.session_state:
                    st.session_state.logica_vencimento = "Por KM"
                if 'edit_km_instalacao' not in st.session_state:
                    st.session_state.edit_km_instalacao = False

                logica_vencimento = st.radio(
                    "📅 **Escolha a Lógica de Vencimento**",
                    ["Sem Vencimento", "Por KM", "Por Data"],
                    index=0 if st.session_state.logica_vencimento == "Sem Vencimento" else 1 if st.session_state.logica_vencimento == "Por KM" else 2,
                    key="logica_vencimento_radio_acessorio",
                    on_change=lambda: st.session_state.update({"logica_vencimento": st.session_state.logica_vencimento_radio_acessorio})
                )

                tem_vencimento = logica_vencimento != "Sem Vencimento"

                with st.form(key="registro_acessorio", clear_on_submit=True):
                    veiculo_selecionado = st.selectbox("🚗 **Selecione o Veículo**", options=[""] + list(veiculos_dict.keys()), index=0)
                    veiculo = veiculos_dict.get(veiculo_selecionado)
                    hodometro_atual = veiculo.hodometro_atual if veiculo and veiculo.hodometro_atual is not None else 0.0

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        nome_acessorio = st.text_input("🛠 **Nome do Acessório** (ex.: pneu, bateria)")
                    with col2:
                        data_instalacao = st.date_input("📅 **Data da Instalação**", value=date.today())

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        km_instalacao = st.number_input(
                            "⏳ **KM na Instalação**",
                            min_value=0.0,
                            step=1.0,
                            format="%.2f",
                            value=hodometro_atual,
                            disabled=not st.session_state.edit_km_instalacao
                        )
                        if st.session_state.edit_km_instalacao:
                            if st.button("🔒 Bloquear KM Instalação"):
                                st.session_state.edit_km_instalacao = False
                                st.rerun()
                        else:
                            if st.button("✏️ Editar KM Instalação"):
                                st.session_state.edit_km_instalacao = True
                                st.rerun()
                    with col2:
                        km_vencimento_default = (km_instalacao + 1000.0) if km_instalacao > 0.0 else 1000.0
                        km_vencimento = st.number_input(
                            "📏 **KM de Vencimento**",
                            min_value=0.0,
                            step=1.0,
                            format="%.2f",
                            value=km_vencimento_default if tem_vencimento else 0.0,
                            disabled=logica_vencimento != "Por KM"
                        )

                    data_vencimento = st.date_input(
                        "📅 **Data de Vencimento**",
                        value=None,
                        min_value=date.today(),
                        disabled=logica_vencimento != "Por Data"
                    )
                    descricao = st.text_area("📝 **Descrição**", height=100)
                    submit_button = st.form_submit_button(label="✅ Adicionar")

                    if submit_button:
                        if veiculo_selecionado not in veiculos_dict:
                            st.error("⚠️ Selecione um veículo válido!")
                        elif not nome_acessorio:
                            st.error("⚠️ Informe o nome do acessório!")
                        elif km_instalacao == 0.0:
                            st.error("⚠️ O KM na instalação deve ser maior que 0!")
                        elif logica_vencimento == "Por KM" and km_vencimento <= km_instalacao:
                            st.error(f"⚠️ O KM de Vencimento ({km_vencimento} km) deve ser maior que o KM na instalação ({km_instalacao} km)!")
                        elif logica_vencimento == "Por Data" and tem_vencimento and not data_vencimento:
                            st.error("⚠️ Informe a Data de Vencimento!")
                        else:
                            veiculo = veiculos_dict[veiculo_selecionado]
                            veiculo_id = veiculo.id
                            hodometro_atual = veiculo.hodometro_atual if veiculo.hodometro_atual is not None else 0.0
                            if km_instalacao < hodometro_atual:
                                st.error(f"⚠️ O KM na instalação ({km_instalacao} km) é menor que o hodômetro atual do veículo ({hodometro_atual} km)!")
                            else:
                                try:
                                    novo_acessorio = Acessorio(
                                        veiculo_id=veiculo_id,
                                        nome=nome_acessorio,
                                        km_instalacao=km_instalacao,
                                        km_vencimento=km_vencimento if logica_vencimento == "Por KM" else None,
                                        data_instalacao=data_instalacao,
                                        data_vencimento=data_vencimento if logica_vencimento == "Por Data" else None,
                                        tem_vencimento=tem_vencimento,
                                        status="pendente" if tem_vencimento else "concluído",
                                        descricao=descricao,
                                        diferenca_hodometro=(hodometro_atual - km_instalacao) if hodometro_atual is not None else None
                                    )
                                    session.add(novo_acessorio)
                                    session.commit()
                                    st.success(f"✅ Acessório {nome_acessorio} adicionado com sucesso para o veículo {veiculo_selecionado}!")
                                    st.session_state.logica_vencimento = "Por KM"
                                    st.session_state.edit_km_instalacao = False
                                    st.rerun()
                                except Exception as e:
                                    session.rollback()
                                    st.error(f"❌ Erro ao adicionar: {str(e)}")

    elif submenu == "Consultar":
        st.subheader("🔍 **Consultar Manutenções e Acessórios**")
        consulta_opcao = st.selectbox("Selecione o tipo de consulta", ["Manutenções", "Acessórios"])
        
        if consulta_opcao == "Manutenções":
            manutencoes = session.query(Manutencao).order_by(Manutencao.data_manutencao.desc()).all()
            if not manutencoes:
                st.warning("⚠️ Nenhuma manutenção cadastrada!")
            else:
                dados_manutencoes = []
                for m in manutencoes:
                    veiculo = session.query(Veiculo).filter_by(id=m.veiculo_id).first()
                    veiculo_nome = f"{veiculo.codigo} - {veiculo.placa} ({veiculo.modelo})" if veiculo else "Desconhecido"
                    hodometro_atual = veiculo.hodometro_atual if veiculo and veiculo.hodometro_atual is not None else 0.0
                    status, motivo = calcular_status(m, veiculo)
                    
                    if not hasattr(m, 'diferenca_hodometro') or m.diferenca_hodometro is None:
                        if hodometro_atual is not None and m.hodometro_manutencao is not None:
                            m.diferenca_hodometro = hodometro_atual - m.hodometro_manutencao
                            session.commit()
                        else:
                            m.diferenca_hodometro = None

                    dados_manutencoes.append({
                        "ID": m.id,
                        "Veículo": veiculo_nome,
                        "Categoria": m.categoria,
                        "Responsável": m.responsavel,
                        "Oficina": m.oficina,
                        "Tipo": adicionar_emoji_tipo(m.tipo),
                        "KM Aviso": m.km_aviso,
                        "KM Aviso (km)": f"{formatar_numero(m.km_aviso)} km",
                        "Data Manutenção": m.data_manutencao,
                        "Hodômetro Atual (km)": f"{formatar_numero(hodometro_atual)} km",
                        "Hodômetro Manutenção (km)": f"{formatar_numero(m.hodometro_manutencao)} km",
                        "Diferença Hodômetro (km)": f"{formatar_numero(m.diferenca_hodometro)} km" if m.diferenca_hodometro is not None else "N/A",
                        "Valor (R$)": m.valor_manutencao,
                        "Valor Formatado (R$)": formatar_valor_monetario(m.valor_manutencao),
                        "KM Vencimento": m.km_vencimento,
                        "KM Vencimento (km)": f"{formatar_numero(m.km_vencimento)} km" if m.km_vencimento else "N/A",
                        "Data Vencimento": m.data_vencimento if m.data_vencimento else "N/A",
                        "Descrição": m.descricao,
                        "Status": adicionar_emoji_status(status),
                        "Status Raw": status,
                        "Motivo": motivo,
                        "Data Realização": m.data_realizacao,
                        "Tem Vencimento": "Sim" if m.tem_vencimento else "Não"
                    })

                df = pd.DataFrame(dados_manutencoes)
                df = df.sort_values(by="Data Manutenção", ascending=False)
                st.markdown("### Filtros")
                with st.container():
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        filtro_veiculo = st.multiselect("🚗 Filtrar por Veículo", options=df["Veículo"].unique())
                    with col2:
                        filtro_status = st.multiselect("📋 Filtrar por Status", options=df["Status Raw"].unique())
                    with col3:
                        filtro_categoria = st.multiselect("🔩 Filtrar por Categoria", options=df["Categoria"].unique())

                st.markdown("#### Filtrar por Período (Data Manutenção)")
                with st.container():
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        data_inicio = st.date_input("📅 Data Início", value=None)
                    with col2:
                        data_fim = st.date_input("📅 Data Fim", value=None)

                df_filtrado = df.copy()
                if filtro_veiculo:
                    df_filtrado = df_filtrado[df_filtrado["Veículo"].isin(filtro_veiculo)]
                if filtro_status:
                    df_filtrado = df_filtrado[df_filtrado["Status Raw"].isin(filtro_status)]
                if filtro_categoria:
                    df_filtrado = df_filtrado[df_filtrado["Categoria"].isin(filtro_categoria)]
                if data_inicio and data_fim:
                    df_filtrado = df_filtrado[
                        (df_filtrado["Data Manutenção"] >= data_inicio) &
                        (df_filtrado["Data Manutenção"] <= data_fim)
                    ]
                elif data_inicio:
                    df_filtrado = df_filtrado[df_filtrado["Data Manutenção"] >= data_inicio]
                elif data_fim:
                    df_filtrado = df_filtrado[df_filtrado["Data Manutenção"] <= data_fim]

                if df_filtrado.empty:
                    st.warning("⚠️ Nenhum resultado encontrado com os filtros aplicados!")
                else:
                    # Formatando as colunas de data para o formato dd/mm/aaaa
                    df_filtrado["Data Manutenção"] = df_filtrado["Data Manutenção"].apply(formatar_data)
                    df_filtrado["Data Vencimento"] = df_filtrado["Data Vencimento"].apply(formatar_data)
                    df_filtrado["Data Realização"] = df_filtrado["Data Realização"].apply(formatar_data)

                    df_display = df_filtrado[[
                        "ID", "Veículo", "Categoria", "Responsável", "Oficina", "Tipo",
                        "KM Aviso (km)", "Data Manutenção", "Hodômetro Atual (km)", "Hodômetro Manutenção (km)",
                        "Diferença Hodômetro (km)", "Valor Formatado (R$)", "KM Vencimento (km)", "Data Vencimento",
                        "Descrição", "Status", "Motivo", "Data Realização", "Tem Vencimento"
                    ]]
                    st.dataframe(df_display, use_container_width=True)

                    total_manutencoes = len(df_filtrado)
                    total_valor = df_filtrado["Valor (R$)"].sum()
                    total_valor_formatado = formatar_valor_monetario(total_valor)

                    st.markdown("### Totais")
                    st.markdown(f"""
                    <div style="background-color: #2e7d32; padding: 15px; border-radius: 5px; color: white; font-size: 18px;">
                        <strong>Total de Manutenções:</strong> {total_manutencoes}<br>
                        <strong>Valor Total (R$):</strong> {total_valor_formatado}
                    </div>
                    """, unsafe_allow_html=True)

                    # Seção Alterar/Excluir para Manutenções
                    st.markdown("---")
                    st.subheader("🔧 **Alterar/Excluir Manutenções**")
                    if 'last_selected_id' not in st.session_state:
                        st.session_state.last_selected_id = 0
                        st.session_state.pop('registro_selecionado', None)
                        st.session_state.pop('tipo_registro', None)
                        st.session_state.pop('acao_selecionada', None)

                    selected_id = st.number_input("🔍 **ID para Alteração/Exclusão**", min_value=0, step=1, value=0, format="%d")

                    if st.button("🔍 Buscar"):
                        if selected_id <= 0:
                            st.warning("⚠️ Insira um ID válido maior que 0!")
                            st.session_state.pop('registro_selecionado', None)
                            st.session_state.pop('tipo_registro', None)
                            st.session_state.pop('acao_selecionada', None)
                            st.session_state.last_selected_id = 0
                        else:
                            registro = session.query(Manutencao).filter_by(id=selected_id).first()
                            if registro:
                                st.session_state['registro_selecionado'] = registro
                                st.session_state['tipo_registro'] = "Manutenção"
                                st.session_state.last_selected_id = selected_id
                                st.success(f"✅ Manutenção ID {selected_id} encontrada!")
                            else:
                                st.warning("⚠️ Nenhuma manutenção encontrada com esse ID!")
                                st.session_state.pop('registro_selecionado', None)
                                st.session_state.pop('tipo_registro', None)
                                st.session_state.pop('acao_selecionada', None)
                                st.session_state.last_selected_id = 0

                    if 'registro_selecionado' in st.session_state and st.session_state.last_selected_id == selected_id and selected_id > 0:
                        registro = st.session_state['registro_selecionado']
                        tipo_registro = st.session_state['tipo_registro']
                        veiculo = session.query(Veiculo).filter_by(id=registro.veiculo_id).first()
                        veiculo_nome = f"{veiculo.codigo} - {veiculo.placa} ({veiculo.modelo})" if veiculo else "Desconhecido"
                        hodometro_atual = veiculo.hodometro_atual if veiculo and veiculo.hodometro_atual is not None else 0.0

                        st.markdown("### 📋 **Detalhes do Registro**")
                        st.write(f"**ID:** {registro.id}")
                        st.write(f"**Veículo:** {veiculo_nome}")
                        st.write(f"**Hodômetro Atual do Veículo:** {formatar_numero(hodometro_atual)} km")
                        st.write(f"**Categoria:** {registro.categoria}")
                        st.write(f"**Responsável:** {registro.responsavel}")
                        st.write(f"**Oficina:** {registro.oficina}")
                        st.write(f"**Tipo:** {adicionar_emoji_tipo(registro.tipo)}")
                        st.write(f"**KM Aviso:** {formatar_numero(registro.km_aviso)} km")
                        st.write(f"**Data Manutenção:** {formatar_data(registro.data_manutencao)}")
                        st.write(f"**Hodômetro Manutenção:** {formatar_numero(registro.hodometro_manutencao)} km")
                        st.write(f"**Diferença Hodômetro:** {formatar_numero(registro.diferenca_hodometro)} km" if registro.diferenca_hodometro is not None else "N/A")
                        st.write(f"**Valor:** {formatar_valor_monetario(registro.valor_manutencao)}")
                        st.write(f"**KM Vencimento:** {formatar_numero(registro.km_vencimento)} km" if registro.km_vencimento else "N/A")
                        st.write(f"**Data Vencimento:** {formatar_data(registro.data_vencimento)}")
                        status, motivo = calcular_status(registro, veiculo)
                        st.write(f"**Status:** {adicionar_emoji_status(status)}")
                        st.write(f"**Motivo:** {motivo}")
                        st.write(f"**Descrição:** {registro.descricao}")
                        st.write(f"**Tem Vencimento:** {'Sim' if registro.tem_vencimento else 'Não'}")

                        acao = st.radio("🔧 **Selecione a Ação**", ["Alterar", "Excluir"], key="acao_selecionada")

                        if acao == "Alterar":
                            veiculos_dict = carregar_dados_veiculos()
                            veiculos_options = [""] + list(veiculos_dict.keys())
                            categorias = carregar_categorias()
                            responsaveis = carregar_responsaveis()
                            oficinas = carregar_oficinas()
                            tipo_manutencao = ["Preventiva", "Corretiva"]
                            status_options = ["pendente", "saudavel", "alerta", "vencido", "concluído", "cancelado"]

                            if 'alterar_tem_vencimento' not in st.session_state:
                                st.session_state.alterar_tem_vencimento = registro.tem_vencimento
                            if 'alterar_logica_vencimento' not in st.session_state:
                                st.session_state.alterar_logica_vencimento = "Por Data" if registro.data_vencimento else "Por KM" if registro.km_vencimento else "Por Data"
                            if 'alterar_edit_hodometro' not in st.session_state:
                                st.session_state.alterar_edit_hodometro = False

                            novo_tem_vencimento = st.checkbox("📅 **Possui Vencimento?**", value=st.session_state.alterar_tem_vencimento, key="alterar_tem_vencimento_checkbox", on_change=lambda: st.session_state.update({"alterar_tem_vencimento": st.session_state.alterar_tem_vencimento_checkbox}))
                            logica_vencimento = st.radio("📅 **Escolha a Lógica de Vencimento**", ["Por Data", "Por KM"], index=0 if st.session_state.alterar_logica_vencimento == "Por Data" else 1, horizontal=True, key="alterar_logica_vencimento_radio", on_change=lambda: st.session_state.update({"alterar_logica_vencimento": st.session_state.alterar_logica_vencimento_radio}))

                            with st.form(key=f"alterar_manutencao_{selected_id}"):
                                novo_veiculo = st.selectbox("🚗 **Veículo**", options=veiculos_options, index=veiculos_options.index(veiculo_nome) if veiculo_nome in veiculos_options else 0)

                                col1, col2 = st.columns([1, 1])
                                with col1:
                                    nova_data_manutencao = st.date_input("📅 **Data da Manutenção**", value=registro.data_manutencao if registro.data_manutencao else datetime.today().date())
                                with col2:
                                    nova_data_vencimento = st.date_input(
                                        "📅 **Data de Vencimento**",
                                        value=registro.data_vencimento if registro.data_vencimento else None,
                                        min_value=date.today(),
                                        disabled=not (novo_tem_vencimento and logica_vencimento == "Por Data")
                                    )

                                col1, col2, col3 = st.columns([1, 1, 1])
                                with col1:
                                    nova_categoria = st.selectbox("🔩 **Categoria**", [""] + categorias, index=categorias.index(registro.categoria) + 1 if registro.categoria in categorias else 0)
                                with col2:
                                    novo_responsavel = st.selectbox("👤 **Responsável**", [""] + responsaveis, index=responsaveis.index(registro.responsavel) + 1 if registro.responsavel in responsaveis else 0)
                                with col3:
                                    nova_oficina = st.selectbox("🏢 **Oficina**", [""] + oficinas, index=oficinas.index(registro.oficina) + 1 if registro.oficina in oficinas else 0)

                                col1, col2 = st.columns([1, 1])
                                with col1:
                                    novo_tipo = st.selectbox("🔧 **Tipo de Manutenção**", [""] + tipo_manutencao, index=tipo_manutencao.index(registro.tipo) + 1 if registro.tipo in tipo_manutencao else 0)
                                with col2:
                                    novo_hodometro_manutencao = st.number_input("⏳ **Hodômetro**", min_value=0.0, step=1.0, format="%.2f", value=registro.hodometro_manutencao, disabled=not st.session_state.alterar_edit_hodometro)
                                    if st.session_state.alterar_edit_hodometro:
                                        if st.button("🔒 Bloquear Hodômetro"):
                                            st.session_state.alterar_edit_hodometro = False
                                            st.rerun()
                                    else:
                                        if st.button("✏️ Editar Hodômetro"):
                                            st.session_state.alterar_edit_hodometro = True
                                            st.rerun()

                                col1, col2 = st.columns([1, 1])
                                with col1:
                                    novo_valor_manutencao = st.number_input("💰 **Valor da Manutenção (R$)**", min_value=0.0, step=0.01, format="%.2f", value=registro.valor_manutencao)
                                with col2:
                                    novo_km_vencimento = st.number_input(
                                        "📏 **KM de Vencimento**",
                                        min_value=0.0,
                                        step=1.0,
                                        format="%.2f",
                                        value=registro.km_vencimento if registro.km_vencimento else novo_hodometro_manutencao,
                                        disabled=not (novo_tem_vencimento and logica_vencimento == "Por KM")
                                    )
                                    st.markdown('<div class="info-tooltip">*KM de Vencimento: Limite exato para realizar a manutenção.*</div>', unsafe_allow_html=True)

                                nova_descricao = st.text_area("📝 **Descrição**", value=registro.descricao, height=100)
                                novo_status = st.selectbox("📋 **Status**", [""] + status_options, index=status_options.index(registro.status) + 1 if registro.status in status_options else 0)

                                submit_alterar_button = st.form_submit_button(label="✅ Salvar Alterações")

                                if submit_alterar_button:
                                    if not novo_veiculo or not nova_categoria or not novo_responsavel or not nova_oficina or not novo_tipo or not novo_status:
                                        st.error("⚠️ Preencha todos os campos obrigatórios!")
                                    elif novo_hodometro_manutencao == 0.0:
                                        st.error("⚠️ O hodômetro deve ser maior que 0!")
                                    elif novo_tem_vencimento and logica_vencimento == "Por Data" and not nova_data_vencimento:
                                        st.error("⚠️ Informe a Data de Vencimento!")
                                    elif novo_tem_vencimento and logica_vencimento == "Por KM" and novo_km_vencimento == 0.0:
                                        st.error("⚠️ Informe o KM de Vencimento!")
                                    else:
                                        veiculo = veiculos_dict[novo_veiculo]
                                        veiculo_id = veiculo.id
                                        hodometro_atual = veiculo.hodometro_atual if veiculo.hodometro_atual is not None else 0.0
                                        if novo_hodometro_manutencao < hodometro_atual:
                                            st.error(f"⚠️ O hodômetro informado ({novo_hodometro_manutencao} km) é menor que o hodômetro atual do veículo ({hodometro_atual} km)!")
                                        elif novo_tem_vencimento and logica_vencimento == "Por KM" and novo_km_vencimento <= novo_hodometro_manutencao:
                                            st.error(f"⚠️ O KM de Vencimento ({novo_km_vencimento} km) deve ser maior que o hodômetro informado ({novo_hodometro_manutencao} km)!")
                                        else:
                                            try:
                                                registro.veiculo_id = veiculo_id
                                                registro.categoria = nova_categoria
                                                registro.responsavel = novo_responsavel
                                                registro.oficina = nova_oficina
                                                registro.tipo = novo_tipo
                                                registro.km_aviso = registro.km_aviso if registro.km_aviso else 0.0
                                                registro.data_manutencao = nova_data_manutencao
                                                registro.hodometro_manutencao = novo_hodometro_manutencao
                                                registro.diferenca_hodometro = (hodometro_atual - novo_hodometro_manutencao) if hodometro_atual is not None else None
                                                registro.valor_manutencao = novo_valor_manutencao
                                                registro.km_vencimento = novo_km_vencimento if logica_vencimento == "Por KM" and novo_tem_vencimento else None
                                                registro.data_vencimento = nova_data_vencimento if logica_vencimento == "Por Data" and novo_tem_vencimento else None
                                                registro.tem_vencimento = novo_tem_vencimento
                                                registro.descricao = nova_descricao
                                                registro.status = novo_status
                                                session.commit()
                                                st.success(f"✅ Manutenção ID {registro.id} alterada com sucesso!")
                                                st.session_state.pop('registro_selecionado', None)
                                                st.session_state.pop('tipo_registro', None)
                                                st.session_state.pop('acao_selecionada', None)
                                                st.session_state.last_selected_id = 0
                                                st.session_state.alterar_edit_hodometro = False
                                                st.rerun()
                                            except Exception as e:
                                                session.rollback()
                                                st.error(f"❌ Erro ao alterar manutenção: {str(e)}")

                        else:  # Ação Excluir
                            if st.button("🗑️ Confirmar Exclusão"):
                                try:
                                    session.delete(registro)
                                    session.commit()
                                    st.success(f"✅ {tipo_registro} ID {selected_id} excluída com sucesso!")
                                    st.session_state.pop('registro_selecionado', None)
                                    st.session_state.pop('tipo_registro', None)
                                    st.session_state.pop('acao_selecionada', None)
                                    st.session_state.last_selected_id = 0
                                    st.rerun()
                                except Exception as e:
                                    session.rollback()
                                    st.error(f"❌ Erro ao excluir: {str(e)}")

        elif consulta_opcao == "Acessórios":
            acessorios = session.query(Acessorio).order_by(Acessorio.data_instalacao.desc()).all()
            if not acessorios:
                st.warning("⚠️ Nenhum acessório cadastrado!")
            else:
                dados_acessorios = []
                for a in acessorios:
                    veiculo = session.query(Veiculo).filter_by(id=a.veiculo_id).first()
                    veiculo_nome = f"{veiculo.codigo} - {veiculo.placa} ({veiculo.modelo})" if veiculo else "Desconhecido"
                    hodometro_atual = veiculo.hodometro_atual if veiculo and veiculo.hodometro_atual is not None else 0.0
                    status, motivo = calcular_status(a, veiculo)
                    
                    if not hasattr(a, 'diferenca_hodometro') or a.diferenca_hodometro is None:
                        if hodometro_atual is not None and a.km_instalacao is not None:
                            a.diferenca_hodometro = hodometro_atual - a.km_instalacao
                            session.commit()
                        else:
                            a.diferenca_hodometro = None

                    dados_acessorios.append({
                        "ID": a.id,
                        "Veículo": veiculo_nome,
                        "Nome": a.nome,
                        "KM Instalação": a.km_instalacao,
                        "KM Instalação (km)": f"{formatar_numero(a.km_instalacao)} km",
                        "Hodômetro Atual (km)": f"{formatar_numero(hodometro_atual)} km",
                        "Diferença Hodômetro (km)": f"{formatar_numero(a.diferenca_hodometro)} km" if a.diferenca_hodometro is not None else "N/A",
                        "KM Vencimento": a.km_vencimento,
                        "KM Vencimento (km)": f"{formatar_numero(a.km_vencimento)} km" if a.km_vencimento else "N/A",
                        "Data Instalação": a.data_instalacao,
                        "Data Vencimento": a.data_vencimento if a.data_vencimento else "N/A",
                        "Descrição": a.descricao,
                        "Status": adicionar_emoji_status(status),
                        "Status Raw": status,
                        "Motivo": motivo,
                        "Tem Vencimento": "Sim" if a.tem_vencimento else "Não"
                    })

                df = pd.DataFrame(dados_acessorios)
                df = df.sort_values(by="Data Instalação", ascending=False)
                st.markdown("### Filtros")
                with st.container():
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        filtro_veiculo = st.multiselect("🚗 Filtrar por Veículo", options=df["Veículo"].unique())
                    with col2:
                        filtro_status = st.multiselect("📋 Filtrar por Status", options=df["Status Raw"].unique())

                df_filtrado = df.copy()
                if filtro_veiculo:
                    df_filtrado = df_filtrado[df_filtrado["Veículo"].isin(filtro_veiculo)]
                if filtro_status:
                    df_filtrado = df_filtrado[df_filtrado["Status Raw"].isin(filtro_status)]

                if df_filtrado.empty:
                    st.warning("⚠️ Nenhum resultado encontrado com os filtros aplicados!")
                else:
                    # Formatando as colunas de data para o formato dd/mm/aaaa
                    df_filtrado["Data Instalação"] = df_filtrado["Data Instalação"].apply(formatar_data)
                    df_filtrado["Data Vencimento"] = df_filtrado["Data Vencimento"].apply(formatar_data)

                    df_display = df_filtrado[[
                        "ID", "Veículo", "Nome", "KM Instalação (km)", "Hodômetro Atual (km)",
                        "Diferença Hodômetro (km)", "KM Vencimento (km)", "Data Instalação", "Data Vencimento",
                        "Descrição", "Status", "Motivo", "Tem Vencimento"
                    ]]
                    st.dataframe(df_display, use_container_width=True)

                    # Seção Alterar/Excluir para Acessórios
                    st.markdown("---")
                    st.subheader("🔧 **Alterar/Excluir Acessórios**")
                    if 'last_selected_id' not in st.session_state:
                        st.session_state.last_selected_id = 0
                        st.session_state.pop('registro_selecionado', None)
                        st.session_state.pop('tipo_registro', None)
                        st.session_state.pop('acao_selecionada', None)

                    selected_id = st.number_input("🔍 **ID para Alteração/Exclusão**", min_value=0, step=1, value=0, format="%d")

                    if st.button("🔍 Buscar"):
                        if selected_id <= 0:
                            st.warning("⚠️ Insira um ID válido maior que 0!")
                            st.session_state.pop('registro_selecionado', None)
                            st.session_state.pop('tipo_registro', None)
                            st.session_state.pop('acao_selecionada', None)
                            st.session_state.last_selected_id = 0
                        else:
                            registro = session.query(Acessorio).filter_by(id=selected_id).first()
                            if registro:
                                st.session_state['registro_selecionado'] = registro
                                st.session_state['tipo_registro'] = "Acessório"
                                st.session_state.last_selected_id = selected_id
                                st.success(f"✅ Acessório ID {selected_id} encontrado!")
                            else:
                                st.warning("⚠️ Nenhum acessório encontrado com esse ID!")
                                st.session_state.pop('registro_selecionado', None)
                                st.session_state.pop('tipo_registro', None)
                                st.session_state.pop('acao_selecionada', None)
                                st.session_state.last_selected_id = 0

                    if 'registro_selecionado' in st.session_state and st.session_state.last_selected_id == selected_id and selected_id > 0:
                        registro = st.session_state['registro_selecionado']
                        tipo_registro = st.session_state['tipo_registro']
                        veiculo = session.query(Veiculo).filter_by(id=registro.veiculo_id).first()
                        veiculo_nome = f"{veiculo.codigo} - {veiculo.placa} ({veiculo.modelo})" if veiculo else "Desconhecido"
                        hodometro_atual = veiculo.hodometro_atual if veiculo and veiculo.hodometro_atual is not None else 0.0

                        st.markdown("### 📋 **Detalhes do Registro**")
                        st.write(f"**ID:** {registro.id}")
                        st.write(f"**Veículo:** {veiculo_nome}")
                        st.write(f"**Hodômetro Atual do Veículo:** {formatar_numero(hodometro_atual)} km")
                        st.write(f"**Nome do Acessório:** {registro.nome}")
                        st.write(f"**KM Instalação:** {formatar_numero(registro.km_instalacao)} km")
                        st.write(f"**Diferença Hodômetro:** {formatar_numero(registro.diferenca_hodometro)} km" if registro.diferenca_hodometro is not None else "N/A")
                        st.write(f"**KM Vencimento:** {formatar_numero(registro.km_vencimento)} km" if registro.km_vencimento else "N/A")
                        st.write(f"**Data Instalação:** {formatar_data(registro.data_instalacao)}")
                        st.write(f"**Data Vencimento:** {formatar_data(registro.data_vencimento)}")
                        status, motivo = calcular_status(registro, veiculo)
                        st.write(f"**Status:** {adicionar_emoji_status(status)}")
                        st.write(f"**Motivo:** {motivo}")
                        st.write(f"**Descrição:** {registro.descricao}")
                        st.write(f"**Tem Vencimento:** {'Sim' if registro.tem_vencimento else 'Não'}")

                        acao = st.radio("🔧 **Selecione a Ação**", ["Alterar", "Excluir"], key="acao_selecionada")

                        if acao == "Alterar":
                            veiculos_dict = carregar_dados_veiculos()
                            veiculos_options = [""] + list(veiculos_dict.keys())
                            status_options = ["pendente", "saudavel", "alerta", "vencido", "concluído", "cancelado"]

                            if 'alterar_logica_vencimento' not in st.session_state:
                                st.session_state.alterar_logica_vencimento = "Por KM" if registro.km_vencimento is not None else "Por Data" if registro.data_vencimento is not None else "Sem Vencimento"
                            if 'alterar_edit_km_instalacao' not in st.session_state:
                                st.session_state.alterar_edit_km_instalacao = False

                            logica_vencimento = st.radio(
                                "📅 **Escolha a Lógica de Vencimento**",
                                ["Sem Vencimento", "Por KM", "Por Data"],
                                index=["Sem Vencimento", "Por KM", "Por Data"].index(st.session_state.alterar_logica_vencimento),
                                key="alterar_logica_vencimento_radio",
                                on_change=lambda: st.session_state.update({"alterar_logica_vencimento": st.session_state.alterar_logica_vencimento_radio})
                            )

                            novo_tem_vencimento = logica_vencimento != "Sem Vencimento"

                            with st.form(key=f"alterar_acessorio_{selected_id}"):
                                col1, col2 = st.columns([2, 1])
                                with col1:
                                    novo_veiculo = st.selectbox("🚗 **Veículo**", options=veiculos_options, index=veiculos_options.index(veiculo_nome) if veiculo_nome in veiculos_options else 0)
                                with col2:
                                    nova_data_instalacao = st.date_input("📅 **Data da Instalação**", value=registro.data_instalacao if registro.data_instalacao else datetime.date.today())

                                col1, col2 = st.columns([1, 1])
                                with col1:
                                    novo_nome = st.text_input("🛠 **Nome do Acessório**", value=registro.nome)
                                with col2:
                                    novo_km_instalacao = st.number_input(
                                        "⏳ **KM na Instalação**",
                                        min_value=0.0,
                                        step=1.0,
                                        format="%.2f",
                                        value=registro.km_instalacao,
                                        disabled=not st.session_state.alterar_edit_km_instalacao
                                    )
                                    if st.session_state.alterar_edit_km_instalacao:
                                        if st.button("🔒 Bloquear KM Instalação"):
                                            st.session_state.alterar_edit_km_instalacao = False
                                            st.rerun()
                                    else:
                                        if st.button("✏️ Editar KM Instalação"):
                                            st.session_state.alterar_edit_km_instalacao = True
                                            st.rerun()

                                col1, col2 = st.columns([1, 1])
                                with col1:
                                    novo_km_vencimento = st.number_input(
                                        "📏 **KM de Vencimento**",
                                        min_value=0.0,
                                        step=1.0,
                                        format="%.2f",
                                        value=registro.km_vencimento if registro.km_vencimento else (novo_km_instalacao + 1000.0 if novo_km_instalacao > 0 else 1000.0),
                                        disabled=logica_vencimento != "Por KM"
                                    )
                                with col2:
                                    nova_data_vencimento = st.date_input(
                                        "📅 **Data de Vencimento**",
                                        value=registro.data_vencimento if registro.data_vencimento else None,
                                        min_value=date.today(),
                                        disabled=logica_vencimento != "Por Data"
                                    )

                                nova_descricao = st.text_area("📝 **Descrição**", value=registro.descricao, height=100)
                                novo_status = st.selectbox(
                                    "📋 **Status**",
                                    [""] + status_options,
                                    index=status_options.index(registro.status) + 1 if registro.status in status_options else 0
                                )

                                submit_alterar_button = st.form_submit_button(label="✅ Salvar Alterações")

                                if submit_alterar_button:
                                    if not novo_veiculo or not novo_nome or not novo_status:
                                        st.error("⚠️ Preencha todos os campos obrigatórios!")
                                    elif novo_km_instalacao == 0.0:
                                        st.error("⚠️ O KM na instalação deve ser maior que 0!")
                                    elif logica_vencimento == "Por KM" and novo_km_vencimento <= novo_km_instalacao:
                                        st.error(f"⚠️ O KM de Vencimento ({novo_km_vencimento} km) deve ser maior que o KM na instalação ({novo_km_instalacao} km)!")
                                    elif logica_vencimento == "Por Data" and novo_tem_vencimento and not nova_data_vencimento:
                                        st.error("⚠️ Informe a Data de Vencimento!")
                                    else:
                                        veiculo = veiculos_dict[novo_veiculo]
                                        veiculo_id = veiculo.id
                                        hodometro_atual = veiculo.hodometro_atual if veiculo.hodometro_atual is not None else 0.0
                                        if novo_km_instalacao < hodometro_atual:
                                            st.error(f"⚠️ O KM na instalação ({novo_km_instalacao} km) é menor que o hodômetro atual do veículo ({hodometro_atual} km)!")
                                        else:
                                            try:
                                                registro.veiculo_id = veiculo_id
                                                registro.nome = novo_nome
                                                registro.km_instalacao = novo_km_instalacao
                                                registro.km_vencimento = novo_km_vencimento if logica_vencimento == "Por KM" else None
                                                registro.data_instalacao = nova_data_instalacao
                                                registro.data_vencimento = nova_data_vencimento if logica_vencimento == "Por Data" else None
                                                registro.tem_vencimento = novo_tem_vencimento
                                                registro.descricao = nova_descricao
                                                registro.status = novo_status
                                                registro.diferenca_hodometro = (hodometro_atual - novo_km_instalacao) if hodometro_atual is not None else None
                                                session.commit()
                                                st.success(f"✅ Acessório ID {registro.id} alterado com sucesso!")
                                                st.session_state.pop('registro_selecionado', None)
                                                st.session_state.pop('tipo_registro', None)
                                                st.session_state.pop('acao_selecionada', None)
                                                st.session_state.last_selected_id = 0
                                                st.session_state.alterar_edit_km_instalacao = False
                                                st.rerun()
                                            except Exception as e:
                                                session.rollback()
                                                st.error(f"❌ Erro ao alterar acessório: {str(e)}")

                        else:  # Ação Excluir
                            if st.button("🗑️ Confirmar Exclusão"):
                                try:
                                    session.delete(registro)
                                    session.commit()
                                    st.success(f"✅ {tipo_registro} ID {selected_id} excluída com sucesso!")
                                    st.session_state.pop('registro_selecionado', None)
                                    st.session_state.pop('tipo_registro', None)
                                    st.session_state.pop('acao_selecionada', None)
                                    st.session_state.last_selected_id = 0
                                    st.rerun()
                                except Exception as e:
                                    session.rollback()
                                    st.error(f"❌ Erro ao excluir: {str(e)}")

if __name__ == "__main__":
    exibir_manutencoes()