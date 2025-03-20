import os
from flask import Flask, render_template, request, redirect, url_for, session, abort
from flask_sqlalchemy import SQLAlchemy
from zoneinfo import ZoneInfo
from datetime import datetime
from datetime import timedelta
from dotenv import load_dotenv
import json

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'MaCleSuperSecrete'
# Utilise l'URL PostgreSQL de Render ou un fallback vers SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://moods_user:iwBHTRsslOMITvDfsmVGnuOS2Tvbvk27@dpg-cvbiduij1k6c73dv1g1g-a.frankfurt-postgres.render.com/moods"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Initialisation de Flask-Migrate
from flask_migrate import Migrate
migrate = Migrate(app, db)



def nowparis_naive():
    """
    Retourne l'heure actuelle en Europe/Paris sous forme de datetime naïf
    (sans information de fuseau horaire).
    """
    return datetime.now(ZoneInfo("Europe/Paris")).replace(tzinfo=None)

@app.template_filter('paris_time')
def paris_time_filter(dt):
    if dt is None:
        return "N/A"
    # Convertit le datetime (déjà stocké en heure de Paris sans fuseau) en heure de Paris formatée
    # Ici, dt est un datetime naïf, donc on suppose qu'il est déjà en heure locale de Paris.
    return dt.strftime('%d/%m/%Y %H:%M')

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
    global_mood = db.Column(db.Integer, default=5)
    global_mood_updated_at = db.Column(db.DateTime, default=nowparis_naive)
    profile_pic = db.Column(db.String(200), default='picture1.png')
    availability = db.Column(db.String(20), default="Pas de statut")
    ideas = db.relationship('Idea', backref='author', lazy=True)
    # Stocke l'heure locale de Paris (datetime naïf)
    last_seen = db.Column(db.DateTime, default=nowparis_naive)
    visit_count = db.Column(db.Integer, default=0)
    medication_taken = db.Column(db.Boolean, default=False)
    medication_last_updated = db.Column(db.Date, default=nowparis_naive)

