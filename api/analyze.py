# 文件名: api/analyze.py

import json
import pandas as pd
import numpy as np # 用於標準化計算
import io

def handler(request):
    """
    Vercel Serverless Function 的標準入口點。
    處理前端傳來的數據和處理選項。
    """
    
    # 設置 CORS 標頭
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }
    
    # 處理 OPTIONS 請求 (CORS 預檢)
    if request['httpMethod'] == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
        
    if request['httpMethod'] != 'POST':
        return {
            'statusCode': 405,
            'headers': headers,
            'body': json.dumps({"success": False, "message": "Method Not Allowed"})
        }

    try:
        # 1. 解析前端傳來的 JSON 數據
        # Vercel Serverless Function 提供了 body
        body = json.loads(request['body'])
        raw_data = body.get('data', '')
        clean_missing = body.get('clean_missing', False)
        normalize_data = body.get('normalize_data', False)
        sort_sales = body.get('sort_sales', False)
        
        if not raw_data:
            # 必須返回 Vercel 要求的格式
            return {
                'statusCode': 400, 
                'headers': headers,
                'body': json.dumps({"success": False, "message": "數據為空。"})
            }

        # 2. 將 CSV 字符串讀取到 Pandas DataFrame
        df = pd.read_csv(io.StringIO(raw_data))

        # 確保 Sales 欄位是數字類型
        if 'Sales' in df.columns:
            df['Sales'] = pd.to_numeric(df['Sales'], errors='coerce')
        
        # 3. 數據處理核心邏輯 (依據前端開關)

        # 3.1 清理缺失值
        if clean_missing:
            # 移除所有包含 NaN 的行
            df.dropna(inplace=True) 

        # 3.2 數據標準化 (Z-Score) - 使用 numpy 替代 scipy
        if normalize_data and 'Sales' in df.columns:
            # 避免對空數據進行計算
            if not df['Sales'].empty:
                mean = df['Sales'].mean()
                std = df['Sales'].std()
                # 只有標準差大於 0 時才執行 Z-Score
                if std > 0:
                    df['Sales_ZScore'] = (df['Sales'] - mean) / std
                else:
                    df['Sales_ZScore'] = 0 # 避免除以零
                
                # 替換 Sales 欄位，並將 Z-Score 四捨五入到 4 位小數
                df['Sales'] = df['Sales_ZScore'].round(4)
                df.drop(columns=['Sales_ZScore'], inplace=True, errors='ignore')


        # 3.3 排序
        if sort_sales and 'Sales' in df.columns:
            # 忽略非數字值進行排序
            df.sort_values(by='Sales', ascending=False, inplace=True, na_position='last')

        # 4. 生成統計摘要
        stats = {}
        # 僅對數字欄位進行描述性統計
        if 'Sales' in df.columns:
            # 確保統計時忽略 NaN
            valid_sales = df['Sales'].dropna()
            if not valid_sales.empty:
                stats['Sales'] = valid_sales.describe().to_dict()
        
        # 5. 準備結果
        # 將處理後的 DataFrame 轉換為 JSON 列表
        processed_data_list = df.fillna('N/A').to_dict('records')

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
        # 捕捉所有運行時錯誤並返回 500
        error_msg = f"後端處理數據時發生錯誤: {str(e)}"
        print(f"ERROR: {error_msg}") # 輸出到 Vercel 運行時日誌
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({"success": False, "message": error_msg})
        }