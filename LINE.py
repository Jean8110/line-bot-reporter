from flask import Flask, request, jsonify
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    TextMessage
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
FOLDER_ID = "1yNH3mP2LAUnZn8EjjGrzzpzNavkSzMqB"

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

def get_drive_service():
    """初始化 Google Drive 服務"""
    try:
        print("開始初始化 Drive 服務")
        creds = service_account.Credentials.from_service_account_file(
            '/etc/secrets/credentials.json',
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        service = build('drive', 'v3', credentials=creds)
        print("Drive 服務初始化成功")
        return service
    except Exception as e:
        print(f"初始化 Drive 服務時發生錯誤: {str(e)}")
        return None

def find_report_file(service, folder_id):
    """找到對應的報表文件"""
    try:
        jst = pytz.timezone('Asia/Tokyo')
        yesterday = datetime.now(jst) - timedelta(days=1)
        target_month = yesterday.strftime('%Y年%m月')
        target_date = yesterday.strftime('%d')
        
        print(f"尋找月份資料夾: {target_month}")
        
        month_query = f"name = '{target_month}' and '{folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder'"
        month_results = service.files().list(q=month_query).execute()
        month_folders = month_results.get('files', [])
        
        if not month_folders:
            print(f"找不到月份資料夾: {target_month}")
            return None
            
        month_folder_id = month_folders[0]['id']
        print(f"找到月份資料夾: {month_folder_id}")
        
        file_query = f"'{month_folder_id}' in parents and name contains '{target_date}'"
        file_results = service.files().list(q=file_query).execute()
        files = file_results.get('files', [])
        
        if not files:
            print(f"找不到日期檔案: {target_date}")
            return None
            
        target_file = files[0]
        print(f"找到目標檔案: {target_file['name']}")
        return target_file['id']
        
    except Exception as e:
        print(f"搜尋檔案時發生錯誤: {str(e)}")
        return None

def send_report():
    """發送營運報表到指定群組"""
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            
            jst = pytz.timezone('Asia/Tokyo')
            current_time = datetime.now(jst)
            yesterday = current_time - timedelta(days=1)
            report_date = yesterday.strftime("%m/%d")
            
            message = TextMessage(text=f"早安，{report_date}大阪新今宮營運報表如下")
            line_bot_api.push_message(
                PushMessageRequest(
                    to=GROUP_ID,
                    messages=[message]
                )
            )
            
            try:
                print("開始搜尋報表檔案")
                service = get_drive_service()
                if service:
                    file_id = find_report_file(service, FOLDER_ID)
                    if file_id:
                        print(f"開始下載檔案 ID: {file_id}")
                        request = service.files().get_media(fileId=file_id)
                        file = io.BytesIO()
                        downloader = MediaIoBaseDownload(file, request)
                        done = False
                        while done is False:
                            status, done = downloader.next_chunk()
                            print(f"下載進度: {int(status.progress() * 100)}%")
                        print("檔案下載成功")
                    else:
                        print("找不到對應的報表檔案")
                
            except Exception as e:
                print(f"處理 Drive 檔案時發生錯誤: {str(e)}")
            
            return True
            
    except Exception as e:
        print(f"發送報表時發生錯誤: {str(e)}")
        return False

@app.route("/")
def hello():
    return "LINE Bot is running!"

@app.route("/callback", methods=['POST', 'GET'])
def callback():
    return 'OK'

@app.route("/send_report", methods=['GET'])
def trigger_report():
    if send_report():
        return "報表發送成功"
    return "報表發送失敗", 500

# 這裡不需要使用 __name__ == "__main__" 的判斷
# 因為 gunicorn 會直接呼叫 app
