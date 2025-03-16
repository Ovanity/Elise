# main/routes.py

from flask import Blueprint, render_template, abort
from .user.data import users

main_bp = Blueprint('main_bp', __name__)

@main_bp.route('/')
def index():
    # Affiche la liste des utilisateurs (Martin, Élise)
    # On passe notre dictionnaire users au template
    return render_template('index.html', users=users)

@main_bp.route('/profile/<username>')
def user_profile(username):
    # On essaie de récupérer l'utilisateur dans notre dict
    user = users.get(username)
    if not user:
        abort(404, description="Utilisateur introuvable")

    # On passe l'username et l'humeur au template user_profile.html
    return render_template('user_profile.html', username=username, mood=user["mood"])