// 文件名: api/analyze.js

const csv = require('csv-parser');
const stream = require('stream');
const _ = require('lodash'); // 用於數據計算和處理

// Vercel Serverless Function (Node.js/Express 格式)
module.exports = async (req, res) => {
    // 設置 CORS 標頭
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    if (req.method !== 'POST') {
        return res.status(405).json({ success: false, message: 'Method Not Allowed' });
    }

    try {
        const { data: rawData, clean_missing, normalize_data, sort_sales } = req.body;
        if (!rawData) {
            return res.status(400).json({ success: false, message: '數據為空。' });
        }

        const data = [];
        const bufferStream = new stream.PassThrough();
        bufferStream.end(rawData);

        // 1. 數據解析 (CSV 解析)
        await new Promise((resolve, reject) => {
            bufferStream
                .pipe(csv())
                .on('data', (row) => {
                    // 將 Sales 欄位轉換為數字，如果轉換失敗則設為 NaN
                    row.Sales = parseFloat(row.Sales);
                    data.push(row);
                })
                .on('end', () => resolve())
                .on('error', (err) => reject(err));
        });

        let processedData = data;

        // 2. 數據處理核心邏輯

        // 2.1 清理缺失值
        if (clean_missing) {
            // 移除 Sales 為 NaN 的行
            processedData = processedData.filter(row => !isNaN(row.Sales));
        }

        const salesValues = processedData.map(row => row.Sales);

        // 2.2 數據標準化 (Z-Score)
        if (normalize_data && salesValues.length > 0) {
            const mean = _.mean(salesValues);
            const std = Math.sqrt(_.sum(salesValues.map(v => Math.pow(v - mean, 2))) / salesValues.length);

            if (std > 0) {
                processedData = processedData.map(row => {
                    // 計算 Z-Score，並四捨五入
                    row.Sales = _.round((row.Sales - mean) / std, 4);
                    return row;
                });
            } else {
                 // 標準差為 0，所有值都一樣，Z-Score 為 0
                processedData = processedData.map(row => { row.Sales = 0; return row; });
            }
        }

        // 2.3 排序
        if (sort_sales) {
            processedData = _.sortBy(processedData, ['Sales']).reverse();
        }

        // 3. 生成統計摘要 (模擬 Pandas describe())
        const stats = {};
        if (salesValues.length > 0) {
            const validSales = processedData.map(row => row.Sales).filter(v => !isNaN(v));

            if (validSales.length > 0) {
                stats.Sales = {
                    count: validSales.length,
                    mean: _.mean(validSales),
                    std: Math.sqrt(_.sum(validSales.map(v => Math.pow(v - _.mean(validSales), 2))) / validSales.length),
                    min: _.min(validSales),
                    max: _.max(validSales)
                };
            }
        }

        // 4. 返回結果
        return res.status(200).json({
            success: true,
            processed_data: processedData,
            statistics: stats,
            message: "Node.js 數據分析成功完成。"
        });

    } catch (error) {
        console.error('Node.js 處理數據時發生錯誤:', error);
        return res.status(500).json({ success: false, message: `後端處理數據時發生錯誤: ${error.message}` });
    }
};