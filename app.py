import os
from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy import func
from app.bd.database import db, Aluno, Professor, Turma

base_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(base_dir, 'app', 'templates')

app = Flask(__name__, template_folder=template_dir)
app.secret_key = 'chave-secreta-frequencyon'

# 1. Garante que a pasta 'data' existe
pasta_bd = os.path.join(base_dir, 'data')
os.makedirs(pasta_bd, exist_ok=True)

# 2. Configura caminho do SQLite
caminho_banco = os.path.join(pasta_bd, 'database.db').replace('\\', '/')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{caminho_banco}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def recalcular_frequencia_turma(turma_id):
    """Atualiza a frequência média da turma com base na média dos alunos"""
    if not turma_id:
        return
    media = db.session.query(func.avg(Aluno.frequencia)).filter(Aluno.turma_id == turma_id).scalar()
    turma = Turma.query.get(turma_id)
    if turma:
        turma.frequencia_media = round(media, 1) if media is not None else 100.0
        db.session.commit()

# --- DASHBOARD ---
@app.route('/')
@app.route('/dashboard')
def dashboard():
    total_alunos = Aluno.query.count()
    total_professores = Professor.query.count()
    total_turmas = Turma.query.count()

    media_frequencia = db.session.query(func.avg(Aluno.frequencia)).scalar() or 0.0
    turmas_criticas = Turma.query.order_by(Turma.frequencia_media.asc()).limit(5).all()

    frequencia_por_curso = db.session.query(
        Turma.curso,
        func.avg(Aluno.frequencia).label('media')
    ).join(Aluno, Turma.id == Aluno.turma_id).group_by(Turma.curso).all()

    alunos_em_risco = Aluno.query.filter(Aluno.frequencia < 75.0).count()

    return render_template(
        'admin/dashboard.html',
        total_alunos=total_alunos,
        total_professores=total_professores,
        total_turmas=total_turmas,
        frequencia_geral=round(media_frequencia, 1),
        turmas_criticas=turmas_criticas,
        frequencia_por_curso=frequencia_por_curso,
        alunos_em_risco=alunos_em_risco
    )

# --- ALUNOS ---
@app.route('/alunos')
def alunos():
    busca = request.args.get('busca', '')
    if busca:
        lista_alunos = Aluno.query.filter(
            (Aluno.nome.ilike(f"%{busca}%")) | (Aluno.matricula.ilike(f"%{busca}%"))
        ).all()
    else:
        lista_alunos = Aluno.query.all()
    return render_template('admin/alunos.html', alunos=lista_alunos, busca=busca)

@app.route('/alunos/novo', methods=['GET', 'POST'])
def novo_aluno():
    if request.method == 'POST':
        nome = request.form.get('nome')
        matricula = request.form.get('matricula')
        email = request.form.get('email')
        frequencia = float(request.form.get('frequencia', 100.0))
        turma_id = request.form.get('turma_id')

        # Validação de matrícula repetida
        if Aluno.query.filter_by(matricula=matricula).first():
            flash('Matrícula já existente no sistema.', 'danger')
            return redirect(url_for('novo_aluno'))

        aluno = Aluno(
            nome=nome,
            matricula=matricula,
            email=email,
            frequencia=frequencia,
            turma_id=int(turma_id) if turma_id else None
        )
        db.session.add(aluno)
        db.session.commit()

        if aluno.turma_id:
            recalcular_frequencia_turma(aluno.turma_id)

        flash('Aluno cadastrado com sucesso!', 'success')
        return redirect(url_for('alunos'))

    turmas = Turma.query.all()
    return render_template('admin/cadastro_aluno.html', turmas=turmas)

@app.route('/alunos/deletar/<int:id>', methods=['POST'])
def deletar_aluno(id):
    aluno = Aluno.query.get_or_404(id)
    turma_id = aluno.turma_id
    db.session.delete(aluno)
    db.session.commit()

    if turma_id:
        recalcular_frequencia_turma(turma_id)

    flash('Aluno excluído com sucesso.', 'info')
    return redirect(url_for('alunos'))

