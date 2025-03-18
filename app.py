import os
from flask import Flask, render_template, request, redirect, url_for, session, abort
from flask_sqlalchemy import SQLAlchemy
from zoneinfo import ZoneInfo
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def now_gmt_plus_1():
    # "Etc/GMT-1" correspond à GMT+1
    return datetime.now(ZoneInfo("Europe/Paris"))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'MaCleSuperSecrete'
# Use your Render PostgreSQL URL or fallback to SQLite if not set
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://moods_user:iwBHTRsslOMITvDfsmVGnuOS2Tvbvk27@dpg-cvbiduij1k6c73dv1g1g-a.frankfurt-postgres.render.com/moods"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Now that 'app' and 'db' are defined, import and initialize Flask-Migrate.
from flask_migrate import Migrate
migrate = Migrate(app, db)


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
    availability = db.Column(db.String(20), default="Pas de statut")
    ideas = db.relationship('Idea', backref='author', lazy=True)
    # Stockage en GMT+1 via now_gmt_plus_1 (callable)
    last_seen = db.Column(db.DateTime, default=now_gmt_plus_1)
    visit_count = db.Column(db.Integer, default=0)


class Idea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    idea_text = db.Column(db.String(500), nullable=False)
    # Utilise now_gmt_plus_1 pour la date en GMT+1
    created_at = db.Column(db.DateTime, default=now_gmt_plus_1)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Mood(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mood_text = db.Column(db.String(200), nullable=False)
    # Utilise now_gmt_plus_1 pour la date en GMT+1
    created_at = db.Column(db.DateTime, default=now_gmt_plus_1)
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


@app.route('/add_idea', methods=['GET', 'POST'])
def add_idea():
    if 'username' not in session:
        return redirect(url_for('login'))

    current_user = User.query.filter_by(username=session['username']).first()

    if request.method == 'POST':
        idea_text = request.form.get('idea_text')
        new_idea = Idea(idea_text=idea_text, user_id=current_user.id)
        db.session.add(new_idea)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template("add_idea.html")


@app.route('/update_availability', methods=['POST'])
def update_availability():
    if 'username' not in session:
        return redirect(url_for('login'))

    new_status = request.form.get('availability')
    if new_status not in ["Disponible", "Seul(e)"]:
        return "Invalid status", 400

    current_user = User.query.filter_by(username=session['username']).first()
    current_user.availability = new_status
    db.session.commit()
    return redirect(url_for('user_profile', username=current_user.username))

@app.route('/')
def presentation():
    return render_template("presentation.html")
############################################
# 3. Routes pour inscription / connexion
############################################
import requests

import requests

import requests
import random

import requests

import requests, random, re
from datetime import datetime

import requests, random, re
from datetime import datetime

@app.route('/home')
def index():
    if 'username' in session:
        current_time = now_gmt_plus_1()  # Heure actuelle en GMT+1
        last_index_visit = session.get("last_index_visit")
        if not last_index_visit:
            session["last_index_visit"] = current_time.strftime("%Y-%m-%dT%H:%M:%S")
            current_user = User.query.filter_by(username=session['username']).first()
            if current_user:
                current_user.last_seen = current_time
                current_user.visit_count = (current_user.visit_count or 0) + 1
                db.session.commit()
        else:
            # On suppose que le timestamp stocké est déjà en GMT+1
            tz = ZoneInfo("Etc/GMT-1")
            last_visit_time = datetime.strptime(last_index_visit.rstrip("Z"), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=tz)
            if (current_time - last_visit_time).total_seconds() > 300:
                session["last_index_visit"] = current_time.strftime("%Y-%m-%dT%H:%M:%S")
                current_user = User.query.filter_by(username=session['username']).first()
                if current_user:
                    current_user.last_seen = current_time
                    current_user.visit_count = (current_user.visit_count or 0) + 1
                    db.session.commit()


    # Étape 1 : Récupérer un mot aléatoire depuis la catégorie "Catégorie:Expressions_en_français"
    try:
        category_url = (
            "https://fr.wiktionary.org/w/api.php"
            "?action=query"
            "&list=categorymembers"
            "&cmtitle=Catégorie:Expressions_en_français"
            "&cmlimit=1000"
            "&format=json"
        )
        resp_cat = requests.get(category_url)
        if resp_cat.status_code == 200:
            data_cat = resp_cat.json()
            members = data_cat.get("query", {}).get("categorymembers", [])
            if members:
                # Utiliser la date actuelle comme graine pour choisir le mot de manière déterministe
                current_day = now_gmt_plus_1().strftime("%Y%m%d")
                random.seed(current_day)
                random_word = random.choice(members).get("title", "mot inconnu")
            else:
                random_word = "mot inconnu"
        else:
            random_word = "mot inconnu"
    except Exception as e:
        random_word = "mot inconnu"

    # Étape 2 : Récupérer jusqu'à 5 phrases de définition du mot choisi
    try:
        extract_url = (
            "https://fr.wiktionary.org/w/api.php"
            "?action=query"
            "&prop=extracts"
            "&explaintext=1"
            "&exsentences=5"
            f"&titles={random_word}"
            "&format=json"
        )
        resp_extract = requests.get(extract_url)
        if resp_extract.status_code == 200:
            data_extract = resp_extract.json()
            pages = data_extract.get("query", {}).get("pages", {})
            page = next(iter(pages.values()))
            definition = page.get("extract", "Aucune définition trouvée.")
        else:
            definition = "Aucune définition trouvée."
    except Exception as e:
        definition = "Aucune définition trouvée."

    # Étape 3 : Nettoyer le texte de la définition
    definition_cleaned = re.sub(r'={2,}.*?={2,}', '', definition, flags=re.DOTALL)
    definition_cleaned = re.sub(r'--.*?--', '', definition_cleaned)
    definition_cleaned = re.sub(
        r"(Étymologie manquante ou incomplète\.?\s*Si vous la connaissez, vous pouvez l’ajouter en cliquant ici\.?)",
        "",
        definition_cleaned,
        flags=re.IGNORECASE
    )
    # Supprimer les lignes vides résiduelles
    lines = [line.strip() for line in definition_cleaned.split('\n') if line.strip()]
    definition_cleaned = '\n'.join(lines)

    # Étape 4 : Découper la définition en phrases
    sentences = definition_cleaned.split('. ')
    sentences = [s.strip().rstrip('.') for s in sentences if s.strip()]

    # Récupérer la liste des utilisateurs
    users = User.query.all()

    ideas = Idea.query.order_by(Idea.created_at.desc()).all()

    # Retourner la réponse via le template index.html
    return render_template("index.html", users=users, word=random_word, definition_sentences=sentences, ideas=ideas)

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
    if 'username' not in session:
        return redirect(url_for('login'))

    current_user = User.query.filter_by(username=session['username']).first()
    if not current_user:
        # User not found: clear session and redirect to login.
        session.pop('username', None)
        return redirect(url_for('login'))

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

    current_mood = user.moods[0].mood_text if user.moods else "Pas d'humeur pour le moment."
    return render_template('user_profile.html', username=username, mood=current_mood, user=user)


@app.route('/moods/<username>')
def user_moods(username):
    """
    Affiche la liste des humeurs pour un utilisateur donné.
    """
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user_moods.html', user=user)

@app.route('/delete_mood/<int:mood_id>', methods=['POST'])
def delete_mood(mood_id):
    # Récupérer l'humeur à supprimer
    mood = Mood.query.get_or_404(mood_id)
    # Vérifier que l'utilisateur connecté est bien l'auteur de l'humeur
    if 'username' not in session or session['username'] != mood.user.username:
        return "Action non autorisée", 403
    db.session.delete(mood)
    db.session.commit()
    return redirect(url_for('user_profile', username=mood.user.username))


@app.route('/delete_idea/<int:idea_id>', methods=['POST'])
def delete_idea(idea_id):
    # Check if the user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))

    # Retrieve the idea by its id or return 404 if not found
    idea = Idea.query.get_or_404(idea_id)

    # Verify that the current user is the author of the idea
    if session['username'] != idea.author.username:
        return "Action non autorisée", 403

    # Delete the idea and commit the change to the database
    db.session.delete(idea)
    db.session.commit()

    # Redirect to the index page (or to a page showing ideas)
    return redirect(url_for('index'))

@app.route('/clock')
def clock():
    current_time = now_gmt_plus_1().strftime('%H:%M:%S')
    return f"<html><body><h1>Time in Paris: {current_time}</h1></body></html>"

############################################
# 5. Création de la base de données au démarrage
############################################
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5002, debug=True)