class DailyMood(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, default=nowparis_naive)  # Stocke uniquement la date (sans l'heure)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Idea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    idea_text = db.Column(db.String(500), nullable=False)
    # Stocke la date en heure de Paris (naïf)
    created_at = db.Column(db.DateTime, default=nowparis_naive)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Mood(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mood_text = db.Column(db.String(200), nullable=False)
    # Stocke la date en heure de Paris (naïf)
    created_at = db.Column(db.DateTime, default=nowparis_naive)
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

@app.route('/update_global_mood', methods=['POST'])
def update_global_mood():
    if 'username' not in session:
        return redirect(url_for('login'))
    try:
        new_score = int(request.form.get('global_mood'))
    except (TypeError, ValueError):
        new_score = 5  # valeur par défaut
    current_user = User.query.filter_by(username=session['username']).first()
    if current_user:
        today = nowparis_naive().date()  # Obtenir la date actuelle en heure de Paris (naïf)
        # Chercher une entrée existante pour aujourd'hui
        daily_mood = DailyMood.query.filter_by(user_id=current_user.id, date=today).first()
        if daily_mood is None:
            daily_mood = DailyMood(score=new_score, date=today, user_id=current_user.id)
            db.session.add(daily_mood)
        else:
            daily_mood.score = new_score  # Met à jour l'entrée existante si besoin
        # Met à jour également le score global stocké dans l'utilisateur (pour affichage immédiat)
        current_user.global_mood = new_score
        current_user.global_mood_updated_at = nowparis_naive()
        db.session.commit()
    return redirect(url_for('user_profile', username=current_user.username))

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


@app.route('/update_medication', methods=['POST'])
def update_medication():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    if user:
        # Obtenir la date actuelle en heure de Paris (naïve)
        today = nowparis_naive()
        # Si le statut n'a pas été mis à jour aujourd'hui, le réinitialiser à False
        if user.medication_last_updated != today:
            user.medication_taken = False

        # Mettre à jour le statut en fonction de la case cochée dans le formulaire
        # La valeur sera "on" si la case est cochée
        user.medication_taken = (request.form.get("medication") == "on")
        user.medication_last_updated = today
        db.session.commit()

    return redirect(url_for('user_profile', username=session['username']))


@app.route('/')
def presentation():
    return render_template("presentation.html")

############################################
# 3. Routes pour inscription / connexion
############################################

import requests, random, re

@app.route('/home')
def index():
    # Gestion du compteur de visites si l'utilisateur est connecté
    if 'username' in session:
        current_time = nowparis_naive()  # datetime naïf en heure de Paris
        last_index_visit = session.get("last_index_visit")
        if not last_index_visit:
            session["last_index_visit"] = current_time.strftime("%Y-%m-%dT%H:%M:%S")
            current_user = User.query.filter_by(username=session['username']).first()
            if current_user:
                current_user.last_seen = current_time
                current_user.visit_count = (current_user.visit_count or 0) + 1
                db.session.commit()
        else:
            try:
                last_visit_time = datetime.strptime(last_index_visit, "%Y-%m-%dT%H:%M:%S")
            except Exception as e:
                last_visit_time = current_time
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
                current_day = nowparis_naive().strftime("%Y%m%d")
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

    definition_cleaned = re.sub(r'={2,}.*?={2,}', '', definition, flags=re.DOTALL)
    definition_cleaned = re.sub(r'--.*?--', '', definition_cleaned)
    definition_cleaned = re.sub(
        r"(Étymologie manquante ou incomplète\.?\s*Si vous la connaissez, vous pouvez l’ajouter en cliquant ici\.?)",
        "",
        definition_cleaned,
        flags=re.IGNORECASE
    )
    lines = [line.strip() for line in definition_cleaned.split('\n') if line.strip()]
    definition_cleaned = '\n'.join(lines)
    sentences = definition_cleaned.split('. ')
    sentences = [s.strip().rstrip('.') for s in sentences if s.strip()]



    users = User.query.all()
    ideas = Idea.query.order_by(Idea.created_at.desc()).all()

    global_mood_data = []
    today = nowparis_naive().date()  # Correctly call the function here
    one_week_ago = today - timedelta(days=7)

    for user in users:
        daily_moods = DailyMood.query.filter(
            DailyMood.user_id == user.id,
            DailyMood.date >= one_week_ago
        ).order_by(DailyMood.date.asc()).all()
        profile_pic_url = url_for('static', filename='images/' + user.profile_pic)
        for dm in daily_moods:
            global_mood_data.append({
                'x': dm.date.isoformat(),
                'y': dm.score,
                'username': user.username,
                'profile_pic': profile_pic_url
            })
    global_mood_data.sort(key=lambda p: p['x'])
    print("Global Mood Data:", json.dumps(global_mood_data))

    return render_template("index.html", users=users, word=random_word, definition_sentences=sentences, ideas=ideas,
                           global_mood_data=json.dumps(global_mood_data))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return "Nom d'utilisateur déjà pris."
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        session['username'] = new_user.username
        return redirect(url_for('choose_profile_pic'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
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
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/majs')
def majs():
    return render_template('majs.html')



@app.route('/add_mood', methods=['GET', 'POST'])
def add_mood():
    if 'username' not in session:
        return redirect(url_for('login'))
    current_user = User.query.filter_by(username=session['username']).first()
    if not current_user:
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
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user_moods.html', user=user)

@app.route('/delete_mood/<int:mood_id>', methods=['POST'])
def delete_mood(mood_id):
    mood = Mood.query.get_or_404(mood_id)
    if 'username' not in session or session['username'] != mood.user.username:
        return "Action non autorisée", 403
    db.session.delete(mood)
    db.session.commit()
    return redirect(url_for('user_profile', username=mood.user.username))


@app.route('/delete_idea/<int:idea_id>', methods=['POST'])
def delete_idea(idea_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    idea = Idea.query.get_or_404(idea_id)
    if session['username'] != idea.author.username:
        return "Action non autorisée", 403
    db.session.delete(idea)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/games')
def games():
    return render_template('games.html')

############################################
# 5. Création de la base de données au démarrage
############################################
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5002, debug=True)