# --- PROFESSORES ---
@app.route('/professores', methods=['GET', 'POST'])
def professores():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        departamento = request.form.get('departamento')

        novo_prof = Professor(nome=nome, email=email, departamento=departamento)
        db.session.add(novo_prof)
        db.session.commit()

        flash('Professor cadastrado com sucesso!', 'success')
        return redirect(url_for('professores'))

    lista_professores = Professor.query.all()
    return render_template('admin/professores.html', professores=lista_professores)

# --- TURMAS ---
@app.route('/turmas', methods=['GET', 'POST'])
def turmas():
    if request.method == 'POST':
        nome = request.form.get('nome')
        curso = request.form.get('curso')
        professor_id = request.form.get('professor_id')

        nova_turma = Turma(
            nome=nome,
            curso=curso,
            professor_id=int(professor_id) if professor_id else None
        )
        db.session.add(nova_turma)
        db.session.commit()

        flash('Turma cadastrada com sucesso!', 'success')
        return redirect(url_for('turmas'))

    lista_turmas = Turma.query.all()
    lista_professores = Professor.query.all()
    return render_template('admin/turmas.html', turmas=lista_turmas, professores=lista_professores)

# --- RISCO DE EVASÃO ---
@app.route('/risco-evasao')
def risco_evasao():
    alunos_risco = Aluno.query.filter(Aluno.frequencia < 75.0).order_by(Aluno.frequencia.asc()).all()
    return render_template('admin/risco_evasao.html', alunos=alunos_risco)

# --- RELATÓRIOS ---
@app.route('/relatorios')
def relatorios():
    total_alunos = Aluno.query.count()
    alunos_criticos = Aluno.query.filter(Aluno.frequencia < 75.0).count()
    media_geral = db.session.query(func.avg(Aluno.frequencia)).scalar() or 0.0
    turmas = Turma.query.all()

    return render_template(
        'admin/relatorios.html',
        total_alunos=total_alunos,
        alunos_criticos=alunos_criticos,
        media_geral=round(media_geral, 1),
        turmas=turmas
    )

# --- POVOAR BANCO DE DADOS INICIAL ---
def popular_banco_inicial():
    with app.app_context():
        db.create_all()
        if Professor.query.count() == 0:
            p1 = Professor(nome="Pedro Souza", email="pedro.souza@if.edu.br", departamento="Construção Civil")
            p2 = Professor(nome="Carlos Neto", email="carlos.neto@if.edu.br", departamento="Química")
            p3 = Professor(nome="Marcia Flores", email="marcia.flores@if.edu.br", departamento="Computação")
            
            db.session.add_all([p1, p2, p3])
            db.session.commit()

            t1 = Turma(nome="Edificações 1º Ano", curso="Edificações", professor=p1)
            t2 = Turma(nome="Química II", curso="Química", professor=p2)
            t3 = Turma(nome="Algoritmos e Estruturas", curso="Computação", professor=p3)

            db.session.add_all([t1, t2, t3])
            db.session.commit()

            alunos = [
                Aluno(nome="Lucas Silva", matricula="2023001", email="lucas@if.edu.br", frequencia=62.5, turma=t1),
                Aluno(nome="Mariana Costa", matricula="2023002", email="mariana@if.edu.br", frequencia=71.0, turma=t1),
                Aluno(nome="Gabriel Rocha", matricula="2023003", email="gabriel@if.edu.br", frequencia=88.0, turma=t2),
                Aluno(nome="Ana Lima", matricula="2023004", email="ana@if.edu.br", frequencia=95.0, turma=t3),
            ]
            
            db.session.add_all(alunos)
            db.session.commit()

            recalcular_frequencia_turma(t1.id)
            recalcular_frequencia_turma(t2.id)
            recalcular_frequencia_turma(t3.id)

if __name__ == '__main__':
    popular_banco_inicial()
    app.run(debug=True, port=5000)