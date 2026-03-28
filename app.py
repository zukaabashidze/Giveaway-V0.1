import random
import datetime
import os
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# მონაცემთა ბაზის კონფიგურაცია
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'giveaway.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# პარამეტრები
ADMIN_PASSWORD = "TSLadmin"
PROXYCHECK_API_KEY = "m3j506-75k483-1c97ho-6848lz"

class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=True) 
    discord_tag = db.Column(db.String(100), nullable=False)
    steam_name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(50), nullable=False)
    browser_fingerprint = db.Column(db.String(200), nullable=False)
    date_joined = db.Column(db.DateTime, default=datetime.datetime.utcnow)

with app.app_context():
    db.create_all()

def is_vpn(ip):
    """ამოწმებს IP მისამართს VPN/Proxy-ზე proxycheck.io-ს მეშვეობით"""
    try:
        # ვიყენებთ შენს პირად API Key-ს
        url = f"https://proxycheck.io/v2/{ip}?key={PROXYCHECK_API_KEY}&vpn=1&asn=1"
        response = requests.get(url, timeout=5).json()
        
        if response.get("status") == "ok":
            # თუ პასუხში proxy არის "yes", ესე იგი VPN ან პროქსია
            if response.get(ip, {}).get("proxy") == "yes":
                return True
        return False
    except Exception as e:
        print(f"VPN Check Error: {e}")
        return False

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

        # ნამდვილი IP-ს ამოღება (Render/Heroku-სთვის)
        user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if user_ip and ',' in user_ip:
            user_ip = user_ip.split(',')[0].strip()

        # 1. VPN შემოწმება
        if is_vpn(user_ip):
            return jsonify({
                "status": "error", 
                "message": "VPN-ის გამოყენება აკრძალულია! გთხოვთ გამორთოთ და სცადოთ თავიდან."
            }), 400

        fingerprint = data.get('fingerprint')

        # 2. დუბლიკატების შემოწმება (IP ან Fingerprint)
        exists = Participant.query.filter(
            (Participant.browser_fingerprint == fingerprint) | 
            (Participant.ip_address == user_ip)
        ).first()
        
        if exists:
            return jsonify({"status": "error", "message": "თქვენ უკვე დარეგისტრირებული ხართ!"}), 400
        
        # 3. მონაცემების შენახვა
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
        print(f"Error: {e}")
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
    # Render-ზე ავტომატურად აიღებს პორტს
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
