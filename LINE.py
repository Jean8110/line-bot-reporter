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

# LINE Bot 設定
CHANNEL_ACCESS_TOKEN = "lFD0fT5izkXIdZvVxg8hhpuehkxbar5utGwa7QyffB/IOLIZ5T1B5jwZnpF9STfHWdv7nbN7dDYklIjMdOU5G8LFXlVqjlC1HHsFemN+ydSYSRE9+lvaoAEdD2fNl76NVl6IhR5cE33AzdRVj+RWuQdB04t89/1O/w1cDnyilFU="
GROUP_ID = "C1171712999af06b315a23dd962ba9185"

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

def send_report():
    """發送營運報表到指定群組"""
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            
            # 使用日本時區
            jst = pytz.timezone('Asia/Tokyo')
            current_time = datetime.now(jst)
            current_date = current_time.strftime("%m/%d")
            
            # 建立訊息
            message = TextMessage(text=f"早安{current_date}大阪新今宮營運報表如下")
            
            # 發送訊息
            response = line_bot_api.push_message(
                PushMessageRequest(
                    to=GROUP_ID,
                    messages=[message]
                )
            )
            print(f"{current_date} 報表發送成功")
            return True
            
    except Exception as e:
        print(f"發送報表時發生錯誤: {e}")
        return False

@app.route('/')
def hello():
    return 'LINE Bot is running!'

@app.route('/send_report', methods=['GET'])
def trigger_report():
    """手動觸發發送報表"""
    if send_report():
        return '報表發送成功'
    return '報表發送失敗', 500

@app.route("/callback", methods=['POST', 'GET'])
def callback():
    return 'OK'

if __name__ == "__main__":
    app.run()
