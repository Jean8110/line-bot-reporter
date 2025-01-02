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
import traceback
import sys
import requests

app = Flask(__name__)

# 設定
CHANNEL_ACCESS_TOKEN = "lFD0fT5izkXIdZvVxg8hhpuehkxbar5utGwa7QyffB/IOLIZ5T1B5jwZnpF9STfHWdv7nbN7dDYklIjMdOU5G8LFXlVqjlC1HHsFemN+ydSYSRE9+lvaoAEdD2fNl76NVl6IhR5cE33AzdRVj+RWuQdB04t89/1O/w1cDnyilFU="
GROUP_IDS = [
    "C1171712999af06b315a23dd962ba9185", # 測試群組
]
FOLDER_ID = "1yNH3mP2LAUnZn8EjjGrzzpzNavkSzMqB"

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

def log_info(message):
    """統一的日誌輸出格式"""
    current_time = datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S JST')
    print(f"[{current_time}] {message}")
    sys.stdout.flush()  # 確保日誌立即輸出

def get_drive_service():
    """初始化 Google Drive 服務"""
    try:
        log_info("開始初始化 Drive 服務")
        SCOPES = [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = service_account.Credentials.from_service_account_file(
            '/etc/secrets/credentials.json',
            scopes=SCOPES
        )
        service = build('drive', 'v3', credentials=creds)
        log_info("Drive 服務初始化成功")
        return service
    except Exception as e:
        log_info(f"初始化 Drive 服務時發生錯誤: {str(e)}")
        log_info(f"錯誤詳情:\n{traceback.format_exc()}")
        return None

def setup_file_sharing(service, file_id):
    """設置檔案分享權限"""
    try:
        # 先檢查是否已經有公開權限
        permissions = service.permissions().list(fileId=file_id).execute()
        for permission in permissions.get('permissions', []):
            if permission.get('type') == 'anyone':
                log_info("檔案已經有公開權限")
                return True
        
        # 如果沒有公開權限，新增權限
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        service.permissions().create(
            fileId=file_id,
            body=permission
        ).execute()
        log_info("成功設置檔案公開權限")
        return True
    except Exception as e:
        log_info(f"設置檔案權限時發生錯誤: {str(e)}")
        return False

def get_shareable_link(service, file_id):
    """獲取圖片分享連結"""
    try:
        log_info(f"開始處理檔案 ID: {file_id} 的分享連結")
        
        # 確保檔案有正確的分享權限
        if not setup_file_sharing(service, file_id):
            log_info("無法設置檔案分享權限")
            return None
        
        # 獲取檔案資訊
        file = service.files().get(
            fileId=file_id,
            fields='webViewLink,webContentLink,mimeType,name'
        ).execute()
        
        log_info(f"檔案資訊: {file}")
        
        if 'webContentLink' in file:
            # 構建新的連結格式
            base_url = f"https://drive.google.com/uc?id={file_id}"
            
            # 根據 MIME type 加上適當的副檔名
            mime_type = file.get('mimeType', '')
            if 'png' in mime_type.lower():
                base_url += '.png'
            elif 'jpeg' in mime_type.lower() or 'jpg' in mime_type.lower():
                base_url += '.jpg'
            
            log_info(f"產生圖片連結: {base_url}")
            
            # 驗證連結是否可以訪問
            try:
                response = requests.head(base_url, allow_redirects=True, timeout=10)
                if response.status_code == 200:
                    return base_url
            except Exception as e:
                log_info(f"驗證連結時發生錯誤: {str(e)}")
        
        log_info("無法獲取有效的檔案連結")
        return None
            
    except Exception as e:
        log_info(f"處理分享連結時發生錯誤: {str(e)}")
        log_info(f"錯誤詳情:\n{traceback.format_exc()}")
        return None

def find_report_file(service, folder_id):
    """找到對應的報表文件"""
    try:
        # 取得日期資訊
        jst = pytz.timezone('Asia/Tokyo')
        current_time = datetime.now(jst)
        yesterday = current_time - timedelta(days=1)
        target_month = yesterday.strftime('%Y年%m月')
        target_filename = yesterday.strftime('%m%d')
        
        log_info(f"當前時間: {current_time}")
        log_info(f"尋找日期: {yesterday}")
        log_info(f"目標月份資料夾: {target_month}")
        log_info(f"目標檔名: {target_filename}")
        
        # 找月份資料夾
        month_query = f"name = '{target_month}' and '{folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder'"
        log_info(f"搜尋月份資料夾查詢: {month_query}")
        
        month_results = service.files().list(q=month_query).execute()
        month_folders = month_results.get('files', [])
        
        if not month_folders:
            log_info(f"錯誤: 找不到月份資料夾 {target_month}")
            return None
            
        month_folder_id = month_folders[0]['id']
        log_info(f"找到月份資料夾 ID: {month_folder_id}")
        
        # 在月份資料夾中找目標檔案
        file_query = f"'{month_folder_id}' in parents and name contains '{target_filename}'"
        log_info(f"搜尋檔案查詢: {file_query}")
        
        file_results = service.files().list(q=file_query).execute()
        files = file_results.get('files', [])
        
        if not files:
            log_info(f"錯誤: 在 {target_month} 資料夾中找不到 {target_filename} 的檔案")
            return None
            
        target_file = files[0]
        log_info(f"成功找到檔案: {target_file['name']} (ID: {target_file['id']})")
        
        return target_file
        
    except Exception as e:
        log_info(f"搜尋檔案時發生錯誤: {str(e)}")
        log_info(f"錯誤詳情:\n{traceback.format_exc()}")
        return None

def send_report():
    """發送營運報表到指定群組"""
    try:
        log_info("開始執行報表發送程序")
        
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            
            # 使用日本時區
            jst = pytz.timezone('Asia/Tokyo')
            current_time = datetime.now(jst)
            yesterday = current_time - timedelta(days=1)
            report_date = yesterday.strftime("%m/%d")
            
            log_info(f"準備發送 {report_date} 的報表")
            
            # 處理 Google Drive 檔案
            service = get_drive_service()
            if not service:
                log_info("無法初始化 Google Drive 服務")
                return False
                
            log_info("開始搜尋檔案")
            file_info = find_report_file(service, FOLDER_ID)
            if not file_info:
                log_info("找不到報表檔案")
                return False
                
            log_info("開始處理檔案分享連結")
            image_url = get_shareable_link(service, file_info['id'])
            if not image_url:
                log_info("無法獲取有效的圖片連結")
                return False
            
            # 對每個群組發送訊息
            for group_id in GROUP_IDS:
                try:
                    log_info(f"開始發送到群組: {group_id}")
                    
                    # 發送文字訊息
                    message = TextMessage(text=f"各位好，{report_date}大阪新今宮營運報表如下")
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=group_id,
                            messages=[message]
                        )
                    )
                    log_info(f"文字訊息發送成功 - 群組: {group_id}")
                    
                    # 發送圖片
                    image_message = ImageMessage(
                        originalContentUrl=image_url,
                        previewImageUrl=image_url  # LINE 會自動處理預覽圖的大小
                    )
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=group_id,
                            messages=[image_message]
                        )
                    )
                    log_info(f"圖片發送成功 - 群組: {group_id}")
                    
                except Exception as e:
                    log_info(f"發送到群組 {group_id} 時發生錯誤: {str(e)}")
                    log_info(f"錯誤詳情:\n{traceback.format_exc()}")
                    continue
            
            log_info("報表發送程序完成")
            return True
            
    except Exception as e:
        log_info(f"發送報表時發生錯誤: {str(e)}")
        log_info(f"錯誤詳情:\n{traceback.format_exc()}")
        return False

@app.route("/")
def hello():
    return "LINE Bot is running!"

@app.route("/callback", methods=['POST', 'GET'])
def callback():
    return 'OK'

@app.route("/send_report", methods=['GET'])
def trigger_report():
    log_info("收到發送報表請求")
    if send_report():
        return "報表發送成功"
    return "報表發送失敗", 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
