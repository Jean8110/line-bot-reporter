from flask import Flask, request, jsonify
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    TextMessage
)
import schedule
import time
import threading
from datetime import datetime
import pytz

app = Flask(__name__)

# LINE Bot ]w
CHANNEL_ACCESS_TOKEN = "lFD0fT5izkXIdZvVxg8hhpuehkxbar5utGwa7QyffB/IOLIZ5T1B5jwZnpF9STfHWdv7nbN7dDYklIjMdOU5G8LFXlVqjlC1HHsFemN+ydSYSRE9+lvaoAEdD2fNl76NVl6IhR5cE33AzdRVj+RWuQdB04t89/1O/w1cDnyilFU="
GROUP_ID = "C1171712999af06b315a23dd962ba9185"

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

def send_report():
    """oews""
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            
            # ϥΤ饻ɰ            jst = pytz.timezone('Asia/Tokyo')
            current_time = datetime.now(jst)
            current_date = current_time.strftime("%m/%d")
            
            # إ߰T
            message = TextMessage(text=f"w{current_date}jscpU")
            
            # oeT
            response = line_bot_api.push_message(
                PushMessageRequest(
                    to=GROUP_ID,
                    messages=[message]
                )
            )
            print(f"{current_date} oe\")
            return True
            
    except Exception as e:
        print(f"oeɵoͿ: {e}")
        return False

def run_scheduler():
    """Ƶ{"""
    # ]wCѦW10oe
    schedule.every().day.at("10:00").do(send_report)
    print("Ƶ{wҰʡANѦW 10:00 oe")
    
    # {
    while True:
        schedule.run_pending()
        time.sleep(60)

@app.route('/')
def hello():
    return 'LINE Bot is running! Scheduled to send report at 10:00 AM every day.'

@app.route('/health', methods=['GET'])
def health_check():
    """dˬdI"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'next_report': '10:00 AM JST'
    })

@app.route('/send_report', methods=['GET'])
def trigger_report():
    """Ĳooe"""
    if send_report():
        return 'oe\'
    return 'oe, 500

@app.route("/callback", methods=['POST', 'GET'])
def callback():
    return 'OK'

# Bz
@app.errorhandler(404)
def not_found(e):
    return '䤣', 404

@app.errorhandler(500)
def server_error(e):
    return '', 500

if __name__ == "__main__":
    # bIƵ{
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # ҰFlask     app.run(debug=True, port=5001)
