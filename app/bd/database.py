from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Classe Pai / Base
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    foto = db.Column(db.String(255), nullable=True)
    tipo = db.Column(db.String(50)) # Identifica automaticamente se é 'aluno' ou 'professor'

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

class Aluno(Usuario):
    __tablename__ = 'alunos'
    
    id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), primary_key=True)
    matricula = db.Column(db.String(20), unique=True, nullable=False)
    numero_chamada = db.Column(db.Integer, nullable=True) # Novo campo
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