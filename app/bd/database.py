from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Professor(db.Model):
    __tablename__ = 'professores'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    departamento = db.Column(db.String(100), nullable=False)
    
    # Relacionamento com Turma
    turmas = db.relationship('Turma', backref='professor', lazy=True)

class Turma(db.Model):
    __tablename__ = 'turmas'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    curso = db.Column(db.String(100), nullable=False)
    frequencia_media = db.Column(db.Float, default=100.0)
    
    professor_id = db.Column(db.Integer, db.ForeignKey('professores.id'), nullable=True)
    alunos = db.relationship('Aluno', backref='turma', lazy=True)

class Aluno(db.Model):
    __tablename__ = 'alunos'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    matricula = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=True)
    frequencia = db.Column(db.Float, default=100.0)
    
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=True)