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
        # 取得昨天的日期
        jst = pytz.timezone('Asia/Tokyo')
        yesterday = datetime.now(jst) - timedelta(days=1)
        target_month = yesterday.strftime('%Y年%m月')    # 資料夾格式：2024年12月
        target_filename = yesterday.strftime('%m%d')     # 檔案格式：1213
        
        print(f"尋找月份資料夾: {target_month}")
        print(f"尋找檔案名稱: {target_filename}")
        
        # 找月份資料夾
        month_query = f"name = '{target_month}' and '{folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder'"
        month_results = service.files().list(q=month_query).execute()
        month_folders = month_results.get('files', [])
        
        if not month_folders:
            print(f"找不到月份資料夾: {target_month}")
            return None
            
        month_folder_id = month_folders[0]['id']
        print(f"找到月份資料夾 ID: {month_folder_id}")
        
        # 在月份資料夾中找目標檔案
        file_query = f"'{month_folder_id}' in parents and name contains '{target_filename}'"
        file_results = service.files().list(q=file_query).execute()
        files = file_results.get('files', [])
        
        if not files:
            print(f"找不到日期檔案: {target_filename}")
            return None
            
        target_file = files[0]
        print(f"找到目標檔案: {target_file['name']}")
        return target_file
        
    except Exception as e:
        print(f"搜尋檔案時發生錯誤: {str(e)}")
        return None

def send_report():
    """發送營運報表到指定群組"""
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            
            # 取得日期
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
            
            # 處理 Google Drive 檔案
            try:
                print("開始處理 Google Drive 檔案")
                service = get_drive_service()
                if service:
                    file_info = find_report_file(service, FOLDER_ID)
                    if file_info:
                        file_id = file_info['id']
                        print(f"開始下載檔案: {file_info['name']}")
                        
                        # 獲取檔案的 webContentLink
                        file = service.files().get(fileId=file_id, fields='webContentLink').execute()
                        webContentLink = file.get('webContentLink')
                        
                        if webContentLink:
                            print("發送圖片訊息")
                            image_message = ImageMessage(
                                originalContentUrl=webContentLink,
                                previewImageUrl=webContentLink
                            )
                            line_bot_api.push_message(
                                PushMessageRequest(
                                    to=GROUP_ID,
                                    messages=[image_message]
                                )
                            )
                            print("圖片發送成功")
                        else:
                            print("無法獲取檔案的公開連結")
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
