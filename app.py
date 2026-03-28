import random
import datetime
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Render-ისთვის ბაზის მისამართის ოპტიმიზაცია
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'giveaway.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

ADMIN_PASSWORD = "TSLadmin"

class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # full_name-ს nullable=True ვუწერთ, რომ თუ ფორმიდან არ მოვა, არ გაჭედოს
    full_name = db.Column(db.String(100), nullable=True) 
    discord_tag = db.Column(db.String(100), nullable=False)
    steam_name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(50), nullable=False)
    browser_fingerprint = db.Column(db.String(200), nullable=False)
    date_joined = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# ბაზის შექმნა
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    try:
        count = Participant.query.count()
    except:
        count = 0
    return render_template('index.html', count=count)

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "მონაცემები არ არის გამოგზავნილი"}), 400

        # Render-ზე რეალური IP-ს ამოღება
        user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if user_ip and ',' in user_ip:
            user_ip = user_ip.split(',')[0].strip()

        fingerprint = data.get('fingerprint')

        # ვამოწმებთ უკვე არის თუ არა ბაზაში (IP-თ ან Fingerprint-ით)
        exists = Participant.query.filter(
            (Participant.browser_fingerprint == fingerprint) | 
            (Participant.ip_address == user_ip)
        ).first()
        
        if exists:
            return jsonify({"status": "error", "message": "თქვენ უკვე დარეგისტრირებული ხართ!"}), 400
        
        # ახალი მომხმარებლის შექმნა
        new_user = Participant( 
            full_name=data.get('full_name', 'No Name'),
            discord_tag=data.get('discord_tag'), 
            steam_name=data.get('steam_name'), 
            ip_address=user_ip, 
            browser_fingerprint=fingerprint
        )
        
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"status": "success", "message": "წარმატებით დარეგისტრირდით!"})

    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}") # ლოგებში რომ გამოჩნდეს რა მოხდა
        return jsonify({"status": "error", "message": "სერვერის შეცდომა რეგისტრაციისას"}), 500

@app.route('/admin/<password>')
def admin_panel(password):
    if password != ADMIN_PASSWORD: 
        return "წვდომა უარყოფილია!", 403
    participants = Participant.query.all()
    return render_template('admin.html', participants=participants, pw=password)

@app.route('/delete/<int:user_id>/<password>')
def delete_user(user_id, password):
    if password != ADMIN_PASSWORD: return "Denied", 403
    user = Participant.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('admin_panel', password=password))

@app.route('/pick_winner/<password>')
def pick_winner(password):
    if password != ADMIN_PASSWORD: return jsonify({"status": "error"}), 403
    participants = Participant.query.all()
    if not participants: 
        return jsonify({"status": "error", "message": "მონაწილეები არ არიან!"})
    
    winner = random.choice(participants)
    return jsonify({ 
        "discord": winner.discord_tag, 
        "steam": winner.steam_name,
        "full_name": winner.full_name
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
