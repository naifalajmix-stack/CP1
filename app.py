from flask import Flask, render_template, request, jsonify
from google import genai
import threading
import asyncio
import discord

app = Flask(__name__)

# ==========================================
# 🛑 توكن بوتك وآيدي سيرفرك:
DISCORD_TOKEN = "MTUzNTMyNDYwOTE3MDM4MzAzMA.G_GReW.CBdQAVQ2mnXqxIq2pGzCMLhgScv9RGrUXeLf-Y"
GUILD_ID = 886379063487373352
# ==========================================

client = genai.Client(api_key="AQ.Ab8RN6IcDQMLwRFFJnSsNpPI6QrWbsVhoUPIpfy_zuhpEBxksA")

intents = discord.Intents.default()
intents.members = True
discord_client = discord.Client(intents=intents)

bot_ready = False

@discord_client.event
async def on_ready():
    global bot_ready
    bot_ready = True
    print(f"Discord Bot logged in as {discord_client.user}")

def run_discord_bot():
    try:
        discord_client.run(DISCORD_TOKEN)
    except Exception as e:
        print(f"Discord Bot Error: {e}")

threading.Thread(target=run_discord_bot, daemon=True).start()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/discord')
def discord_page():
    return render_template('discord.html')

@app.route('/get_discord_members', methods=['GET'])
def get_discord_members():
    if not bot_ready:
        return jsonify({"success": False, "message": "البوت لم يتصل بعد بالديسكورد."})
    
    guild = discord_client.get_guild(GUILD_ID)
    if not guild:
        return jsonify({"success": False, "message": "لم يتم العثور على السيرفر."})
    
    # جلب الأعضاء
    members_data = []
    for m in guild.members:
        if m.bot:
            continue
        members_data.append({
            "id": str(m.id),
            "name": m.name
        })
    
    # جلب كل رتب السيرفر وترتيبها تماماً نفس ديسكورد (من الأعلى للأقل)
    sorted_roles = sorted(guild.roles, key=lambda r: r.position, reverse=True)
    all_roles = [{"id": str(r.id), "name": r.name} for r in sorted_roles if r.name != "@everyone"]
    
    return jsonify({"success": True, "members": members_data, "roles": all_roles})

@app.route('/discord_admin_action', methods=['POST'])
def discord_admin_action():
    data = request.get_json()
    action = data.get('action')
    user_id = int(data.get('user_id'))

    guild = discord_client.get_guild(GUILD_ID)
    if not guild:
        return jsonify({"message": "السيرفر غير متصل."})

    member = guild.get_member(user_id)
    if not member:
        return jsonify({"message": "العضو غير موجود في السيرفر حالياً."})

    future = asyncio.run_coroutine_threadsafe(perform_action(member, action, data), discord_client.loop)
    try:
        result_msg = future.result(timeout=5)
    except Exception as e:
        result_msg = f"فشل التنفيذ: {str(e)}"

    return jsonify({"message": result_msg})

async def perform_action(member, action, data):
    try:
        if action == 'ban':
            await member.ban(reason="تم التنفيذ عبر لوحة التحكم")
            return f"تم تبنيد العضو {member.name} بنجاح 🔨"
        elif action == 'kick':
            await member.kick(reason="تم التنفيذ عبر لوحة التحكم")
            return f"تم طرد العضو {member.name} بنجاح 👢"
        elif action == 'disconnect':
            if member.voice:
                await member.move_to(None, reason="فصل من الروم الصوتي عبر لوحة التحكم")
                return f"تم فصل العضو {member.name} من الروم الصوتي 📴"
            else:
                return f"العضو {member.name} ليس متصلاً بأي روم صوتي حالياً."
        elif action == 'add_role':
            role_id = int(data.get('role_id'))
            role = member.guild.get_role(role_id)
            if role:
                await member.add_roles(role)
                return f"تم إعطاء الرتبة {role.name} للعضو {member.name} بنجاح ✅"
            return "لم يتم العثور على الرتبة المحددة."
        else:
            return "أمر إداري غير معروف."
    except Exception as e:
        return f"خطأ في الصلاحيات (تأكد أن رتبة البوت أعلى من العضو والرتبة): {str(e)}"

@app.route('/chat')
def chat_page():
    return render_template('chat.html')

@app.route('/generator')
def generator_page():
    return render_template('generator.html')
@app.route('/get_ai_response', methods=['POST'])
def get_ai_response():
    data = request.get_json()
    user_message = data.get('message', '')
    try:
        response = client.models.generate_content(model='gemini-3.6-flash', contents=user_message)
        ai_reply = response.text
    except Exception as e:
        ai_reply = f"Error: {str(e)}"
    return jsonify({"reply": ai_reply})

if __name__ == '__main__':
    app.run(debug=True)