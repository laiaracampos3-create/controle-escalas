import streamlit as st
import pandas as pd
from datetime import date
from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.orm import declarative_base, sessionmaker

# Banco SQLite local
DATABASE_URL = "sqlite:///escalas.db"
engine = create_engine(DATABASE_URL, echo=False)
Base = declarative_base()

class Colaborador(Base):
    __tablename__ = "colaboradores"
    matricula = Column(String, primary_key=True)
    nome = Column(String, nullable=False)
    funcao = Column(String)

class Escala(Base):
    __tablename__ = "escalas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    matricula = Column(String, nullable=False)
    nome = Column(String, nullable=False)
    data = Column(Date, nullable=False)
    tipo_escala = Column(String, nullable=False)
    entrada = Column(String)
    saida = Column(String)
    observacao = Column(String)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

st.set_page_config(page_title="Gestão de Escalas", layout="wide")

st.title("🚌 Controle de Escalas de Colaboradores")

menu = st.sidebar.radio("Navegação", ["Registrar Minha Escala", "Visualizar Escalas", "Admin / Upload de Colaboradores"])

# 1. ADMIN: UPLOAD DA PLANILHA
if menu == "Admin / Upload de Colaboradores":
    st.subheader("Importar Lista de Colaboradores")
    st.write("Suba uma planilha (.xlsx ou .csv) contendo as colunas: `matricula`, `nome`, `funcao`")
    
    arquivo = st.file_uploader("Escolha a planilha", type=["xlsx", "csv"])
    if arquivo:
        if arquivo.name.endswith(".csv"):
            df = pd.read_csv(arquivo)
        else:
            df = pd.read_excel(arquivo)
            
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

# 2. COLABORADOR: LANÇAR ESCALA
elif menu == "Registrar Minha Escala":
    st.subheader("Informe sua Escala")
    session = Session()
    colabs = session.query(Colaborador).order_by(Colaborador.nome).all()
    session.close()
    
    if not colabs:
        st.warning("Nenhum colaborador cadastrado ainda. O DP precisa subir a lista primeiro na aba Admin.")
    else:
        opcoes_colab = {f"{c.matricula} - {c.nome}": c for c in colabs}
        colab_escolhido = st.selectbox("Selecione seu nome:", list(opcoes_colab.keys()))
        colab_obj = opcoes_colab[colab_escolhido]
        
        with st.form("form_escala"):
            col1, col2 = st.columns(2)
            with col1:
                dt_escala = st.date_input("Data do turno", value=date.today())
                tipo = st.selectbox("Tipo de Escala", ["Turno Regular", "Escala 12x36", "Plantão/Extra", "Folga/DSR", "Viagem"])
            with col2:
                hr_entrada = st.text_input("Horário Previsto Entrada (ex: 06:00)")
                hr_saida = st.text_input("Horário Previsto Saída (ex: 15:00)")
            
            obs = st.text_input("Observações (ex: Rota/Linha, Carro nº, etc.)")
            
            enviado = st.form_submit_button("Salvar Escala")
            if enviado:
                session = Session()
                nova_escala = Escala(
                    matricula=colab_obj.matricula,
                    nome=colab_obj.nome,
                    data=dt_escala,
                    tipo_escala=tipo,
                    entrada=hr_entrada,
                    saida=hr_saida,
                    observacao=obs
                )
                session.add(nova_escala)
                session.commit()
                session.close()
                st.success("Escala registrada com sucesso!")

# 3. DP / VISUALIZAÇÃO GERAL
elif menu == "Visualizar Escalas":
    st.subheader("Consultar Escalas Cadastradas")
    session = Session()
    escalas = session.query(Escala).all()
    session.close()
    
    if escalas:
        dados = [{
            "Matrícula": e.matricula,
            "Nome": e.nome,
            "Data": e.data,
            "Tipo": e.tipo_escala,
            "Entrada": e.entrada,
            "Saída": e.saida,
            "Obs": e.observacao
        } for e in escalas]
        
        df_escalas = pd.DataFrame(dados)
        st.dataframe(df_escalas, use_container_width=True)
        
        csv = df_escalas.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Relatório (CSV)", data=csv, file_name="escalas_consolidadas.csv", mime="text/csv")
    else:
        st.info("Nenhuma escala lançada até o momento.")
