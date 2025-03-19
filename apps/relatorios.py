import streamlit as st
import pandas as pd
import plotly.express as px
from database import Session, Manutencao, Veiculo, Acessorio
from datetime import datetime, date
import locale

try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')

session = Session()

def formatar_valor_monetario(valor):
    valor_formatado = f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {valor_formatado}"

def formatar_valor_ptbr(valor):
    return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def obter_dados_manutencoes(filtro_status=None, data_inicio=None, data_fim=None, veiculo_id=None, session_instance=None):
    if not session_instance:
        return pd.DataFrame()
    try:
        query = session_instance.query(Manutencao).filter(Manutencao.tem_vencimento == True)
        if veiculo_id:
            query = query.filter(Manutencao.veiculo_id == veiculo_id)
        if data_inicio:
            query = query.filter(Manutencao.data_manutencao >= data_inicio)
        if data_fim:
            query = query.filter(Manutencao.data_manutencao <= data_fim)
        manutencoes = query.all()
        
        if not manutencoes:
            return pd.DataFrame()
        dados_manutencoes = []
        for m in manutencoes:
            veiculo = session_instance.query(Veiculo).filter_by(id=m.veiculo_id).first()
            veiculo_nome = f"{veiculo.codigo} - {veiculo.placa} ({veiculo.modelo})" if veiculo else "Desconhecido"
            hodometro_atual = veiculo.hodometro_atual if veiculo and hasattr(veiculo, 'hodometro_atual') else m.hodometro_manutencao

            vencida = False
            alerta = False
            motivo = ""
            if m.tem_vencimento:
                if m.data_vencimento:
                    dias_restantes = (m.data_vencimento - date.today()).days
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
            status = "Vencida" if vencida else "Alerta" if alerta else "Saudável"
            dados_manutencoes.append({
                "ID": m.id, "Veículo": veiculo_nome, "Categoria": m.categoria, "Responsável": m.responsavel,
                "Oficina": m.oficina, "Tipo": m.tipo, "KM Aviso": m.km_aviso,
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

def obter_dados_acessorios(filtro_status=None, data_inicio=None, data_fim=None, session_instance=None):
    if not session_instance:
        return pd.DataFrame()
    try:
        query = session_instance.query(Acessorio).filter(Acessorio.tem_vencimento == True)
        if data_inicio:
            query = query.filter(Acessorio.data_instalacao >= data_inicio)
        if data_fim:
            query = query.filter(Acessorio.data_instalacao <= data_fim)
        acessorios = query.all()
        
        if not acessorios:
            return pd.DataFrame()
        dados_acessorios = []
        for a in acessorios:
            veiculo = session_instance.query(Veiculo).filter_by(id=a.veiculo_id).first()
            veiculo_nome = f"{veiculo.codigo} - {veiculo.placa} ({veiculo.modelo})" if veiculo else "Desconhecido"
            hodometro_atual = veiculo.hodometro_atual if veiculo and hasattr(veiculo, 'hodometro_atual') else a.km_instalacao

            vencido = False
            alerta = False
            motivo = ""
            if a.tem_vencimento:
                if a.data_vencimento:
                    dias_restantes = (a.data_vencimento - date.today()).days
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

def exibir_relatorios():
    st.title("📊 **Relatórios Avançados**")

    submenu = st.sidebar.radio("🔍 Escolha:", [
        "Manutenções por Veículo", "Manutenções por Status", "Acessórios Vencidos por Ano",
        "Gastos por Período", "Custo Médio por Manutenção", "KM Rodado vs. Manutenções"
    ])

    if submenu == "Manutenções por Veículo":
        st.subheader("🚗 **Manutenções por Veículo**")

        veiculos = session.query(Veiculo).all()
        veiculos_dict = {f"{v.codigo} - {v.placa} ({v.modelo})": v.id for v in veiculos}

        if not veiculos_dict:
            st.warning("⚠️ Nenhum veículo cadastrado!")
        else:
            veiculo_selecionado = st.selectbox("🚗 **Selecione o Veículo**", options=["Todos"] + list(veiculos_dict.keys()), index=0)
            data_inicio = st.date_input("📅 **Data Início**", value=None)
            data_fim = st.date_input("📅 **Data Fim**", value=None)
            ano_selecionado = st.selectbox("📅 **Filtrar por Ano**", options=["Todos"] + sorted(list(range(2020, date.today().year + 1)), reverse=True), index=0)

            if st.button("Gerar Relatório"):
                veiculo_id = veiculos_dict[veiculo_selecionado] if veiculo_selecionado != "Todos" else None
                df = obter_dados_manutencoes(data_inicio=data_inicio, data_fim=data_fim, veiculo_id=veiculo_id, session_instance=session)
                
                if ano_selecionado != "Todos":
                    df = df[pd.to_datetime(df["Data Manutenção"]).dt.year == int(ano_selecionado)]

                if not df.empty:
                    # Gráfico de Colunas: Manutenções por Veículo e Status
                    df_grouped = df.groupby(["Veículo", "Status"]).size().reset_index(name="Quantidade")
                    fig_colunas = px.bar(df_grouped, x="Veículo", y="Quantidade", color="Status", 
                                         title="📊 Quantidade de Manutenções por Veículo e Status", 
                                         barmode="group", color_discrete_sequence=['#4CAF50', '#FFC107', '#FF5722'])
                    fig_colunas.update_layout(height=400, xaxis_title="Veículo", yaxis_title="Quantidade de Manutenções")
                    st.plotly_chart(fig_colunas, use_container_width=True)

                    # Gráfico de Pizza: Distribuição por Tipo (apenas para veículo selecionado, se aplicável)
                    if veiculo_selecionado != "Todos":
                        df_tipo = df.groupby("Tipo").size().reset_index(name="Quantidade")
                        fig_pizza = px.pie(df_tipo, names="Tipo", values="Quantidade", 
                                           title=f"📊 Distribuição de Manutenções por Tipo ({veiculo_selecionado})", hole=0.3)
                        fig_pizza.update_layout(height=400)
                        st.plotly_chart(fig_pizza, use_container_width=True)

                    # Exibir dados
                    st.markdown("### 📋 **Dados Detalhados**")
                    st.dataframe(df[["Veículo", "Categoria", "Tipo", "Status", "Data Manutenção", "Valor Formatado (R$)", "Motivo"]], use_container_width=True)
                else:
                    st.warning("⚠️ Nenhuma manutenção encontrada para os filtros aplicados!")

    elif submenu == "Manutenções por Status":
        st.subheader("📋 **Manutenções por Status**")

        data_inicio = st.date_input("📅 **Data Início**", value=None)
        data_fim = st.date_input("📅 **Data Fim**", value=None)

        if st.button("Gerar Relatório"):
            df = obter_dados_manutencoes(data_inicio=data_inicio, data_fim=data_fim, session_instance=session)

            if not df.empty:
                # Gráfico de Pizza: Distribuição por Status
                df_status = df.groupby("Status").size().reset_index(name="Quantidade")
                fig_pizza = px.pie(df_status, names="Status", values="Quantidade", 
                                   title="📊 Distribuição de Manutenções por Status", hole=0.3,
                                   color_discrete_sequence=['#4CAF50', '#FFC107', '#FF5722'])
                fig_pizza.update_layout(height=400)
                st.plotly_chart(fig_pizza, use_container_width=True)

                # Gráfico de Linhas: Evolução por Status ao Longo do Tempo (por Mês)
                df['Mês'] = pd.to_datetime(df['Data Manutenção']).dt.strftime('%Y-%m')
                df_evolucao = df.groupby(["Mês", "Status"]).size().reset_index(name="Quantidade")
                fig_linhas = px.line(df_evolucao, x="Mês", y="Quantidade", color="Status", 
                                     title="📉 Evolução de Manutenções por Status ao Longo do Tempo",
                                     color_discrete_sequence=['#4CAF50', '#FFC107', '#FF5722'])
                fig_linhas.update_layout(height=400, xaxis_title="Mês", yaxis_title="Quantidade")
                st.plotly_chart(fig_linhas, use_container_width=True)

                # Exibir dados
                st.markdown("### 📋 **Dados Detalhados**")
                st.dataframe(df[["Veículo", "Categoria", "Tipo", "Status", "Data Manutenção", "Valor Formatado (R$)", "Motivo"]], use_container_width=True)
            else:
                st.warning("⚠️ Nenhuma manutenção encontrada para o período selecionado!")

    elif submenu == "Acessórios Vencidos por Ano":
        st.subheader("🛠️ **Acessórios Vencidos por Ano**")

        ano_inicio = st.selectbox("📅 **Ano Início**", options=["Todos"] + sorted(list(range(2020, date.today().year + 1))), index=0)
        ano_fim = st.selectbox("📅 **Ano Fim**", options=["Todos"] + sorted(list(range(2020, date.today().year + 1)), reverse=True), index=0)

        if st.button("Gerar Relatório"):
            data_inicio = datetime.strptime(f"{ano_inicio}-01-01", "%Y-%m-%d").date() if ano_inicio != "Todos" else None
            data_fim = datetime.strptime(f"{ano_fim}-12-31", "%Y-%m-%d").date() if ano_fim != "Todos" else None
            df = obter_dados_acessorios(filtro_status=["Vencida"], data_inicio=data_inicio, data_fim=data_fim, session_instance=session)

            if not df.empty:
                # Gráfico de Colunas: Acessórios Vencidos por Ano
                df['Ano'] = pd.to_datetime(df['Data Instalação']).dt.year
                df_ano = df.groupby("Ano").size().reset_index(name="Quantidade")
                fig_colunas = px.bar(df_ano, x="Ano", y="Quantidade", title="📊 Acessórios Vencidos por Ano",
                                     labels={"Ano": "Ano", "Quantidade": "Quantidade"}, color="Ano")
                fig_colunas.update_layout(height=400)
                st.plotly_chart(fig_colunas, use_container_width=True)

                # Gráfico de Dispersão: Acessórios Vencidos por Ano e Veículo
                fig_dispersao = px.scatter(df, x="Ano", y="Veículo", color="Nome", 
                                           title="📍 Acessórios Vencidos por Ano e Veículo", size_max=10)
                fig_dispersao.update_layout(height=400)
                st.plotly_chart(fig_dispersao, use_container_width=True)

                # Exibir dados
                st.markdown("### 📋 **Dados Detalhados**")
                st.dataframe(df[["Veículo", "Nome", "Data Instalação", "Data Vencimento", "Status", "Motivo"]], use_container_width=True)
            else:
                st.warning("⚠️ Nenhum acessório vencido encontrado!")

    elif submenu == "Gastos por Período":
        st.subheader("💰 **Gastos por Período**")

        data_inicio = st.date_input("📅 **Data Início**", value=None)
        data_fim = st.date_input("📅 **Data Fim**", value=None)
        status_filter = st.multiselect("📋 Filtrar por Status", options=["Saudável", "Alerta", "Vencida"], default=["Alerta", "Vencida"])

        if st.button("Gerar Relatório"):
            if data_inicio and data_fim:
                df = obter_dados_manutencoes(filtro_status=status_filter, data_inicio=data_inicio, data_fim=data_fim, session_instance=session)
                if not df.empty:
                    # Gráfico de Linhas: Gastos Acumulados por Período
                    df["Data"] = pd.to_datetime(df["Data Manutenção"]).dt.date
                    df_gastos = df.groupby("Data")["Valor (R$)"].sum().reset_index()
                    df_gastos["Total Formatado"] = df_gastos["Valor (R$)"].apply(formatar_valor_monetario)
                    fig_linhas = px.line(df_gastos, x="Data", y="Valor (R$)", title="📉 Gastos Acumulados por Período", 
                                         markers=True, hover_data=["Total Formatado"])
                    fig_linhas.update_layout(height=400, xaxis_title="Data", yaxis_title="Valor (R$)")
                    st.plotly_chart(fig_linhas, use_container_width=True)

                    # Gráfico de Área: Gastos por Categoria
                    df["Data"] = pd.to_datetime(df["Data Manutenção"]).dt.strftime("%Y-%m")
                    df_area = df.groupby(["Data", "Categoria"])["Valor (R$)"].sum().reset_index()
                    fig_area = px.area(df_area, x="Data", y="Valor (R$)", color="Categoria", 
                                       title="📈 Gastos por Categoria ao Longo do Tempo")
                    fig_area.update_layout(height=400, xaxis_title="Mês", yaxis_title="Valor (R$)")
                    st.plotly_chart(fig_area, use_container_width=True)

                    # Exibir dados
                    st.markdown("### 📋 **Dados Detalhados**")
                    st.dataframe(df[["Veículo", "Categoria", "Data Manutenção", "Valor Formatado (R$)", "Status"]], use_container_width=True)
                else:
                    st.warning("⚠️ Nenhum gasto registrado no período selecionado!")
            else:
                st.error("⚠️ Selecione um período válido!")

    elif submenu == "Custo Médio por Manutenção":
        st.subheader("💸 **Custo Médio por Manutenção**")

        data_inicio = st.date_input("📅 **Data Início**", value=None)
        data_fim = st.date_input("📅 **Data Fim**", value=None)
        categoria_filter = st.multiselect("🔩 Filtrar por Categoria", options=session.query(Manutencao.categoria).distinct().all(), default=None)

        if st.button("Gerar Relatório"):
            df = obter_dados_manutencoes(data_inicio=data_inicio, data_fim=data_fim, session_instance=session)
            if categoria_filter:
                df = df[df["Categoria"].isin([cat[0] for cat in categoria_filter])]

            if not df.empty:
                # Gráfico de Barras: Custo Médio por Veículo
                df_custo_medio = df.groupby("Veículo")["Valor (R$)"].mean().reset_index()
                df_custo_medio["Valor Formatado (R$)"] = df_custo_medio["Valor (R$)"].apply(formatar_valor_monetario)
                fig_barras = px.bar(df_custo_medio, x="Veículo", y="Valor (R$)", 
                                    title="📊 Custo Médio de Manutenção por Veículo", hover_data=["Valor Formatado (R$)"])
                fig_barras.update_layout(height=400, xaxis_title="Veículo", yaxis_title="Custo Médio (R$)")
                st.plotly_chart(fig_barras, use_container_width=True)

                # Gráfico de Boxplot: Distribuição de Custos por Categoria
                fig_box = px.box(df, x="Categoria", y="Valor (R$)", title="📉 Distribuição de Custos por Categoria",
                                 hover_data=["Veículo", "Data Manutenção"])
                fig_box.update_layout(height=400, xaxis_title="Categoria", yaxis_title="Valor (R$)")
                st.plotly_chart(fig_box, use_container_width=True)

                # Exibir dados
                st.markdown("### 📋 **Dados Detalhados**")
                st.dataframe(df[["Veículo", "Categoria", "Data Manutenção", "Valor Formatado (R$)", "Status"]], use_container_width=True)
            else:
                st.warning("⚠️ Nenhuma manutenção encontrada para os filtros aplicados!")

    elif submenu == "KM Rodado vs. Manutenções":
        st.subheader("📏 **KM Rodado vs. Manutenções**")

        data_inicio = st.date_input("📅 **Data Início**", value=None)
        data_fim = st.date_input("📅 **Data Fim**", value=None)

        if st.button("Gerar Relatório"):
            df = obter_dados_manutencoes(data_inicio=data_inicio, data_fim=data_fim, session_instance=session)
            if not df.empty:
                # Gráfico de Dispersão: KM Rodado vs. Número de Manutenções por Veículo
                df_veiculos = df.groupby("Veículo").agg({"ID": "count", "Hodômetro": "max"}).reset_index()
                df_veiculos = df_veiculos.rename(columns={"ID": "Número de Manutenções", "Hodômetro": "KM Rodado"})
                fig_dispersao = px.scatter(df_veiculos, x="KM Rodado", y="Número de Manutenções", color="Veículo",
                                           title="📍 KM Rodado vs. Número de Manutenções por Veículo", size_max=10)
                fig_dispersao.update_layout(height=400, xaxis_title="KM Rodado", yaxis_title="Número de Manutenções")
                st.plotly_chart(fig_dispersao, use_container_width=True)

                # Gráfico de Linhas: Média de KM por Manutenção ao Longo do Tempo
                df["Mês"] = pd.to_datetime(df["Data Manutenção"]).dt.strftime("%Y-%m")
                df_km_media = df.groupby(["Mês", "Veículo"]).agg({"Hodômetro": "max", "ID": "count"}).reset_index()
                df_km_media["KM por Manutenção"] = df_km_media["Hodômetro"] / df_km_media["ID"]
                fig_linhas = px.line(df_km_media, x="Mês", y="KM por Manutenção", color="Veículo",
                                     title="📉 Média de KM por Manutenção ao Longo do Tempo")
                fig_linhas.update_layout(height=400, xaxis_title="Mês", yaxis_title="KM por Manutenção")
                st.plotly_chart(fig_linhas, use_container_width=True)

                # Exibir dados
                st.markdown("### 📋 **Dados Detalhados**")
                st.dataframe(df[["Veículo", "Hodômetro (km)", "Data Manutenção", "Status"]], use_container_width=True)
            else:
                st.warning("⚠️ Nenhuma manutenção encontrada para os filtros aplicados!")

    if st.button("🏠 Home"):
        st.session_state['menu_principal'] = "Dashboard"
        st.rerun()

if __name__ == "__main__":
    exibir_relatorios()