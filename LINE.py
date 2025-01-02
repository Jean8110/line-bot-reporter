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
import requests
from urllib.parse import urlparse

app = Flask(__name__)

# 設定
CHANNEL_ACCESS_TOKEN = "lFD0fT5izkXIdZvVxg8hhpuehkxbar5utGwa7QyffB/IOLIZ5T1B5jwZnpF9STfHWdv7nbN7dDYklIjMdOU5G8LFXlVqjlC1HHsFemN+ydSYSRE9+lvaoAEdD2fNl76NVl6IhR5cE33AzdRVj+RWuQdB04t89/1O/w1cDnyilFU="
GROUP_IDS = [
    "C1171712999af06b315a23dd962ba9185", # 測試群組
]
FOLDER_ID = "1yNH3mP2LAUnZn8EjjGrzzpzNavkSzMqB"
MAX_RETRIES = 3  # 最大重試次數

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

def get_drive_service():
    """初始化 Google Drive 服務"""
    try:
        print("開始初始化 Drive 服務")
        SCOPES = ['https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/drive.file']
        creds = service_account.Credentials.from_service_account_file(
            '/etc/secrets/credentials.json',
            scopes=SCOPES
        )
        service = build('drive', 'v3', credentials=creds)
        print("Drive 服務初始化成功")
        return service
    except Exception as e:
        print(f"初始化 Drive 服務時發生錯誤: {str(e)}")
        print(f"錯誤詳情:\n{traceback.format_exc()}")
        return None

def validate_image_url(url):
    """驗證圖片 URL 是否符合 LINE 的要求"""
    try:
        # 檢查是否為 HTTPS
        if not url.startswith('https'):
            print("URL 必須使用 HTTPS")
            return False

        # 檢查副檔名
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        valid_extensions = ('.jpg', '.jpeg', '.png', '.gif')
        if not any(path.endswith(ext) for ext in valid_extensions):
            print("URL 必須以 .jpg, .jpeg, .png 或 .gif 結尾")
            return False

        # 檢查檔案大小（發送 HEAD 請求）
        response = requests.head(url, allow_redirects=True, timeout=5)
        if response.status_code != 200:
            print(f"無法訪問 URL: {response.status_code}")
            return False

        content_length = int(response.headers.get('content-length', 0))
        if content_length > 10 * 1024 * 1024:  # 10MB
            print("圖片大小超過 10MB 限制")
            return False

        return True
    except Exception as e:
        print(f"驗證 URL 時發生錯誤: {str(e)}")
        return False

def get_shareable_link(service, file_id):
    """獲取可共享的連結並確保檔案權限設定正確"""
    try:
        for attempt in range(MAX_RETRIES):
            try:
                # 設定檔案權限為公開
                permission = {
                    'type': 'anyone',
                    'role': 'reader'
                }
                service.permissions().create(
                    fileId=file_id,
                    body=permission
                ).execute()

                # 獲取檔案資訊
                file = service.files().get(
                    fileId=file_id,
                    fields='webContentLink,mimeType'
                ).execute()

                # 處理連結格式
                content_link = file.get('webContentLink', '')
                if content_link:
                    # 移除下載參數
                    content_link = content_link.replace('&export=download', '')
                    
                    # 如果是圖片檔案，確保有正確的副檔名
                    mime_type = file.get('mimeType', '')
                    if 'image' in mime_type and not any(content_link.lower().endswith(ext) 
                        for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                        # 根據 MIME type 加入副檔名
                        ext_map = {
                            'image/jpeg': '.jpg',
                            'image/png': '.png',
                            'image/gif': '.gif'
                        }
                        content_link += ext_map.get(mime_type, '.jpg')

                    if validate_image_url(content_link):
                        print(f"成功產生有效的圖片連結: {content_link}")
                        return content_link
                    else:
                        print("產生的連結未通過驗證")
                        continue

            except Exception as e:
                print(f"嘗試 {attempt + 1}/{MAX_RETRIES} 失敗: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)  # 指數退避
                continue

        print("無法產生有效的圖片連結")
        return None

    except Exception as e:
        print(f"產生連結時發生錯誤: {str(e)}")
        print(f"錯誤詳情:\n{traceback.format_exc()}")
        return None

def find_report_file(service, folder_id):
    """找到對應的報表文件"""
    try:
        # 取得昨天的日期
        jst = pytz.timezone('Asia/Tokyo')
        yesterday = datetime.now(jst) - timedelta(days=1)
        target_month = yesterday.strftime('%Y年%m月')    # 資料夾格式：2024年12月
        target_filename = yesterday.strftime('%m%d')     # 檔案格式：1213
        
        print(f"開始搜尋檔案 - 月份資料夾: {target_month}, 目標檔名: {target_filename}")
        
        # 找月份資料夾
        month_query = f"name = '{target_month}' and '{folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder'"
        month_results = service.files().list(q=month_query).execute()
        month_folders = month_results.get('files', [])
        
        if not month_folders:
            print(f"錯誤: 找不到月份資料夾 {target_month}")
            return None
            
        month_folder_id = month_folders[0]['id']
        print(f"找到月份資料夾 ID: {month_folder_id}")
        
        # 在月份資料夾中找目標檔案
        file_query = f"'{month_folder_id}' in parents and name contains '{target_filename}'"
        file_results = service.files().list(q=file_query).execute()
        files = file_results.get('files', [])
        
        if not files:
            print(f"錯誤: 在 {target_month} 資料夾中找不到 {target_filename} 的檔案")
            return None
            
        target_file = files[0]
        print(f"成功找到檔案: {target_file['name']} (ID: {target_file['id']})")
        return target_file
        
    except Exception as e:
        print(f"搜尋檔案時發生錯誤: {str(e)}")
        print(f"錯誤詳情:\n{traceback.format_exc()}")
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
            
            print(f"開始處理 {report_date} 的報表")
            
            # 處理 Google Drive 檔案
            service = get_drive_service()
            file_info = None
            image_url = None
            
            if service:
                print("成功連接 Google Drive，開始搜尋檔案")
                file_info = find_report_file(service, FOLDER_ID)
                if file_info:
                    print(f"找到檔案，開始處理圖片連結")
                    image_url = get_shareable_link(service, file_info['id'])
            
            if not image_url:
                print("無法獲取有效的圖片連結")
                return False
            
            # 對每個群組發送訊息
            for group_id in GROUP_IDS:
                try:
                    print(f"開始發送到群組: {group_id}")
                    
                    # 發送文字訊息
                    message = TextMessage(text=f"各位好，{report_date}大阪新今宮營運報表如下")
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=group_id,
                            messages=[message]
                        )
                    )
                    print(f"文字訊息發送成功 - 群組: {group_id}")
                    
                    # 確保圖片 URL 有效後再發送
                    if validate_image_url(image_url):
                        image_message = ImageMessage(
                            originalContentUrl=image_url,
                            previewImageUrl=image_url
                        )
                        line_bot_api.push_message(
                            PushMessageRequest(
                                to=group_id,
                                messages=[image_message]
                            )
                        )
                        print(f"圖片發送成功 - 群組: {group_id}")
                    else:
                        print(f"圖片 URL 無效，跳過發送圖片")
                        return False
                    
                except Exception as e:
                    print(f"發送到群組 {group_id} 時發生錯誤: {str(e)}")
                    continue
            
            return True
            
    except Exception as e:
        print(f"發送報表時發生錯誤: {str(e)}")
        print(f"錯誤詳情:\n{traceback.format_exc()}")
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
