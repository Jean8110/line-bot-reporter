from flask import Flask, request
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
            
            # 取得當前日期
            current_date = datetime.now().strftime("%m/%d")
            current_time = datetime.now().strftime("%H:%M")
            
            # 建立訊息
            message = TextMessage(text=f"早安{current_date}大阪新今宮營運報表如下")
            
            # 發送訊息
            response = line_bot_api.push_message(
                PushMessageRequest(
                    to=GROUP_ID,
                    messages=[message]
                )
            )
            print(f"{current_date} {current_time} 報表發送成功")
            return True
            
    except Exception as e:
        print(f"發送報表時發生錯誤: {e}")
        return False

def run_scheduler():
    """執行排程器"""
    # 設定每天早上10點發送
    schedule.every().day.at("10:00").do(send_report)
    
    print("排程器已啟動，將於每天早上 10:00 發送報表")
    
    # 持續執行排程
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分鐘檢查一次

@app.route('/')
def hello():
    return 'LINE Bot is running! Scheduled to send report at 10:00 AM every day.'

@app.route('/send_report', methods=['GET'])
def trigger_report():
    """測試用的路由，立即發送報表"""
    if send_report():
        return '報表發送成功'
    return '報表發送失敗', 500

@app.route("/callback", methods=['POST', 'GET'])
def callback():
    return 'OK'

if __name__ == "__main__":
    # 在背景執行排程器
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    print("程式啟動中...")
    # 啟動 Flask 應用
    app.run(debug=True, port=5001)