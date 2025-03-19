import pandas as pd
import streamlit as st
from database import Session, Veiculo, Categoria, Responsavel, Oficina

# Inicializar a sessão
session = Session()

def exibir_cadastros():
    st.title("📋 **Cadastros**")

    submenu = st.sidebar.radio("🔍 Escolha:", ["Veículos", "Categorias", "Responsáveis", "Oficinas"])

    if submenu == "Veículos":
        st.subheader("🚗 **Cadastro de Veículos**")

        with st.form(key="cadastro_veiculo", clear_on_submit=True):
            codigo = st.number_input("🔢 **Código**", min_value=1, step=1)
            placa = st.text_input("📜 **Placa**")
            modelo = st.text_input("🚘 **Modelo**")
            fabricante = st.text_input("🏭 **Fabricante**")
            hodometro_atual = st.number_input("⏳ **Hodômetro Atual (km)**", min_value=0.0, step=1.0, format="%.2f")
            submit_button = st.form_submit_button(label="✅ **Cadastrar Veículo**")

            if submit_button:
                if not placa or not modelo or not fabricante:
                    st.error("⚠️ Preencha todos os campos obrigatórios!")
                else:
                    try:
                        novo_veiculo = Veiculo(
                            codigo=codigo,
                            placa=placa.upper(),
                            modelo=modelo,
                            fabricante=fabricante,
                            hodometro_atual=hodometro_atual
                        )
                        session.add(novo_veiculo)
                        session.commit()
                        st.success(f"✅ Veículo {placa} cadastrado com sucesso!")
                    except Exception as e:
                        session.rollback()
                        st.error(f"❌ Erro ao cadastrar veículo: {str(e)}")

        st.markdown("### 🚗 **Veículos Cadastrados**")
        veiculos = session.query(Veiculo).all()
        if not veiculos:
            st.warning("⚠️ Nenhum veículo cadastrado!")
        else:
            dados_veiculos = []
            for v in veiculos:
                dados_veiculos.append({
                    "ID": v.id,
                    "Código": v.codigo,
                    "Placa": v.placa,
                    "Modelo": v.modelo,
                    "Fabricante": v.fabricante,
                    "Hodômetro Atual (km)": f"{v.hodometro_atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                })
            df = pd.DataFrame(dados_veiculos)
            st.dataframe(df, use_container_width=True)

        # Busca, Alteração e Exclusão
        st.subheader("🔍 **Gerenciar Veículo**")
        id_busca = st.number_input("🔎 **ID do Veículo para Busca/Edição/Exclusão**", min_value=0, step=1, value=0, format="%d", key="busca_veiculo")
        if st.button("🔍 Buscar"):
            if id_busca > 0:
                veiculo = session.query(Veiculo).filter_by(id=id_busca).first()
                if veiculo:
                    st.session_state['veiculo_selecionado'] = veiculo
                    st.success(f"✅ Veículo encontrado: ID {veiculo.id}, Placa {veiculo.placa}")
                else:
                    st.warning("⚠️ Nenhum veículo encontrado com esse ID!")
                    st.session_state.pop('veiculo_selecionado', None)
                    st.session_state.pop('confirmar_exclusao_veiculo', None)
            else:
                st.warning("⚠️ Insira um ID válido!")

        if 'veiculo_selecionado' in st.session_state:
            veiculo = st.session_state['veiculo_selecionado']
            with st.form(key="editar_veiculo"):
                codigo = st.number_input("🔢 **Código**", min_value=1, step=1, value=veiculo.codigo)
                placa = st.text_input("📜 **Placa**", value=veiculo.placa)
                modelo = st.text_input("🚘 **Modelo**", value=veiculo.modelo)
                fabricante = st.text_input("🏭 **Fabricante**", value=veiculo.fabricante)
                hodometro_atual = st.number_input("⏳ **Hodômetro Atual (km)**", min_value=0.0, step=1.0, format="%.2f", value=veiculo.hodometro_atual)
                col1, col2 = st.columns(2)
                with col1:
                    alterar_button = st.form_submit_button(label="💾 Aplicar")
                with col2:
                    excluir_button = st.form_submit_button(label="🗑️ Excluir")

                if alterar_button:
                    try:
                        veiculo.codigo = codigo
                        veiculo.placa = placa.upper()
                        veiculo.modelo = modelo
                        veiculo.fabricante = fabricante
                        veiculo.hodometro_atual = hodometro_atual
                        session.commit()
                        st.success(f"✅ Veículo ID {veiculo.id} alterado com sucesso!")
                        st.session_state.pop('veiculo_selecionado', None)
                        st.session_state.pop('confirmar_exclusao_veiculo', None)
                    except Exception as e:
                        session.rollback()
                        st.error(f"❌ Erro ao alterar veículo: {str(e)}")

                if excluir_button:
                    st.session_state['confirmar_exclusao_veiculo'] = True

        if st.session_state.get('confirmar_exclusao_veiculo', False) and 'veiculo_selecionado' in st.session_state:
            veiculo = st.session_state['veiculo_selecionado']
            if st.button(f"Confirme a exclusão do veículo ID {veiculo.id} (Placa: {veiculo.placa})"):
                try:
                    session.delete(veiculo)
                    session.commit()
                    st.success(f"✅ Veículo ID {veiculo.id} excluído com sucesso!")
                    st.session_state.pop('veiculo_selecionado', None)
                    st.session_state.pop('confirmar_exclusao_veiculo', None)
                except Exception as e:
                    session.rollback()
                    st.error(f"❌ Erro ao excluir veículo: {str(e)}")

    elif submenu == "Categorias":
        st.subheader("🔩 **Cadastro de Categorias**")

        with st.form(key="cadastro_categoria", clear_on_submit=True):
            nome = st.text_input("📋 **Nome da Categoria**")
            submit_button = st.form_submit_button(label="✅ **Cadastrar Categoria**")

            if submit_button:
                if not nome:
                    st.error("⚠️ Informe o nome da categoria!")
                else:
                    try:
                        nova_categoria = Categoria(nome=nome)
                        session.add(nova_categoria)
                        session.commit()
                        st.success(f"✅ Categoria {nome} cadastrada com sucesso!")
                    except Exception as e:
                        session.rollback()
                        st.error(f"❌ Erro ao cadastrar categoria: {str(e)}")

        st.markdown("### 🔩 **Categorias Cadastradas**")
        categorias = session.query(Categoria).all()
        if not categorias:
            st.warning("⚠️ Nenhuma categoria cadastrada!")
        else:
            dados_categorias = [{"ID": c.id, "Nome": c.nome} for c in categorias]
            df = pd.DataFrame(dados_categorias)
            st.dataframe(df, use_container_width=True)

        # Busca, Alteração e Exclusão
        st.subheader("🔍 **Gerenciar Categoria**")
        id_busca = st.number_input("🔎 **ID da Categoria para Busca/Edição/Exclusão**", min_value=0, step=1, value=0, format="%d", key="busca_categoria")
        if st.button("🔍 Buscar"):
            if id_busca > 0:
                categoria = session.query(Categoria).filter_by(id=id_busca).first()
                if categoria:
                    st.session_state['categoria_selecionada'] = categoria
                    st.success(f"✅ Categoria encontrada: ID {categoria.id}, Nome {categoria.nome}")
                else:
                    st.warning("⚠️ Nenhuma categoria encontrada com esse ID!")
                    st.session_state.pop('categoria_selecionada', None)
                    st.session_state.pop('confirmar_exclusao_categoria', None)
            else:
                st.warning("⚠️ Insira um ID válido!")

        if 'categoria_selecionada' in st.session_state:
            categoria = st.session_state['categoria_selecionada']
            with st.form(key="editar_categoria"):
                nome = st.text_input("📋 **Nome da Categoria**", value=categoria.nome)
                col1, col2 = st.columns(2)
                with col1:
                    alterar_button = st.form_submit_button(label="💾 Aplicar")
                with col2:
                    excluir_button = st.form_submit_button(label="🗑️ Excluir")

                if alterar_button:
                    try:
                        categoria.nome = nome
                        session.commit()
                        st.success(f"✅ Categoria ID {categoria.id} alterada com sucesso!")
                        st.session_state.pop('categoria_selecionada', None)
                        st.session_state.pop('confirmar_exclusao_categoria', None)
                    except Exception as e:
                        session.rollback()
                        st.error(f"❌ Erro ao alterar categoria: {str(e)}")

                if excluir_button:
                    st.session_state['confirmar_exclusao_categoria'] = True

        if st.session_state.get('confirmar_exclusao_categoria', False) and 'categoria_selecionada' in st.session_state:
            categoria = st.session_state['categoria_selecionada']
            if st.button(f"Confirme a exclusão da categoria ID {categoria.id} (Nome: {categoria.nome})"):
                try:
                    session.delete(categoria)
                    session.commit()
                    st.success(f"✅ Categoria ID {categoria.id} excluída com sucesso!")
                    st.session_state.pop('categoria_selecionada', None)
                    st.session_state.pop('confirmar_exclusao_categoria', None)
                except Exception as e:
                    session.rollback()
                    st.error(f"❌ Erro ao excluir categoria: {str(e)}")

    elif submenu == "Responsáveis":
        st.subheader("👤 **Cadastro de Responsáveis**")

        with st.form(key="cadastro_responsavel", clear_on_submit=True):
            nome = st.text_input("👤 **Nome do Responsável**")
            submit_button = st.form_submit_button(label="✅ **Cadastrar Responsável**")

            if submit_button:
                if not nome:
                    st.error("⚠️ Informe o nome do responsável!")
                else:
                    try:
                        novo_responsavel = Responsavel(nome=nome)
                        session.add(novo_responsavel)
                        session.commit()
                        st.success(f"✅ Responsável {nome} cadastrado com sucesso!")
                    except Exception as e:
                        session.rollback()
                        st.error(f"❌ Erro ao cadastrar responsável: {str(e)}")

        st.markdown("### 👤 **Responsáveis Cadastrados**")
        responsaveis = session.query(Responsavel).all()
        if not responsaveis:
            st.warning("⚠️ Nenhum responsável cadastrado!")
        else:
            dados_responsaveis = [{"ID": r.id, "Nome": r.nome} for r in responsaveis]
            df = pd.DataFrame(dados_responsaveis)
            st.dataframe(df, use_container_width=True)

        # Busca, Alteração e Exclusão
        st.subheader("🔍 **Gerenciar Responsável**")
        id_busca = st.number_input("🔎 **ID do Responsável para Busca/Edição/Exclusão**", min_value=0, step=1, value=0, format="%d", key="busca_responsavel")
        if st.button("🔍 Buscar"):
            if id_busca > 0:
                responsavel = session.query(Responsavel).filter_by(id=id_busca).first()
                if responsavel:
                    st.session_state['responsavel_selecionado'] = responsavel
                    st.success(f"✅ Responsável encontrado: ID {responsavel.id}, Nome {responsavel.nome}")
                else:
                    st.warning("⚠️ Nenhum responsável encontrado com esse ID!")
                    st.session_state.pop('responsavel_selecionado', None)
                    st.session_state.pop('confirmar_exclusao_responsavel', None)
            else:
                st.warning("⚠️ Insira um ID válido!")

        if 'responsavel_selecionado' in st.session_state:
            responsavel = st.session_state['responsavel_selecionado']
            with st.form(key="editar_responsavel"):
                nome = st.text_input("👤 **Nome do Responsável**", value=responsavel.nome)
                col1, col2 = st.columns(2)
                with col1:
                    alterar_button = st.form_submit_button(label="💾 Aplicar")
                with col2:
                    excluir_button = st.form_submit_button(label="🗑️ Excluir")

                if alterar_button:
                    try:
                        responsavel.nome = nome
                        session.commit()
                        st.success(f"✅ Responsável ID {responsavel.id} alterado com sucesso!")
                        st.session_state.pop('responsavel_selecionado', None)
                        st.session_state.pop('confirmar_exclusao_responsavel', None)
                    except Exception as e:
                        session.rollback()
                        st.error(f"❌ Erro ao alterar responsável: {str(e)}")

                if excluir_button:
                    st.session_state['confirmar_exclusao_responsavel'] = True

        if st.session_state.get('confirmar_exclusao_responsavel', False) and 'responsavel_selecionado' in st.session_state:
            responsavel = st.session_state['responsavel_selecionado']
            if st.button(f"Confirme a exclusão do responsável ID {responsavel.id} (Nome: {responsavel.nome})"):
                try:
                    session.delete(responsavel)
                    session.commit()
                    st.success(f"✅ Responsável ID {responsavel.id} excluído com sucesso!")
                    st.session_state.pop('responsavel_selecionado', None)
                    st.session_state.pop('confirmar_exclusao_responsavel', None)
                except Exception as e:
                    session.rollback()
                    st.error(f"❌ Erro ao excluir responsável: {str(e)}")

    elif submenu == "Oficinas":
        st.subheader("🏢 **Cadastro de Oficinas**")

        with st.form(key="cadastro_oficina", clear_on_submit=True):
            nome = st.text_input("🏢 **Nome da Oficina**")
            endereco = st.text_input("📍 **Endereço**")
            telefone = st.text_input("📞 **Telefone**")
            submit_button = st.form_submit_button(label="✅ **Cadastrar Oficina**")

            if submit_button:
                if not nome:
                    st.error("⚠️ Informe o nome da oficina!")
                else:
                    try:
                        nova_oficina = Oficina(nome=nome, endereco=endereco, telefone=telefone)
                        session.add(nova_oficina)
                        session.commit()
                        st.success(f"✅ Oficina {nome} cadastrada com sucesso!")
                    except Exception as e:
                        session.rollback()
                        st.error(f"❌ Erro ao cadastrar oficina: {str(e)}")

        st.markdown("### 🏢 **Oficinas Cadastradas**")
        oficinas = session.query(Oficina).all()
        if not oficinas:
            st.warning("⚠️ Nenhuma oficina cadastrada!")
        else:
            dados_oficinas = [{"ID": o.id, "Nome": o.nome, "Endereço": o.endereco, "Telefone": o.telefone} for o in oficinas]
            df = pd.DataFrame(dados_oficinas)
            st.dataframe(df, use_container_width=True)

        # Busca, Alteração e Exclusão
        st.subheader("🔍 **Gerenciar Oficina**")
        id_busca = st.number_input("🔎 **ID da Oficina para Busca/Edição/Exclusão**", min_value=0, step=1, value=0, format="%d", key="busca_oficina")
        if st.button("🔍 Buscar"):
            if id_busca > 0:
                oficina = session.query(Oficina).filter_by(id=id_busca).first()
                if oficina:
                    st.session_state['oficina_selecionada'] = oficina
                    st.success(f"✅ Oficina encontrada: ID {oficina.id}, Nome {oficina.nome}")
                else:
                    st.warning("⚠️ Nenhuma oficina encontrada com esse ID!")
                    st.session_state.pop('oficina_selecionada', None)
                    st.session_state.pop('confirmar_exclusao_oficina', None)
            else:
                st.warning("⚠️ Insira um ID válido!")

        if 'oficina_selecionada' in st.session_state:
            oficina = st.session_state['oficina_selecionada']
            with st.form(key="editar_oficina"):
                nome = st.text_input("🏢 **Nome da Oficina**", value=oficina.nome)
                endereco = st.text_input("📍 **Endereço**", value=oficina.endereco)
                telefone = st.text_input("📞 **Telefone**", value=oficina.telefone)
                col1, col2 = st.columns(2)
                with col1:
                    alterar_button = st.form_submit_button(label="💾 Aplicar")
                with col2:
                    excluir_button = st.form_submit_button(label="🗑️ Excluir")

                if alterar_button:
                    try:
                        oficina.nome = nome
                        oficina.endereco = endereco
                        oficina.telefone = telefone
                        session.commit()
                        st.success(f"✅ Oficina ID {oficina.id} alterada com sucesso!")
                        st.session_state.pop('oficina_selecionada', None)
                        st.session_state.pop('confirmar_exclusao_oficina', None)
                    except Exception as e:
                        session.rollback()
                        st.error(f"❌ Erro ao alterar oficina: {str(e)}")

                if excluir_button:
                    st.session_state['confirmar_exclusao_oficina'] = True

        if st.session_state.get('confirmar_exclusao_oficina', False) and 'oficina_selecionada' in st.session_state:
            oficina = st.session_state['oficina_selecionada']
            if st.button(f"Confirme a exclusão da oficina ID {oficina.id} (Nome: {oficina.nome})"):
                try:
                    session.delete(oficina)
                    session.commit()
                    st.success(f"✅ Oficina ID {oficina.id} excluída com sucesso!")
                    st.session_state.pop('oficina_selecionada', None)
                    st.session_state.pop('confirmar_exclusao_oficina', None)
                except Exception as e:
                    session.rollback()
                    st.error(f"❌ Erro ao excluir oficina: {str(e)}")

    if st.button("🏠 Home"):
        st.session_state['menu_principal'] = "Dashboard"
        st.rerun()

if __name__ == "__main__":
    exibir_cadastros()