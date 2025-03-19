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

def formatar_numero(numero):
    return locale.format_string("%.2f", numero, grouping=True)

def formatar_valor_monetario(valor):
    valor_formatado = f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {valor_formatado}"

def exibir_manutencoes():
    st.title("🛠 **Gestão de Manutenções e Acessórios**")

    # CSS para ajustar tamanhos dos campos e reduzir espaços
    st.markdown("""
    <style>
    /* Ajuste geral para selectbox */
    div[data-testid="stSelectbox"] {
        margin-bottom: 5px;
    }
    /* Aumentar o campo Veículo */
    div[data-testid="stSelectbox"][data-baseweb="select"][aria-label="🚗 **Selecione o Veículo**"] {
        max-width: 350px !important;
        margin-bottom: 5px;
    }
    /* Ajuste para campos de texto curto (Categoria, Responsável, Oficina, Tipo, Nome do Acessório) */
    div[data-testid="stSelectbox"][data-baseweb="select"][aria-label="🔩 **Categoria**"],
    div[data-testid="stSelectbox"][data-baseweb="select"][aria-label="👤 **Responsável**"],
    div[data-testid="stSelectbox"][data-baseweb="select"][aria-label="🏢 **Oficina**"],
    div[data-testid="stSelectbox"][data-baseweb="select"][aria-label="🔧 **Tipo de Manutenção**"],
    div[data-testid="stTextInput"][data-baseweb="input"][aria-label="🛠 **Nome do Acessório** (ex.: pneu, bateria)"] {
        max-width: 200px !important;
        margin-bottom: 5px;
    }
    /* Ajuste para campos numéricos (Hodômetro, KM Vencimento, Valor) */
    div[data-testid="stNumberInput"][data-baseweb="input"][aria-label="⏳ **Hodômetro**"],
    div[data-testid="stNumberInput"][data-baseweb="input"][aria-label="📏 **KM de Vencimento**"],
    div[data-testid="stNumberInput"][data-baseweb="input"][aria-label="💰 **Valor (R$)**"],
    div[data-testid="stNumberInput"][data-baseweb="input"][aria-label="⏳ **KM na Instalação**"] {
        max-width: 150px !important;
        margin-bottom: 5px;
    }
    /* Ajuste para campos de data */
    div[data-testid="stDateInput"][data-baseweb="calendar"][aria-label="📅 **Data da Manutenção**"],
    div[data-testid="stDateInput"][data-baseweb="calendar"][aria-label="📅 **Data de Vencimento**"],
    div[data-testid="stDateInput"][data-baseweb="calendar"][aria-label="📅 **Data da Instalação**"] {
        max-width: 120px !important;
        margin-bottom: 5px;
    }
    /* Ajuste para campo de descrição (text_area) */
    div[data-testid="stTextArea"][data-baseweb="textarea"][aria-label="📝 **Descrição**"] {
        width: 100% !important;
        margin-bottom: 5px;
    }
    /* Ajuste para campo de ID na consulta */
    div[data-testid="stNumberInput"][data-baseweb="input"][aria-label="🔍 **ID para Alteração/Exclusão**"] {
        max-width: 100px !important;
        margin-bottom: 5px;
    }
    /* Estilo para campos desativados */
    .disabled-field {
        background-color: #f0f0f0 !important;
        color: #a0a0a0 !important;
        opacity: 0.6;
        pointer-events: none;
    }
    /* Reduzir margens entre elementos */
    div[data-testid="stForm"] > div > div {
        margin-bottom: 5px !important;
        padding-bottom: 0px !important;
    }
    div[data-testid="stHorizontalBlock"] {
        gap: 10px !important;
    }
    /* Informações sobre KM de Vencimento */
    .info-tooltip {
        font-size: 12px;
        color: #666;
        margin-top: -5px;
        margin-bottom: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

    submenu = st.sidebar.radio("🔍 Escolha:", ["Registrar", "Alterar/Excluir", "Consultar"])

    if submenu == "Registrar":
        st.subheader("🛠 **Registrar Manutenção ou Acessório**")

        veiculos = session.query(Veiculo).all()
        veiculos_dict = {f"{v.codigo} - {v.placa} ({v.modelo})": v.id for v in veiculos}

        categorias = [c.nome for c in session.query(Categoria).all()]
        responsaveis = [r.nome for r in session.query(Responsavel).all()]
        oficinas = [o.nome for o in session.query(Oficina).all()]
        tipo_manutencao = ["Preventiva", "Corretiva"]

        if not veiculos_dict:
            st.error("⚠️ Nenhum veículo cadastrado!")
        else:
            # Tipo de Registro
            tipo_registro = st.radio("📋 **Tipo de Registro**", ["Manutenção", "Acessório"], index=0, horizontal=True)

            if tipo_registro == "Manutenção":
                # Controles fora do formulário para reatividade
                if 'tem_vencimento' not in st.session_state:
                    st.session_state.tem_vencimento = True
                if 'logica_vencimento' not in st.session_state:
                    st.session_state.logica_vencimento = "Por Data"

                tem_vencimento = st.checkbox("📅 **Possui Vencimento?**", value=st.session_state.tem_vencimento, key="tem_vencimento_checkbox", on_change=lambda: st.session_state.update({"tem_vencimento": st.session_state.tem_vencimento_checkbox}))
                logica_vencimento = st.radio("📅 **Escolha a Lógica de Vencimento**", ["Por Data", "Por KM"], index=0 if st.session_state.logica_vencimento == "Por Data" else 1, horizontal=True, key="logica_vencimento_radio", on_change=lambda: st.session_state.update({"logica_vencimento": st.session_state.logica_vencimento_radio}))

                with st.form(key="registro_manutencao", clear_on_submit=True):
                    # Linha 1: Veículo
                    veiculo_selecionado = st.selectbox("🚗 **Selecione o Veículo**", options=[""] + list(veiculos_dict.keys()), index=0)

                    # Linha 2: Data da Manutenção e Data de Vencimento
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        data_manutencao = st.date_input("📅 **Data da Manutenção**", value=date.today())
                    with col2:
                        data_vencimento = st.date_input("📅 **Data de Vencimento**", value=None, min_value=date.today(), disabled=not (tem_vencimento and logica_vencimento == "Por Data"))

                    # Linha 3: Categoria, Responsável, Oficina
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        categoria = st.selectbox("🔩 **Categoria**", ["Selecione..."] + categorias)
                    with col2:
                        responsavel = st.selectbox("👤 **Responsável**", ["Selecione..."] + responsaveis)
                    with col3:
                        oficina = st.selectbox("🏢 **Oficina**", ["Selecione..."] + oficinas)

                    # Linha 4: Tipo, Hodômetro
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        tipo = st.selectbox("🔧 **Tipo de Manutenção**", ["Selecione..."] + tipo_manutencao)
                    with col2:
                        hodometro_manutencao = st.number_input("⏳ **Hodômetro**", min_value=0.0, step=1.0, format="%.2f")

                    # Linha 5: Valor, KM de Vencimento
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        valor_manutencao = st.number_input("💰 **Valor (R$)**", min_value=0.0, step=0.01, format="%.2f")
                    with col2:
                        km_vencimento = st.number_input("📏 **KM de Vencimento**", min_value=0.0, step=1.0, format="%.2f", value=hodometro_manutencao if tem_vencimento else 0.0, disabled=not (tem_vencimento and logica_vencimento == "Por KM"))
                        st.markdown('<div class="info-tooltip">*KM de Vencimento: Limite exato para realizar a manutenção.*</div>', unsafe_allow_html=True)

                    # Linha 6: Descrição
                    descricao = st.text_area("📝 **Descrição**", height=100)

                    submit_button = st.form_submit_button(label="✅ **Adicionar**")

                if submit_button:
                    if veiculo_selecionado not in veiculos_dict:
                        st.error("⚠️ Selecione um veículo válido!")
                    elif categoria == "Selecione..." or responsavel == "Selecione..." or oficina == "Selecione..." or tipo == "Selecione...":
                        st.error("⚠️ Preencha todos os campos obrigatórios!")
                    elif tem_vencimento and logica_vencimento == "Por Data" and not data_vencimento:
                        st.error("⚠️ Informe a Data de Vencimento!")
                    elif tem_vencimento and logica_vencimento == "Por KM" and km_vencimento == 0.0:
                        st.error("⚠️ Informe o KM de Vencimento!")
                    else:
                        veiculo_id = veiculos_dict[veiculo_selecionado]
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
                                data_realizacao=datetime.today()
                            )
                            session.add(nova_manutencao)
                            session.commit()
                            st.success(f"✅ Manutenção adicionada com sucesso para o veículo {veiculo_selecionado}!")
                            st.session_state.tem_vencimento = True
                            st.session_state.logica_vencimento = "Por Data"
                        except Exception as e:
                            session.rollback()
                            st.error(f"❌ Erro ao adicionar: {str(e)}")

            else:  # Acessório
                if 'vence_por_km' not in st.session_state:
                    st.session_state.vence_por_km = True
                if 'vence_por_data' not in st.session_state:
                    st.session_state.vence_por_data = False

                vence_por_km = st.checkbox("📏 **Vencimento por KM?**", value=st.session_state.vence_por_km, key="vence_por_km_checkbox", on_change=lambda: st.session_state.update({"vence_por_km": st.session_state.vence_por_km_checkbox}))
                vence_por_data = st.checkbox("📅 **Vencimento por Data?**", value=st.session_state.vence_por_data, key="vence_por_data_checkbox", on_change=lambda: st.session_state.update({"vence_por_data": st.session_state.vence_por_data_checkbox}))

                if vence_por_km and vence_por_data:
                    st.warning("⚠️ Escolha apenas um tipo de vencimento (KM ou Data). Desmarque um dos dois.")
                    tem_vencimento = False
                else:
                    tem_vencimento = vence_por_km or vence_por_data

                with st.form(key="registro_acessorio", clear_on_submit=True):
                    veiculo_selecionado = st.selectbox("🚗 **Selecione o Veículo**", options=[""] + list(veiculos_dict.keys()), index=0)

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        nome_acessorio = st.text_input("🛠 **Nome do Acessório** (ex.: pneu, bateria)")
                    with col2:
                        data_instalacao = st.date_input("📅 **Data da Instalação**", value=date.today())

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        km_instalacao = st.number_input("⏳ **KM na Instalação**", min_value=0.0, step=1.0, format="%.2f")
                    with col2:
                        km_vencimento = st.number_input("📏 **KM de Vencimento**", min_value=0.0, step=1.0, format="%.2f", disabled=not vence_por_km)

                    data_vencimento = st.date_input("📅 **Data de Vencimento**", value=None, min_value=date.today(), disabled=not vence_por_data)

                    descricao = st.text_area("📝 **Descrição**", height=100)

                    submit_button = st.form_submit_button(label="✅ **Adicionar**")

                if submit_button:
                    if veiculo_selecionado not in veiculos_dict:
                        st.error("⚠️ Selecione um veículo válido!")
                    elif not nome_acessorio:
                        st.error("⚠️ Informe o nome do acessório!")
                    elif vence_por_km and vence_por_data:
                        st.error("⚠️ Escolha apenas um tipo de vencimento (KM ou Data).")
                    else:
                        veiculo_id = veiculos_dict[veiculo_selecionado]
                        try:
                            novo_acessorio = Acessorio(
                                veiculo_id=veiculo_id,
                                nome=nome_acessorio,
                                km_instalacao=km_instalacao,
                                km_vencimento=km_vencimento if vence_por_km else None,
                                data_instalacao=data_instalacao,
                                data_vencimento=data_vencimento if vence_por_data else None,
                                tem_vencimento=tem_vencimento,
                                status="pendente" if tem_vencimento else "concluído",
                                descricao=descricao
                            )
                            session.add(novo_acessorio)
                            session.commit()
                            st.success(f"✅ Acessório {nome_acessorio} adicionado com sucesso para o veículo {veiculo_selecionado}!")
                            st.session_state.vence_por_km = True
                            st.session_state.vence_por_data = False
                        except Exception as e:
                            session.rollback()
                            st.error(f"❌ Erro ao adicionar: {str(e)}")

    elif submenu == "Consultar":
        st.subheader("🔍 **Consultar Manutenções e Acessórios**")

        consulta_opcao = st.selectbox("Selecione o tipo de consulta", ["Manutenções", "Acessórios"])
        
        if consulta_opcao == "Manutenções":
            manutencoes = session.query(Manutencao).all()
            if not manutencoes:
                st.warning("⚠️ Nenhuma manutenção cadastrada!")
            else:
                dados_manutencoes = []
                for m in manutencoes:
                    veiculo = session.query(Veiculo).filter_by(id=m.veiculo_id).first()
                    veiculo_nome = f"{veiculo.codigo} - {veiculo.placa} ({veiculo.modelo})" if veiculo else "Desconhecido"
                    dados_manutencoes.append({
                        "ID": m.id,
                        "Veículo": veiculo_nome,
                        "Categoria": m.categoria,
                        "Responsável": m.responsavel,
                        "Oficina": m.oficina,
                        "Tipo": m.tipo,
                        "KM Aviso": m.km_aviso,
                        "KM Aviso (km)": f"{formatar_numero(m.km_aviso)} km",
                        "Data Manutenção": m.data_manutencao,
                        "Hodômetro": m.hodometro_manutencao,
                        "Hodômetro (km)": f"{formatar_numero(m.hodometro_manutencao)} km",
                        "Valor (R$)": m.valor_manutencao,
                        "Valor Formatado (R$)": formatar_valor_monetario(m.valor_manutencao),
                        "KM Vencimento": m.km_vencimento,
                        "KM Vencimento (km)": f"{formatar_numero(m.km_vencimento)} km" if m.km_vencimento else "N/A",
                        "Data Vencimento": m.data_vencimento if m.data_vencimento else "N/A",
                        "Descrição": m.descricao,
                        "Status": m.status,
                        "Data Realização": m.data_realizacao,
                        "Tem Vencimento": "Sim" if m.tem_vencimento else "Não"
                    })

                df = pd.DataFrame(dados_manutencoes)

                st.markdown("### Filtros")
                with st.container():
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        filtro_veiculo = st.multiselect("🚗 Filtrar por Veículo", options=df["Veículo"].unique())
                    with col2:
                        filtro_status = st.multiselect("📋 Filtrar por Status", options=df["Status"].unique())
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
                    df_filtrado = df_filtrado[df_filtrado["Status"].isin(filtro_status)]
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
                    df_display = df_filtrado[[
                        "ID", "Veículo", "Categoria", "Responsável", "Oficina", "Tipo",
                        "KM Aviso (km)", "Data Manutenção", "Hodômetro (km)", "Valor Formatado (R$)",
                        "KM Vencimento (km)", "Data Vencimento", "Descrição", "Status", "Data Realização", "Tem Vencimento"
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

        elif consulta_opcao == "Acessórios":
            acessorios = session.query(Acessorio).all()
            if not acessorios:
                st.warning("⚠️ Nenhum acessório cadastrado!")
            else:
                dados_acessorios = []
                for a in acessorios:
                    veiculo = session.query(Veiculo).filter_by(id=a.veiculo_id).first()
                    veiculo_nome = f"{veiculo.codigo} - {veiculo.placa} ({veiculo.modelo})" if veiculo else "Desconhecido"
                    dados_acessorios.append({
                        "ID": a.id,
                        "Veículo": veiculo_nome,
                        "Nome": a.nome,
                        "KM Instalação": a.km_instalacao,
                        "KM Instalação (km)": f"{formatar_numero(a.km_instalacao)} km",
                        "KM Vencimento": a.km_vencimento,
                        "KM Vencimento (km)": f"{formatar_numero(a.km_vencimento)} km" if a.km_vencimento else "N/A",
                        "Data Instalação": a.data_instalacao,
                        "Data Vencimento": a.data_vencimento if a.data_vencimento else "N/A",
                        "Descrição": a.descricao,
                        "Status": a.status,
                        "Tem Vencimento": "Sim" if a.tem_vencimento else "Não"
                    })

                df = pd.DataFrame(dados_acessorios)

                st.markdown("### Filtros")
                with st.container():
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        filtro_veiculo = st.multiselect("🚗 Filtrar por Veículo", options=df["Veículo"].unique())
                    with col2:
                        filtro_status = st.multiselect("📋 Filtrar por Status", options=df["Status"].unique())

                df_filtrado = df.copy()
                if filtro_veiculo:
                    df_filtrado = df_filtrado[df_filtrado["Veículo"].isin(filtro_veiculo)]
                if filtro_status:
                    df_filtrado = df_filtrado[df_filtrado["Status"].isin(filtro_status)]

                if df_filtrado.empty:
                    st.warning("⚠️ Nenhum resultado encontrado com os filtros aplicados!")
                else:
                    df_display = df_filtrado[[
                        "ID", "Veículo", "Nome", "KM Instalação (km)", "KM Vencimento (km)",
                        "Data Instalação", "Data Vencimento", "Descrição", "Status", "Tem Vencimento"
                    ]]
                    st.dataframe(df_display, use_container_width=True)

    elif submenu == "Alterar/Excluir":
        st.subheader("🔧 **Alterar/Excluir Manutenções e Acessórios**")

        # Limpar o session_state ao entrar no submenu para evitar exibição de registros antigos
        if 'last_selected_id' not in st.session_state:
            st.session_state.last_selected_id = 0
            st.session_state.pop('registro_selecionado', None)
            st.session_state.pop('tipo_registro', None)
            st.session_state.pop('acao_selecionada', None)

        consulta_opcao = st.selectbox("Selecione o tipo de registro", ["Manutenções", "Acessórios"])

        # Busca por ID
        selected_id = st.number_input("🔍 **ID para Alteração/Exclusão**", min_value=0, step=1, value=0, format="%d")

        if st.button("🔍 Buscar"):
            if selected_id <= 0:
                st.warning("⚠️ Insira um ID válido maior que 0!")
                st.session_state.pop('registro_selecionado', None)
                st.session_state.pop('tipo_registro', None)
                st.session_state.pop('acao_selecionada', None)
                st.session_state.last_selected_id = 0
            else:
                if consulta_opcao == "Manutenções":
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

        # Exibição de Detalhes e Seleção de Ação somente se houver um registro selecionado e o ID for válido
        if 'registro_selecionado' in st.session_state and st.session_state.last_selected_id == selected_id and selected_id > 0:
            registro = st.session_state['registro_selecionado']
            tipo_registro = st.session_state['tipo_registro']
            veiculo = session.query(Veiculo).filter_by(id=registro.veiculo_id).first()
            veiculo_nome = f"{veiculo.codigo} - {veiculo.placa} ({veiculo.modelo})" if veiculo else "Desconhecido"

            st.markdown("### 📋 **Detalhes do Registro**")
            st.write(f"**ID:** {registro.id}")
            st.write(f"**Veículo:** {veiculo_nome}")
            if tipo_registro == "Manutenção":
                st.write(f"**Categoria:** {registro.categoria}")
                st.write(f"**Responsável:** {registro.responsavel}")
                st.write(f"**Oficina:** {registro.oficina}")
                st.write(f"**Tipo:** {registro.tipo}")
                st.write(f"**KM Aviso:** {formatar_numero(registro.km_aviso)} km")
                st.write(f"**Data Manutenção:** {registro.data_manutencao}")
                st.write(f"**Hodômetro:** {formatar_numero(registro.hodometro_manutencao)} km")
                st.write(f"**Valor:** {formatar_valor_monetario(registro.valor_manutencao)}")
                st.write(f"**KM Vencimento:** {formatar_numero(registro.km_vencimento)} km" if registro.km_vencimento else "N/A")
                st.write(f"**Data Vencimento:** {registro.data_vencimento if registro.data_vencimento else 'N/A'}")
                st.write(f"**Status:** {registro.status}")
            else:
                st.write(f"**Nome do Acessório:** {registro.nome}")
                st.write(f"**KM Instalação:** {formatar_numero(registro.km_instalacao)} km")
                st.write(f"**KM Vencimento:** {formatar_numero(registro.km_vencimento)} km" if registro.km_vencimento else "N/A")
                st.write(f"**Data Instalação:** {registro.data_instalacao}")
                st.write(f"**Data Vencimento:** {registro.data_vencimento if registro.data_vencimento else 'N/A'}")
                st.write(f"**Status:** {registro.status}")
            st.write(f"**Descrição:** {registro.descricao}")
            st.write(f"**Tem Vencimento:** {'Sim' if registro.tem_vencimento else 'Não'}")

            acao = st.radio("🔧 **Selecione a Ação**", ["Alterar", "Excluir"], key="acao_selecionada")

            if acao == "Alterar":
                if tipo_registro == "Manutenção":
                    veiculos = session.query(Veiculo).all()
                    veiculos_dict = {f"{v.codigo} - {v.placa} ({v.modelo})": v.id for v in veiculos}
                    veiculos_options = [""] + list(veiculos_dict.keys())
                    categorias = [c.nome for c in session.query(Categoria).all()]
                    responsaveis = [r.nome for r in session.query(Responsavel).all()]
                    oficinas = [o.nome for o in session.query(Oficina).all()]
                    tipo_manutencao = ["Preventiva", "Corretiva"]
                    status_options = ["pendente", "saudavel", "alerta", "vencido", "concluído", "cancelado"]

                    if 'alterar_tem_vencimento' not in st.session_state:
                        st.session_state.alterar_tem_vencimento = registro.tem_vencimento
                    if 'alterar_logica_vencimento' not in st.session_state:
                        st.session_state.alterar_logica_vencimento = "Por Data" if registro.data_vencimento else "Por KM" if registro.km_vencimento else "Por Data"

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
                            novo_hodometro_manutencao = st.number_input("⏳ **Hodômetro**", min_value=0.0, step=1.0, format="%.2f", value=registro.hodometro_manutencao)

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

                        submit_alterar_button = st.form_submit_button(label="✅ **Salvar Alterações**")

                        if submit_alterar_button:
                            if not novo_veiculo or not nova_categoria or not novo_responsavel or not nova_oficina or not novo_tipo or not novo_status:
                                st.error("⚠️ Preencha todos os campos obrigatórios!")
                            elif novo_tem_vencimento and logica_vencimento == "Por Data" and not nova_data_vencimento:
                                st.error("⚠️ Informe a Data de Vencimento!")
                            elif novo_tem_vencimento and logica_vencimento == "Por KM" and novo_km_vencimento == 0.0:
                                st.error("⚠️ Informe o KM de Vencimento!")
                            else:
                                veiculo_id = veiculos_dict[novo_veiculo]
                                try:
                                    registro.veiculo_id = veiculo_id
                                    registro.categoria = nova_categoria
                                    registro.responsavel = novo_responsavel
                                    registro.oficina = nova_oficina
                                    registro.tipo = novo_tipo
                                    registro.km_aviso = registro.km_aviso if registro.km_aviso else 0.0
                                    registro.data_manutencao = nova_data_manutencao
                                    registro.hodometro_manutencao = novo_hodometro_manutencao
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
                                    st.rerun()
                                except Exception as e:
                                    session.rollback()
                                    st.error(f"❌ Erro ao alterar manutenção: {str(e)}")

                else:  # Acessório
                    veiculos = session.query(Veiculo).all()
                    veiculos_dict = {f"{v.codigo} - {v.placa} ({v.modelo})": v.id for v in veiculos}
                    veiculos_options = [""] + list(veiculos_dict.keys())
                    status_options = ["pendente", "saudavel", "alerta", "vencido", "concluído", "cancelado"]

                    if 'alterar_vence_por_km' not in st.session_state:
                        st.session_state.alterar_vence_por_km = registro.km_vencimento is not None
                    if 'alterar_vence_por_data' not in st.session_state:
                        st.session_state.alterar_vence_por_data = registro.data_vencimento is not None

                    vence_por_km = st.checkbox("📏 **Vencimento por KM?**", value=st.session_state.alterar_vence_por_km, key="alterar_vence_por_km_checkbox", on_change=lambda: st.session_state.update({"alterar_vence_por_km": st.session_state.alterar_vence_por_km_checkbox}))
                    vence_por_data = st.checkbox("📅 **Vencimento por Data?**", value=st.session_state.alterar_vence_por_data, key="alterar_vence_por_data_checkbox", on_change=lambda: st.session_state.update({"alterar_vence_por_data": st.session_state.alterar_vence_por_data_checkbox}))

                    if vence_por_km and vence_por_data:
                        st.warning("⚠️ Escolha apenas um tipo de vencimento (KM ou Data). Desmarque um dos dois.")
                        novo_tem_vencimento = False
                    else:
                        novo_tem_vencimento = vence_por_km or vence_por_data

                    with st.form(key=f"alterar_acessorio_{selected_id}"):
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            novo_veiculo = st.selectbox("🚗 **Veículo**", options=veiculos_options, index=veiculos_options.index(veiculo_nome) if veiculo_nome in veiculos_options else 0)
                        with col2:
                            nova_data_instalacao = st.date_input("📅 **Data da Instalação**", value=registro.data_instalacao if registro.data_instalacao else datetime.today().date())

                        col1, col2 = st.columns([1, 1])
                        with col1:
                            novo_nome = st.text_input("🛠 **Nome do Acessório**", value=registro.nome)
                        with col2:
                            novo_km_instalacao = st.number_input("⏳ **KM na Instalação**", min_value=0.0, step=1.0, format="%.2f", value=registro.km_instalacao)

                        col1, col2 = st.columns([1, 1])
                        with col1:
                            pass
                        with col2:
                            novo_km_vencimento = st.number_input("📏 **KM de Vencimento**", min_value=0.0, step=1.0, format="%.2f", value=registro.km_vencimento if registro.km_vencimento else 0.0, disabled=not vence_por_km)

                        nova_data_vencimento = st.date_input("📅 **Data de Vencimento**", value=registro.data_vencimento if registro.data_vencimento else datetime.today().date(), min_value=date.today(), disabled=not vence_por_data)

                        nova_descricao = st.text_area("📝 **Descrição**", value=registro.descricao, height=100)
                        novo_status = st.selectbox("📋 **Status**", [""] + status_options, index=status_options.index(registro.status) + 1 if registro.status in status_options else 0)

                        submit_alterar_button = st.form_submit_button(label="✅ **Salvar Alterações**")

                        if submit_alterar_button:
                            if not novo_veiculo or not novo_nome or not novo_status:
                                st.error("⚠️ Preencha todos os campos obrigatórios!")
                            elif vence_por_km and vence_por_data:
                                st.error("⚠️ Escolha apenas um tipo de vencimento (KM ou Data).")
                            else:
                                veiculo_id = veiculos_dict[novo_veiculo]
                                try:
                                    registro.veiculo_id = veiculo_id
                                    registro.nome = novo_nome
                                    registro.km_instalacao = novo_km_instalacao
                                    registro.km_vencimento = novo_km_vencimento if vence_por_km else None
                                    registro.data_instalacao = nova_data_instalacao
                                    registro.data_vencimento = nova_data_vencimento if vence_por_data else None
                                    registro.tem_vencimento = novo_tem_vencimento
                                    registro.descricao = nova_descricao
                                    registro.status = novo_status
                                    session.commit()
                                    st.success(f"✅ Acessório ID {registro.id} alterado com sucesso!")
                                    st.session_state.pop('registro_selecionado', None)
                                    st.session_state.pop('tipo_registro', None)
                                    st.session_state.pop('acao_selecionada', None)
                                    st.session_state.last_selected_id = 0
                                    st.rerun()
                                except Exception as e:
                                    session.rollback()
                                    st.error(f"❌ Erro ao alterar acessório: {str(e)}")

            elif acao == "Excluir":
                st.info("ℹ️ Esta ação é irreversível. Confirme antes de excluir.")
                if st.button(f"Confirme a exclusão do {tipo_registro.lower()} ID {registro.id} (Veículo: {veiculo_nome})"):
                    try:
                        session.delete(registro)
                        session.commit()
                        st.success(f"✅ {tipo_registro} ID {registro.id} excluído com sucesso!")
                        st.session_state.pop('registro_selecionado', None)
                        st.session_state.pop('tipo_registro', None)
                        st.session_state.pop('acao_selecionada', None)
                        st.session_state.last_selected_id = 0
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error(f"❌ Erro ao excluir {tipo_registro.lower()}: {str(e)}")

    if st.button("🏠 Home"):
        st.session_state['menu_principal'] = "Dashboard"
        st.rerun()

if __name__ == "__main__":
    exibir_manutencoes()