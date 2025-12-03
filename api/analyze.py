# 文件名: api/analyze.py

import json
import pandas as pd
import io
from scipy.stats import zscore # 引入 scipy 進行標準化 (通常 Pandas 自帶或依賴 numpy/scipy)

def handler(event, context):
    """
    Vercel Serverless Function 的入口點。
    處理前端傳來的數據和處理選項。
    """
    
    # 設置 CORS 標頭，允許前端調用
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }
    
    # 處理 OPTIONS 請求 (CORS 預檢)
    if event['httpMethod'] == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
        
    if event['httpMethod'] != 'POST':
        return {
            'statusCode': 405,
            'headers': headers,
            'body': json.dumps({"success": False, "message": "Method Not Allowed"})
        }

    try:
        # 1. 解析前端傳來的 JSON 數據
        body = json.loads(event['body'])
        raw_data = body.get('data', '')
        clean_missing = body.get('clean_missing', False)
        normalize_data = body.get('normalize_data', False)
        sort_sales = body.get('sort_sales', False)
        
        if not raw_data:
            raise ValueError("數據為空。")

        # 2. 將 CSV 字符串讀取到 Pandas DataFrame
        df = pd.read_csv(io.StringIO(raw_data))

        # 3. 數據處理核心邏輯 (依據前端開關)

        # 3.1 清理缺失值
        if clean_missing:
            df.dropna(inplace=True)

        # 3.2 數據標準化 (Z-Score)
        if normalize_data and 'Sales' in df.columns:
            # 確保 'Sales' 是數字類型
            df['Sales'] = pd.to_numeric(df['Sales'], errors='coerce')
            df['Sales_ZScore'] = zscore(df['Sales'])
            # 為了簡潔顯示，這裡我們將 'Sales' 替換為 ZScore
            df['Sales'] = df['Sales_ZScore']
            df.drop(columns=['Sales_ZScore'], inplace=True)


        # 3.3 排序
        if sort_sales and 'Sales' in df.columns:
            df.sort_values(by='Sales', ascending=False, inplace=True)

        # 4. 生成統計摘要
        # 僅對數字欄位進行描述性統計
        stats = df.describe(include=[pd.np.number]).T.to_dict()
        
        # 5. 準備結果
        # 將處理後的 DataFrame 轉換為 JSON 列表，以便前端 JS 處理
        processed_data_list = df.fillna('').to_dict('records')

        response_data = {
            "success": True,
            "processed_data": processed_data_list,
            "statistics": stats,
            "message": "數據分析成功完成。"
        }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response_data)
        }

    except Exception as e:
        print(f"處理錯誤: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({"success": False, "message": f"伺服器錯誤: {str(e)}"})
        }