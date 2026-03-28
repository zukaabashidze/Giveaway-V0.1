import random
import datetime
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Render-ისთვის ბაზის მისამართის დაზუსტება
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'giveaway.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

ADMIN_PASSWORD = "TSLadmin"

class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    discord_tag = db.Column(db.String(100), nullable=False)
    steam_name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(50), nullable=False)
    browser_fingerprint = db.Column(db.String(200), nullable=False, unique=True)
    date_joined = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# ბაზის შექმნა ავტომატურად
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
    data = request.json
    # ვამოწმებთ IP-ს და Fingerprint-ს
    exists = Participant.query.filter(
        (Participant.browser_fingerprint == data['fingerprint']) | 
        (Participant.ip_address == request.remote_addr)
    ).first()
    
    if exists:
        return jsonify({"status": "error", "message": "თქვენ უკვე დარეგისტრირებული ხართ!"}), 400
    
    new_user = Participant(
        full_name=data['full_name'], 
        discord_tag=data['discord_tag'], 
        steam_name=data['steam_name'], 
        ip_address=request.remote_addr, 
        browser_fingerprint=data['fingerprint']
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"status": "success", "message": "წარმატებით დარეგისტრირდით!"})

# ყურადღება: შენი ადმინ პანელი იხსნება ამ ლინკზე: /admin/TSLadmin
@app.route('/admin/<password>')
def admin_panel(password):
    if password != ADMIN_PASSWORD: 
        return "წვდომა უარყოფილია! არასწორი პაროლი.", 403
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
    if not participants: return jsonify({"status": "error", "message": "მონაწილეები არ არიან!"})
    winner = random.choice(participants)
    return jsonify({
        "full_name": winner.full_name, 
        "discord": winner.discord_tag, 
        "steam": winner.steam_name
    })

if __name__ == '__main__':
    # Render-ისთვის საჭიროა პორტის დინამიური აღება
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
