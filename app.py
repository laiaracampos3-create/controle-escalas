import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

# Banco de dados SQLite local
DATABASE_URL = "sqlite:///escalas.db"
engine = create_engine(DATABASE_URL, echo=False)
Base = declarative_base()

class Colaborador(Base):
    __tablename__ = "colaboradores"
    matricula = Column(String, primary_key=True)
    nome = Column(String, nullable=False)
    funcao = Column(String)

class EscalaMensal(Base):
    __tablename__ = "escalas_mensais"
    id = Column(Integer, primary_key=True, autoincrement=True)
    mes_ano = Column(String, nullable=False) # Ex: "10/2026"
    matricula = Column(String, nullable=False)
    nome = Column(String, nullable=False)
    funcao = Column(String)
    regime = Column(String, nullable=False) # Ex: 6x1, 12x36, etc.
    horario_previsto = Column(String, nullable=False) # Ex: "06:00 às 15:48"
    refeicao = Column(String) # Ex: "1h (12:00 às 13:00)"
    regra_folgas = Column(String) # Ex: "Domingos alternados", "Escala par"
    linha_ou_rota = Column(String) # Ex: "Linha 102 - Gerdau"
    data_registro = Column(String)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

st.set_page_config(page_title="Escalas Mensais", layout="wide")

st.title("🗓️ Informação de Escala Mensal")

menu = st.sidebar.radio("Navegação", [
    "Informar Minha Escala Mensal", 
    "Consultar Escalas do Mês (DP)", 
    "Admin / Cadastro de Colaboradores"
])

# ----------------------------------------------------
# 1. ADMIN: IMPORTAR COLABORADORES
# ----------------------------------------------------
if menu == "Admin / Cadastro de Colaboradores":
    st.subheader("Importar Lista de Colaboradores")
    st.write("Envie uma planilha com as colunas: `matricula`, `nome`, `funcao` (aceita maiúsculas/minúsculas).")
    
    arquivo = st.file_uploader("Escolha a planilha (.xlsx ou .csv)", type=["xlsx", "csv"])
    if arquivo:
        if arquivo.name.endswith(".csv"):
            df = pd.read_csv(arquivo)
        else:
            df = pd.read_excel(arquivo)
            
        # Normaliza nomes de colunas
        df.columns = (
            df.columns.astype(str)
            .str.strip()
            .str.lower()
            .str.replace('ç', 'c')
            .str.replace('ã', 'a')
            .str.replace('á', 'a')
            .str.replace('é', 'e')
            .str.replace('í', 'i')
        )
        
        st.write("Prévia dos dados:")
        st.dataframe(df.head())
        
        if st.button("Salvar no Sistema"):
            session = Session()
            try:
                for _, row in df.iterrows():
                    mat = str(row['matricula'])
                    colab = session.query(Colaborador).filter_by(matricula=mat).first()
                    if not colab:
                        colab = Colaborador(matricula=mat, nome=str(row['nome']), funcao=str(row.get('funcao', '')))
                        session.add(colab)
                    else:
                        colab.nome = str(row['nome'])
                        colab.funcao = str(row.get('funcao', ''))
                session.commit()
                st.success("Colaboradores importados com sucesso!")
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
            finally:
                session.close()

