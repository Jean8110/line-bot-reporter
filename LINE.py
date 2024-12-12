from flask import Flask, request, jsonify
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
    ImageMessage
)
import schedule
import time
import threading
from datetime import datetime
import pytz
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

app = Flask(__name__)

# LINE Bot 設定
CHANNEL_ACCESS_TOKEN = "lFD0fT5izkXIdZvVxg8hhpuehkxbar5utGwa7QyffB/IOLIZ5T1B5jwZnpF9STfHWdv7nbN7dDYklIjMdOU5G8LFXlVqjlC1HHsFemN+ydSYSRE9+lvaoAEdD2fNl76NVl6IhR5cE33AzdRVj+RWuQdB04t89/1O/w1cDnyilFU="
GROUP_ID = "C1171712999af06b315a23dd962ba9185"
FILE_ID = "183mytEyLQVeYxdxH1UgtemwaNLclscPF"

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

def get_drive_service():
    """初始化 Google Drive 服務"""
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    creds = service_account.Credentials.from_service_account_file(
        'credentials.json', scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def download_file(service, file_id):
    """從 Google Drive 下載檔案"""
    try:
        request = service.files().get_media(fileId=file_id)
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return file.getvalue()
    except Exception as e:
        print(f"下載檔案時發生錯誤: {e}")
        return None

def send_report():
    """發送營運報表到指定群組"""
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            
            # 使用日本時區
            jst = pytz.timezone('Asia/Tokyo')
            current_time = datetime.now(jst)
            current_date = current_time.strftime("%m/%d")
            
            # 發送文字訊息
            text_message = TextMessage(text=f"早安{current_date}大阪新今宮營運報表如下")
            line_bot_api.push_message(
                PushMessageRequest(
                    to=GROUP_ID,
                    messages=[text_message]
                )
            )

            # 下載並發送圖片
            try:
                service = get_drive_service()
                image_data = download_file(service, FILE_ID)
                if image_data:
                    # 處理並發送圖片的邏輯待補充
                    print("圖片下載成功")
                else:
                    print("圖片下載失敗")
            except Exception as e:
                print(f"處理圖片時發生錯誤: {e}")

            print(f"{current_date} 報表發送成功")
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
        time.sleep(60)

@app.route('/')
def hello():
    return 'LINE Bot is running! Scheduled to send report at 10:00 AM every day.'

@app.route('/health', methods=['GET'])
def health_check():
    """健康檢查端點"""
    jst = pytz.timezone('Asia/Tokyo')
    current_time = datetime.now(jst)
    return jsonify({
        'status': 'healthy',
        'current_time': current_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
        'next_report': '10:00 AM JST'
    })

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
    # 在背景執行排程器
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # 啟動 Flask 應用
    app.run(debug=True, port=5001)
