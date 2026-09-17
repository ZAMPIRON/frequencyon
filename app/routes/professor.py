from flask import Blueprint, render_template, jsonify, request
from datetime import date, datetime
from app.bd.database import db, Aluno, Turma, Frequencia
from app.routes.admin import recalcular_frequencia_turma  # Importe sua função de recálculo

professor_bp = Blueprint('professor', __name__, url_prefix='/professor')

TOTAL_BARRAS = 10
AULAS_COM_ATRASO_PERMITIDO = (0, 1)

def obter_iniciais(nome: str) -> str:
    partes = nome.strip().split(" ") if nome else []
    if not partes:
        return "?"
    primeira = partes[0][0] if partes[0] else ""
    segunda = partes[1][0] if len(partes) > 1 else ""
    return (primeira + segunda).upper()

@professor_bp.route('/chamada')
def chamada():
    turma_id = request.args.get('turma_id', type=int)
    turmas = Turma.query.all()
    
    # Se nenhuma turma for selecionada, seleciona a primeira do banco
    if not turma_id and turmas:
        turma_id = turmas[0].id

    turma_selecionada = Turma.query.get(turma_id) if turma_id else None
    alunos_db = Aluno.query.filter_by(turma_id=turma_id).all() if turma_id else []

    hoje = date.today()
    data_formatada = hoje.strftime("%d/%m/%Y")
    
    alunos_view = []
    total_presentes_hoje = 0
    total_faltas_hoje = 0

    for aluno in alunos_db:
        # Busca registros de frequência de hoje para este aluno
        frequencias_hoje = {
            f.num_aula: f.status 
            for f in Frequencia.query.filter_by(aluno_id=aluno.id, data=hoje).all()
        }

        status_barras = []
        for i in range(TOTAL_BARRAS):
            # Se ainda não houver registro no banco para hoje, o padrão é 'presente'
            st = frequencias_hoje.get(i, 'presente')
            status_barras.append(st)

        # Contabilização simplificada de hoje
        if 'falta' in status_barras:
            total_faltas_hoje += 1
        else:
            total_presentes_hoje += 1

        alunos_view.append({
            "id": aluno.id,
            "nome": aluno.nome,
            "matricula": aluno.matricula,
            "data": data_formatada,
            "iniciais": obter_iniciais(aluno.nome),
            "status": status_barras
        })

    # Estatísticas gerais da turma vindas do Banco de Dados
    media_frequencia = turma_selecionada.frequencia_media if turma_selecionada else 100.0

    return render_template(
        "professor/frequencia.html",
        turmas=turmas,
        turma_selecionada=turma_selecionada,
        alunos=alunos_view,
        total_matriculados=len(alunos_db),
        total_presentes=total_presentes_hoje,
        total_faltas=total_faltas_hoje,
        media_frequencia=media_frequencia
    )


@professor_bp.route('/toggle/<int:aluno_id>/<int:barra_indice>', methods=["POST"])
def toggle_presenca(aluno_id, barra_indice):
    aluno = Aluno.query.get_or_404(aluno_id)
    hoje = date.today()

    freq = Frequencia.query.filter_by(aluno_id=aluno.id, data=hoje, num_aula=barra_indice).first()
    
    if not freq:
        freq = Frequencia(aluno_id=aluno.id, data=hoje, num_aula=barra_indice, status='falta')
        db.session.add(freq)
    else:
        freq.status = 'falta' if freq.status != 'falta' else 'presente'

    db.session.commit()
    recalcular_frequencia_aluno(aluno.id)

    turma = Turma.query.get(aluno.turma_id)
    return jsonify({
        "estado": freq.status,
        "media_frequencia": turma.frequencia_media if turma else 100.0
    })


@professor_bp.route('/atraso/<int:aluno_id>/<int:barra_indice>', methods=["POST"])
def marcar_atraso(aluno_id, barra_indice):
    if barra_indice not in AULAS_COM_ATRASO_PERMITIDO:
        return jsonify({"erro": "Atraso permitido apenas nas 2 primeiras aulas"}), 400

    aluno = Aluno.query.get_or_404(aluno_id)
    hoje = date.today()

    freq = Frequencia.query.filter_by(aluno_id=aluno.id, data=hoje, num_aula=barra_indice).first()

    if not freq:
        freq = Frequencia(aluno_id=aluno.id, data=hoje, num_aula=barra_indice, status='atraso')
        db.session.add(freq)
    else:
        freq.status = 'presente' if freq.status == 'atraso' else 'atraso'

    db.session.commit()
    recalcular_frequencia_aluno(aluno.id)

    turma = Turma.query.get(aluno.turma_id)
    return jsonify({
        "estado": freq.status,
        "media_frequencia": turma.frequencia_media if turma else 100.0
    })