# ----------------------------------------------------
# 2. COLABORADOR/LÍDER: LANÇAR ESCALA DO MÊS
# ----------------------------------------------------
elif menu == "Informar Minha Escala Mensal":
    st.subheader("Informe a Escala Prevista para o Mês")
    session = Session()
    colabs = session.query(Colaborador).order_by(Colaborador.nome).all()
    session.close()
    
    if not colabs:
        st.warning("Nenhum colaborador cadastrado. Faça o upload inicial na aba de Admin.")
    else:
        # Monta opções de meses (mês atual e próximo)
        ano_atual = datetime.now().year
        meses = [
            f"{str(m).zfill(2)}/{ano_atual}" for m in range(1, 13)
        ]
        mes_default_idx = datetime.now().month - 1
        
        opcoes_colab = {f"{c.matricula} - {c.nome} ({c.funcao})": c for c in colabs}
        
        with st.form("form_escala_mensal"):
            col_m, col_c = st.columns([1, 2])
            with col_m:
                mes_ref = st.selectbox("Mês de Referência:", meses, index=mes_default_idx)
            with col_c:
                colab_escolhido = st.selectbox("Colaborador:", list(opcoes_colab.keys()))
            
            colab_obj = opcoes_colab[colab_escolhido]
            
            st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                regime = st.selectbox("Tipo de Escala / Regime:", [
                    "6x1 (Folga semanal)",
                    "5x2 (Segunda a Sexta)",
                    "5x1 (Turno de revezamento)",
                    "12x36 Diurno (07h às 19h)",
                    "12x36 Noturno (19h às 07h)",
                    "Plantão / Reserva Técnica / Folguista",
                    "Outro Regime Específico"
                ])
                horario = st.text_input("Horário Contratual Habitual:", placeholder="Ex: 06:00 às 15:48 ou 07:00 às 17:00")
            
            with col2:
                refeicao = st.text_input("Intervalo de Refeição / Descanso:", placeholder="Ex: 1 hora (11:30 às 12:30)")
                regra_folgas = st.text_input("Critério de Folgas no Mês:", placeholder="Ex: Todo domingo e 1 sábado por mês / Dias pares")

            linha = st.text_input("Linha / Rota / Posto de Serviço (Opcional):", placeholder="Ex: Transporte Fretado Linha 2, Tráfego Urbano, etc.")
            
            enviado = st.form_submit_button("Salvar Escala do Mês")
            if enviado:
                if not horario:
                    st.error("Por favor, preencha o horário habitual.")
                else:
                    session = Session()
                    # Verifica se já tinha cadastro desse colaborador no mês e atualiza
                    registro_existente = session.query(EscalaMensal).filter_by(
                        matricula=colab_obj.matricula, 
                        mes_ano=mes_ref
                    ).first()
                    
                    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                    
                    if registro_existente:
                        registro_existente.regime = regime
                        registro_existente.horario_previsto = horario
                        registro_existente.refeicao = refeicao
                        registro_existente.regra_folgas = regra_folgas
                        registro_existente.linha_ou_rota = linha
                        registro_existente.data_registro = agora
                    else:
                        novo = EscalaMensal(
                            mes_ano=mes_ref,
                            matricula=colab_obj.matricula,
                            nome=colab_obj.nome,
                            funcao=colab_obj.funcao,
                            regime=regime,
                            horario_previsto=horario,
                            refeicao=refeicao,
                            regra_folgas=regra_folgas,
                            linha_ou_rota=linha,
                            data_registro=agora
                        )
                        session.add(novo)
                        
                    session.commit()
                    session.close()
                    st.success(f"Escala de {colab_obj.nome} para {mes_ref} salva com sucesso!")

# ----------------------------------------------------
# 3. VISÃO DO DP / EXPORTAÇÃO
# ----------------------------------------------------
elif menu == "Consultar Escalas do Mês (DP)":
    st.subheader("Quadro de Escalas Mensais Registradas")
    session = Session()
    escalas = session.query(EscalaMensal).all()
    session.close()
    
    if escalas:
        dados = [{
            "Mês/Ano": e.mes_ano,
            "Matrícula": e.matricula,
            "Nome": e.nome,
            "Função": e.funcao,
            "Regime": e.regime,
            "Horário Previsto": e.horario_previsto,
            "Intervalo": e.refeicao,
            "Regra de Folgas": e.regra_folgas,
            "Linha/Rota": e.linha_ou_rota,
            "Última Atualização": e.data_registro
        } for e in escalas]
        
        df_escalas = pd.DataFrame(dados)
        
        # Filtro por mês
        meses_disponiveis = ["Todos"] + sorted(list(df_escalas["Mês/Ano"].unique()))
        mes_filtro = st.selectbox("Filtrar por Mês:", meses_disponiveis)
        
        if mes_filtro != "Todos":
            df_filtrado = df_escalas[df_escalas["Mês/Ano"] == mes_filtro]
        else:
            df_filtrado = df_escalas
            
        st.dataframe(df_filtrado, use_container_width=True)
        
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Baixar Relatório do DP em CSV (Excel)", 
            data=csv, 
            file_name=f"escalas_{mes_filtro.replace('/', '_')}.csv", 
            mime="text/csv"
        )
    else:
        st.info("Nenhuma escala mensal cadastrada até o momento.")
