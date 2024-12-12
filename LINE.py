def send_report():
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
                print("開始搜尋報表檔案")
                service = get_drive_service()
                if service:
                    # 使用實際的資料夾 ID
                    folder_id = "1yNH3mP2LAUnZn8EjjGrzzpzNavkSzMqB"
                    file_id = find_report_file(service, folder_id)
                    
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
