import os
from flask import Flask, render_template, request, redirect, url_for, session, flash

from app.bd.database import db, Usuario, Professor
from app.routes.admin import admin_bp
from app.routes.professor import professor_bp


def create_app():
    app = Flask(__name__, template_folder='app/templates', static_folder='app/static')

    app.config['SECRET_KEY'] = 'frequencia_on_chave_secreta_123'
    base_dir = os.path.abspath(os.path.dirname(__file__))
    
    upload_folder = os.path.join(base_dir, 'app', 'static', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = upload_folder

    db_path = os.path.join(base_dir, 'database', 'frequencyon.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # Registra as Blueprints
    app.register_blueprint(admin_bp)
    app.register_blueprint(professor_bp)
    def criar_usuario_admin_padrao():
        admin_existente = Usuario.query.filter_by(tipo='admin').first()
        if not admin_existente:
            admin = Usuario(
                nome="Administrador",
                email="admin@frequencyon.com",
                matricula="ADM001",
                tipo="admin"  
            )
            admin.set_senha("admin123")  # Define a senha antes de salvar
            db.session.add(admin)
            db.session.commit()

    @app.context_processor
    def inject_usuario_logado():
        if 'usuario_id' in session:
            usuario_atual = Usuario.query.get(session['usuario_id'])
        else:
            usuario_atual = Professor.query.first() or {'nome': 'Administrador', 'foto': None}
        return dict(usuario=usuario_atual)

    @app.template_filter('inicial')
    def obter_inicial(nome):
        if not nome:
            return '?'
        return nome.strip()[0].upper()

    # Rotas de Autenticação e Landing Page
    @app.route('/')
    def index():
        if 'usuario_id' in session:
            if session.get('tipo') == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif session.get('tipo') == 'professor':
                return redirect(url_for('professor.chamada'))
        
        return render_template('index.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            login_input = request.form.get('email')
            senha_input = request.form.get('senha')

            usuario = Usuario.query.filter(
                (Usuario.email == login_input) | (Usuario.matricula == login_input)
            ).first()

            if usuario and usuario.verificar_senha(senha_input):
                session['usuario_id'] = usuario.id
                session['nome'] = usuario.nome
                session['tipo'] = usuario.tipo

                flash(f'Bem-vindo(a), {usuario.nome}!', 'success')

                if usuario.tipo == 'admin':
                    return redirect(url_for('admin.dashboard'))
                else:
                    return redirect(url_for('professor.chamada'))
            else:
                flash('E-mail/Matrícula ou senha incorretos.', 'danger')

        return render_template('login.html')
    @app.route('/login/admin', methods=['GET', 'POST'])
    def login_admin():
        if request.method == 'POST':
            login_input = request.form.get('email')
            senha_input = request.form.get('senha')

            usuario = Usuario.query.filter(
                (Usuario.email == login_input) | (Usuario.matricula == login_input)
            ).first()

            if usuario and usuario.verificar_senha(senha_input) and usuario.tipo == 'admin':
                session['usuario_id'] = usuario.id
                session['nome'] = usuario.nome
                session['tipo'] = usuario.tipo

                flash(f'Bem-vindo(a), {usuario.nome}!', 'success')
                return redirect(url_for('admin.dashboard'))
            else:
                flash('E-mail/Matrícula ou senha incorretos, ou você não tem permissão de administrador.', 'danger')

        return render_template('admin/login_admin.html')
    @app.route('/logout')
    def logout():
        session.clear()
        flash('Você saiu do sistema.', 'info')
        return redirect(url_for('index'))

    with app.app_context():
        db.create_all()
        criar_usuario_admin_padrao()

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)