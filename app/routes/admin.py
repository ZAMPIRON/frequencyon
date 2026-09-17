import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from sqlalchemy import func
from werkzeug.utils import secure_filename

# Importa a instância do banco de dados e os modelos
from app.bd.database import db, Usuario, Aluno, Professor, Turma, Frequencia

# Criação da Blueprint para o módulo Admin
admin_bp = Blueprint('admin', __name__)


def recalcular_frequencia_turma(turma_id):
    """Atualiza a frequência média da turma com base na média dos alunos"""
    if not turma_id:
        return
    media = db.session.query(func.avg(Aluno.frequencia)).filter(Aluno.turma_id == turma_id).scalar()
    turma = Turma.query.get(turma_id)
    if turma:
        turma.frequencia_media = round(media, 1) if media is not None else 100.0
        db.session.commit()


# ------------------------------------------------------------------
# DASHBOARD E RELATÓRIOS
# ------------------------------------------------------------------
@admin_bp.route('/dashboard')
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


@admin_bp.route('/risco-evasao')
def risco_evasao():
    alunos_risco = Aluno.query.filter(Aluno.frequencia < 75.0).order_by(Aluno.frequencia.asc()).all()
    return render_template('admin/risco_evasao.html', alunos=alunos_risco)


@admin_bp.route('/relatorios')
def relatorios():
    total_alunos = Aluno.query.count()
    media_geral = db.session.query(func.avg(Aluno.frequencia)).scalar() or 0.0
    alunos_criticos = Aluno.query.filter(Aluno.frequencia < 75.0).count()
    
    taxa_evasao = round((alunos_criticos / total_alunos * 100), 1) if total_alunos > 0 else 0.0

    dados_cursos = db.session.query(
        Turma.curso,
        func.avg(Aluno.frequencia)
    ).join(Aluno, Turma.id == Aluno.turma_id).group_by(Turma.curso).all()

    cursos_labels = [c[0] for c in dados_cursos] if dados_cursos else []
    cursos_valores = [round(c[1], 1) for c in dados_cursos] if dados_cursos else []

    meses_labels = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun']
    base = media_geral if media_geral > 0 else 80
    meses_valores = [
        round(base * 0.95, 1),
        round(base * 0.98, 1),
        round(base * 0.96, 1),
        round(base * 1.01 if base * 1.01 <= 100 else 100, 1),
        round(base * 0.97, 1),
        round(base, 1)
    ]

    professores_query = db.session.query(
        Professor.nome,
        Professor.departamento,
        func.coalesce(func.avg(Aluno.frequencia), 100.0).label('media_freq')
    ).outerjoin(Turma, Professor.id == Turma.professor_id)\
     .outerjoin(Aluno, Turma.id == Aluno.turma_id)\
     .group_by(Professor.id)\
     .order_by(func.coalesce(func.avg(Aluno.frequencia), 100.0).desc())\
     .limit(5).all()

    top_professores = [
        {
            'nome': p.nome,
            'departamento': p.departamento,
            'media': round(p.media_freq, 1)
        }
        for p in professores_query
    ]

    return render_template(
        'admin/relatorios.html',
        total_alunos=total_alunos,
        media_geral=round(media_geral, 1),
        alunos_criticos=alunos_criticos,
        taxa_evasao=taxa_evasao,
        cursos_labels=cursos_labels,
        cursos_valores=cursos_valores,
        meses_labels=meses_labels,
        meses_valores=meses_valores,
        top_professores=top_professores
    )


# ------------------------------------------------------------------
# GESTÃO DE ALUNOS
# ------------------------------------------------------------------

@admin_bp.route('/alunos')
def alunos():
    busca = request.args.get('busca', '')
    if busca:
        lista_alunos = Aluno.query.filter(
            (Aluno.nome.ilike(f"%{busca}%")) | (Aluno.matricula.ilike(f"%{busca}%"))
        ).all()
    else:
        lista_alunos = Aluno.query.all()
    return render_template('admin/alunos.html', alunos=lista_alunos, busca=busca)


@admin_bp.route('/alunos/novo', methods=['GET', 'POST'])
def novo_aluno():
    if request.method == 'POST':
        nome = request.form.get('nome')
        matricula = request.form.get('matricula')
        email = request.form.get('email')
        numero_chamada = request.form.get('numero_chamada')
        frequencia = float(request.form.get('frequencia', 100.0))
        turma_id = request.form.get('turma_id')

        caminho_foto = None
        file = request.files.get('foto')

        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            caminho_foto = url_for('static', filename=f'uploads/{filename}')

        if Aluno.query.filter_by(matricula=matricula).first():
            flash('Matrícula já existente no sistema.', 'danger')
            return redirect(url_for('admin.novo_aluno'))

        aluno = Aluno(
            nome=nome,
            matricula=matricula,
            email=email,
            foto=caminho_foto,
            numero_chamada=int(numero_chamada) if numero_chamada else None,
            frequencia=frequencia,
            turma_id=int(turma_id) if turma_id else None
        )
        db.session.add(aluno)
        db.session.commit()

        if aluno.turma_id:
            recalcular_frequencia_turma(aluno.turma_id)

        flash('Aluno cadastrado com sucesso!', 'success')
        return redirect(url_for('admin.alunos'))

    turmas = Turma.query.all()
    return render_template('admin/cadastro_aluno.html', turmas=turmas)


