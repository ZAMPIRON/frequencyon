from flask import Blueprint, render_template, jsonify, request
from datetime import datetime

# Criamos o Blueprint 'professor'
professor_bp = Blueprint('professor', __name__, url_prefix='/professor')

TOTAL_BARRAS = 10
AULAS_COM_ATRASO_PERMITIDO = (0, 1)

# Dados mockados temporários (ou consultas no Banco de Dados)
ALUNOS = [
    {"nome": "André Luiz Melo da Silva", "matricula": "2026.123.456", "presencas": ["presente"]*10, "status_atual": "presente"},
    {"nome": "Beatriz Silva de Souza",   "matricula": "2026.234.567", "presencas": ["presente"]*10, "status_atual": "presente"},
    {"nome": "Camila Oliveira Santos",   "matricula": "2026.345.678", "presencas": ["presente"]*9 + ["falta"], "status_atual": "falta"},
    {"nome": "Diego Costa Pereira",      "matricula": "2026.456.789", "presencas": ["presente"]*10, "status_atual": "presente"},
    {"nome": "Elena Santos Lima",        "matricula": "2026.567.890", "presencas": ["presente"]*10, "status_atual": "presente"},
    {"nome": "Felipe Martins Almeida",   "matricula": "2026.678.901", "presencas": ["presente"]*9 + ["falta"], "status_atual": "falta"},
]

def iniciais(nome: str) -> str:
    partes = nome.strip().split(" ")
    primeira = partes[0][0] if partes[0] else ""
    segunda = partes[1][0] if len(partes) > 1 else ""
    return (primeira + segunda).upper()

def preparar_alunos():
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    alunos_view = []
    for indice, aluno in enumerate(ALUNOS):
        alunos_view.append({
            "indice": indice,
            "nome": aluno["nome"],
            "matricula": aluno["matricula"],
            "data": data_hoje,
            "iniciais": iniciais(aluno["nome"]),
            "status": aluno["presencas"],
        })
    return alunos_view

def calcular_estatisticas():
    total_matriculados = len(ALUNOS)
    total_presentes = sum(1 for a in ALUNOS if a["status_atual"] == "presente")
    total_faltas = sum(1 for a in ALUNOS if a["status_atual"] in ("falta", "atraso"))

    total_aulas_possiveis = total_matriculados * TOTAL_BARRAS
    total_quadrados_verdes = sum(a["presencas"].count("presente") for a in ALUNOS)
    media_frequencia = (total_quadrados_verdes / total_aulas_possiveis) * 100 if total_aulas_possiveis else 0

    return {
        "total_matriculados": total_matriculados,
        "total_presentes": total_presentes,
        "total_faltas": total_faltas,
        "media_frequencia": f"{media_frequencia:.1f}",
    }

# Rota principal do professor (Chamada)
@professor_bp.route('/chamada')
def chamada():
    alunos = preparar_alunos()
    stats = calcular_estatisticas()

    return render_template(
        "professor/frequencia.html",
        alunos=alunos,
        total_matriculados=stats["total_matriculados"],
        total_presentes=stats["total_presentes"],
        total_faltas=stats["total_faltas"],
        media_frequencia=stats["media_frequencia"],
    )

# Rota AJAX para alternar presença/falta
@professor_bp.route('/toggle/<int:aluno_indice>/<int:barra_indice>', methods=["POST"])
def toggle_presenca(aluno_indice, barra_indice):
    if aluno_indice < 0 or aluno_indice >= len(ALUNOS):
        return jsonify({"erro": "aluno inválido"}), 404
    if barra_indice < 0 or barra_indice >= TOTAL_BARRAS:
        return jsonify({"erro": "barra inválida"}), 404

    aluno = ALUNOS[aluno_indice]
    novo_estado = "falta" if aluno["presencas"][barra_indice] != "falta" else "presente"

    aluno["presencas"][barra_indice] = novo_estado
    aluno["status_atual"] = novo_estado

    stats = calcular_estatisticas()

    return jsonify({
        "estado": novo_estado,
        "total_presentes": stats["total_presentes"],
        "total_faltas": stats["total_faltas"],
        "media_frequencia": stats["media_frequencia"],
    })

# Rota AJAX para marcar atraso
@professor_bp.route('/atraso/<int:aluno_indice>/<int:barra_indice>', methods=["POST"])
def marcar_atraso(aluno_indice, barra_indice):
    if aluno_indice < 0 or aluno_indice >= len(ALUNOS):
        return jsonify({"erro": "aluno inválido"}), 404
    if barra_indice not in AULAS_COM_ATRASO_PERMITIDO:
        return jsonify({"erro": "atraso só é permitido nas duas primeiras aulas"}), 400

    aluno = ALUNOS[aluno_indice]
    novo_estado = "presente" if aluno["presencas"][barra_indice] == "atraso" else "atraso"

    aluno["presencas"][barra_indice] = novo_estado
    aluno["status_atual"] = novo_estado

    stats = calcular_estatisticas()

    return jsonify({
        "estado": novo_estado,
        "total_presentes": stats["total_presentes"],
        "total_faltas": stats["total_faltas"],
        "media_frequencia": stats["media_frequencia"],
    })