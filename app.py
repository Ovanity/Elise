from flask import Flask, render_template, request, redirect, url_for, session, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'MaCleSuperSecrete'
# Base de données SQLite dans un fichier moods.db
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///moods.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


############################################
# 1. Modèles de base de données
############################################
class User(db.Model):
    __tablename__ = 'user'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    moods = db.relationship('Mood', backref='user', lazy=True, order_by="Mood.created_at.desc()")
    profile_pic = db.Column(db.String(200), default='picture1.png')


class Mood(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mood_text = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Clé étrangère liant l'humeur à l'utilisateur
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


############################################
# 2. Routes pour choisir le profile picture
############################################
@app.route('/choose_profile_pic', methods=['GET', 'POST'])
def choose_profile_pic():
    if 'username' not in session:
        return redirect(url_for('login'))

    current_user = User.query.filter_by(username=session['username']).first()
    images = ['picture1.png', 'picture2.png']

    if request.method == 'POST':
        chosen_img = request.form.get('profile_pic')
        current_user.profile_pic = chosen_img
        db.session.commit()
        # Redirect to the user's profile page after choosing the picture
        return redirect(url_for('user_profile', username=current_user.username))

    return render_template('choose_profile_pic.html', images=images)


############################################
# 3. Routes pour inscription / connexion
############################################
@app.route('/')
def index():
    users = User.query.all()
    return render_template('index.html', users=users)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Page d'inscription : crée un nouvel utilisateur dans la base.
    After successful registration, the user is logged in and redirected to choose a profile picture.
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # Vérifie si l'utilisateur existe déjà
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return "Nom d'utilisateur déjà pris."

        # Crée un nouvel utilisateur
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()

        # Auto login and redirect to choose profile picture
        session['username'] = new_user.username
        return redirect(url_for('choose_profile_pic'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Page de connexion : vérifie le couple username/password et met l'username en session.
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            session['username'] = user.username
            return redirect(url_for('index'))
        else:
            return "Identifiants invalides. <a href='/login'>Réessayer</a>"

    return render_template('login.html')


@app.route('/logout')
def logout():
    """
    Déconnexion : supprime l'utilisateur de la session
    """
    session.pop('username', None)
    return redirect(url_for('index'))


############################################
# 4. Routes pour gérer les humeurs et profil utilisateur
############################################
@app.route('/add_mood', methods=['GET', 'POST'])
def add_mood():
    """
    Permet à l'utilisateur connecté d'ajouter une humeur.
    """
    if 'username' not in session:
        return redirect(url_for('login'))

    current_user = User.query.filter_by(username=session['username']).first()

    if request.method == 'POST':
        mood_text = request.form.get('mood_text')
        new_mood = Mood(mood_text=mood_text, user_id=current_user.id)
        db.session.add(new_mood)
        db.session.commit()
        return redirect(url_for('user_profile', username=current_user.username))

    return render_template('add_mood.html')


@app.route('/profile/<username>', methods=['GET', 'POST'])
def user_profile(username):
    """
    Affiche la page de profil d'un utilisateur (user_profile.html).
    Si l'utilisateur connecté correspond au profil, il peut ajouter une nouvelle humeur.
    """
    user = User.query.filter_by(username=username).first_or_404()

    if request.method == 'POST':
        if 'username' in session and session['username'] == username:
            new_mood_text = request.form.get('mood')
            new_mood = Mood(mood_text=new_mood_text, user_id=user.id)
            db.session.add(new_mood)
            db.session.commit()
            return redirect(url_for('user_profile', username=username))
        else:
            return "Action non autorisée."

    current_mood = user.moods[0].mood_text if user.moods else "No mood set"
    return render_template('user_profile.html', username=username, mood=current_mood, user=user)


@app.route('/moods/<username>')
def user_moods(username):
    """
    Affiche la liste des humeurs pour un utilisateur donné.
    """
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user_moods.html', user=user)


############################################
# 5. Création de la base de données au démarrage
############################################
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Crée les tables avant de lancer l'application
    app.run(debug=False)
