from flask import Flask, request, jsonify
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
    ImageMessage
)
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import schedule
import time
import threading
from datetime import datetime, timedelta
import pytz
import io

app = Flask(__name__)

# 設定
CHANNEL_ACCESS_TOKEN = "lFD0fT5izkXIdZvVxg8hhpuehkxbar5utGwa7QyffB/IOLIZ5T1B5jwZnpF9STfHWdv7nbN7dDYklIjMdOU5G8LFXlVqjlC1HHsFemN+ydSYSRE9+lvaoAEdD2fNl76NVl6IhR5cE33AzdRVj+RWuQdB04t89/1O/w1cDnyilFU="
GROUP_ID = "C1171712999af06b315a23dd962ba9185"
FILE_ID = "183mytEyLQVeYxdxH1UgtemwaNLclscPF"

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

def get_drive_service():
    """初始化 Google Drive 服務"""
    try:
        print("開始初始化 Drive 服務")
        creds = service_account.Credentials.from_service_account_file(
            'credentials.json',
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        service = build('drive', 'v3', credentials=creds)
        print("Drive 服務初始化成功")
        return service
    except Exception as e:
        print(f"初始化 Drive 服務時發生錯誤: {str(e)}")
        return None

def send_report():
    """發送營運報表到指定群組"""
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            
            # 使用日本時區，並計算前一天的日期
            jst = pytz.timezone('Asia/Tokyo')
            current_time = datetime.now(jst)
            yesterday = current_time - timedelta(days=1)
            report_date = yesterday.strftime("%m/%d")
            
            # 發送文字訊息
            message = TextMessage(text=f"早安，{report_date}大阪新今宮營運報表如下")
            line_bot_api.push_message(
                PushMessageRequest(
                    to=GROUP_ID,
                    messages=[message]
                )
            )
            
            # 嘗試下載並發送 Google Drive 文件
            try:
                print("開始下載 Google Drive 檔案")
                service = get_drive_service()
                if service:
                    request = service.files().get_media(fileId=FILE_ID)
                    file = io.BytesIO()
                    downloader = MediaIoBaseDownload(file, request)
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()
                        print(f"下載進度: {int(status.progress() * 100)}%")
                    print("檔案下載成功")
                    
                    # 發送圖片
                    # TODO: 實作圖片發送功能
                    
            except Exception as e:
                print(f"處理 Drive 檔案時發生錯誤: {str(e)}")
            
            return True
            
    except Exception as e:
        print(f"發送報表時發生錯誤: {str(e)}")
        return False

@app.route('/')
def hello():
    jst = pytz.timezone('Asia/Tokyo')
    current_time = datetime.now(jst)
    yesterday = current_time - timedelta(days=1)
    return f'LINE Bot is running! Will send {yesterday.strftime("%m/%d")} report at 10:00 AM JST.'

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
