from datetime import date
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Classe Pai / Base
class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    matricula = db.Column(db.String(50), unique=True, nullable=True)
    senha_hash = db.Column(db.String(255), nullable=True)
    tipo = db.Column(db.String(20), nullable=True)  # Pode ser 'admin', 'professor' ou 'aluno'
    foto = db.Column(db.String(255), nullable=True)  # Campo para armazenar o caminho da foto do usuário

    def set_senha(self, senha):
        """Criptografa e armazena a senha"""
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        """Valida a senha informada no formulário de login"""
        return check_password_hash(self.senha_hash, senha)

    __mapper_args__ = {
        'polymorphic_identity': 'usuario',
        'polymorphic_on': tipo
    }


# Classe Filha: Professor
class Professor(Usuario):
    __tablename__ = 'professores'
    
    id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), primary_key=True)
    departamento = db.Column(db.String(100), nullable=False)
    
    turmas = db.relationship('Turma', backref='professor', lazy=True)

    __mapper_args__ = {
        'polymorphic_identity': 'professor',
    }


# Classe Filha: Aluno
class Aluno(Usuario):
    __tablename__ = 'alunos'
    
    id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), primary_key=True)
    # O campo matricula foi removido daqui pois já é herdado de Usuario
    numero_chamada = db.Column(db.Integer, nullable=True)
    frequencia = db.Column(db.Float, default=100.0)
    
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=True)

    __mapper_args__ = {
        'polymorphic_identity': 'aluno',
    }


# Turma
class Turma(db.Model):
    __tablename__ = 'turmas'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    curso = db.Column(db.String(100), nullable=False)
    frequencia_media = db.Column(db.Float, default=100.0)
    
    professor_id = db.Column(db.Integer, db.ForeignKey('professores.id'), nullable=True)
    alunos = db.relationship('Aluno', backref='turma', lazy=True)


# Frequencia
class Frequencia(db.Model):
    __tablename__ = 'frequencias'

    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=False)
    data = db.Column(db.Date, default=date.today, nullable=False)
    num_aula = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='presente', nullable=False)

    __table_args__ = (
        db.UniqueConstraint('aluno_id', 'data', 'num_aula', name='_aluno_data_aula_uc'),
    )
class Admin(Usuario):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'admin',
    }