@admin_bp.route('/alunos/desvincular/<int:aluno_id>', methods=['POST'])
def desvincular_aluno(aluno_id):
    aluno = Aluno.query.get_or_404(aluno_id)
    turma_id_antiga = aluno.turma_id

    aluno.turma_id = None
    db.session.commit()

    if turma_id_antiga:
        recalcular_frequencia_turma(turma_id_antiga)

    flash('Aluno desvinculado da turma com sucesso!', 'warning')
    return redirect(request.referrer or url_for('admin.turmas'))


@admin_bp.route('/alunos/deletar/<int:id>', methods=['POST'])
def deletar_aluno(id):
    aluno = Aluno.query.get_or_404(id)
    turma_id = aluno.turma_id
    db.session.delete(aluno)
    db.session.commit()

    if turma_id:
        recalcular_frequencia_turma(turma_id)

    flash('Aluno excluído com sucesso.', 'info')
    return redirect(url_for('admin.alunos'))


# ------------------------------------------------------------------
# GESTÃO DE PROFESSORES
# ------------------------------------------------------------------

@admin_bp.route('/professores', methods=['GET', 'POST'])
def professores():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        departamento = request.form.get('departamento')

        caminho_foto = None
        file = request.files.get('foto')

        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            caminho_foto = url_for('static', filename=f'uploads/{filename}')

        novo_prof = Professor(
            nome=nome,
            email=email,
            departamento=departamento,
            foto=caminho_foto
        )
        db.session.add(novo_prof)
        db.session.commit()

        flash('Professor cadastrado com sucesso!', 'success')
        return redirect(url_for('admin.professores'))

    lista_professores = Professor.query.all()
    return render_template('admin/professores.html', professores=lista_professores)


@admin_bp.route('/professores/deletar/<int:id>', methods=['POST'])
def deletar_professor(id):
    professor = Professor.query.get_or_404(id)
    db.session.delete(professor)
    db.session.commit()
    flash('Professor excluído com sucesso.', 'info')
    return redirect(url_for('admin.professores'))


# ------------------------------------------------------------------
# GESTÃO DE TURMAS
# ------------------------------------------------------------------

@admin_bp.route('/turmas', methods=['GET', 'POST'])
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
        return redirect(url_for('admin.turmas'))

    lista_turmas = Turma.query.all()
    lista_professores = Professor.query.all()
    return render_template('admin/turmas.html', turmas=lista_turmas, professores=lista_professores)


@admin_bp.route('/turmas/<int:id>')
def detalhes_turma(id):
    turma = Turma.query.get_or_404(id)
    alunos_sem_turma = Aluno.query.filter(Aluno.turma_id == None).all()
    
    return render_template(
        'admin/detalhes_turma.html',
        turma=turma,
        alunos_sem_turma=alunos_sem_turma
    )


@admin_bp.route('/turmas/<int:turma_id>/adicionar-aluno', methods=['POST'])
def adicionar_aluno_turma(turma_id):
    turma = Turma.query.get_or_404(turma_id)
    aluno_id = request.form.get('aluno_id')
    
    if aluno_id:
        aluno = Aluno.query.get(aluno_id)
        if aluno:
            aluno.turma_id = turma.id
            db.session.commit()
            recalcular_frequencia_turma(turma.id)
            flash(f'Aluno "{aluno.nome}" adicionado à turma com sucesso!', 'success')
            
    return redirect(url_for('admin.detalhes_turma', id=turma_id))


@admin_bp.route('/turmas/<int:turma_id>/remover-aluno/<int:aluno_id>', methods=['POST'])
def remover_aluno_turma(turma_id, aluno_id):
    aluno = Aluno.query.get_or_404(aluno_id)
    if aluno.turma_id == turma_id:
        aluno.turma_id = None
        db.session.commit()
        recalcular_frequencia_turma(turma_id)
        flash(f'Aluno "{aluno.nome}" removido da turma.', 'info')
        
    return redirect(url_for('admin.detalhes_turma', id=turma_id))


@admin_bp.route('/turmas/deletar/<int:id>', methods=['POST'])
def deletar_turma(id):
    turma = Turma.query.get_or_404(id)
    db.session.delete(turma)
    db.session.commit()
    flash('Turma excluída com sucesso.', 'info')
    return redirect(url_for('admin.turmas'))