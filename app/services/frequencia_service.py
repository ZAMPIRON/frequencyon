from app.bd.database import db, Aluno, Turma, Frequencia
from sqlalchemy import func
from app import recalcular_frequencia_turma  # Importe sua função de recálculo
def recalcular_frequencia_aluno(aluno_id):
    """Calcula a % de presença individual do aluno e atualiza o banco"""
    aluno = Aluno.query.get(aluno_id)
    if not aluno:
        return

    total_aulas = Frequencia.query.filter_by(aluno_id=aluno_id).count()
    if total_aulas == 0:
        aluno.frequencia = 100.0
    else:
        # Atraso e Presença contam como presença
        aulas_presente = Frequencia.query.filter(
            Frequencia.aluno_id == aluno_id,
            Frequencia.status.in_(['presente', 'atraso'])
        ).count()
        
        aluno.frequencia = round((aulas_presente / total_aulas) * 100, 1)

    db.session.commit()

    # Recalcula a média da turma do aluno para atualizar o Dashboard do Admin
    if aluno.turma_id:
        recalcular_frequencia_turma(aluno.turma_id)