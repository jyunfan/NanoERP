# customer tabl (客戶資料表)
| Field Name | Data Type | Description |
| ------- | ------ | --- |
| id | int | 客戶ID |
| car_number | int | 車次 |
| name | string | 名稱 |
| checkout_code | int | 結帳代碼 |
| phone1 | string | 電話1 |
| phone2 | string | 電話2 |
| market | int | 市場代碼 |
 
## 結帳代碼
0: 不印
1: 出貨
2: 日
3: 週
4: 旬
5: 半月
6: 月

## 市場代碼
1: 其餘市場
2: 建國市場
3: 南部市場

# product table (產品資料表)
| Field Name | Data Type | Description |
| ------ | ------ | ---- |
| id | int | 產品ID |
| car_number | int | 車次 |
| detailed_name | string | 詳細名稱 |
| short_name | string | 簡稱 |
| purchase_price | int | 進價 |
| sale_price | int | 售價 |
| safety_stock | int | 安存量 |
| return_unit | string | 銷退單位 |

# order table (訂單資料表)
| Field Name | Data Type | Description |
| ---------- | --------- | ----------- |
| customer_id | int | 客戶ID (foreign key: customer.id) |
| product_id | int | 產品ID (foreign key: product.id) |
| quantity | int | 數量 |
| order_date | date | 訂單日期 |
| is_return | boolean | 最後一筆是否為退貨 |
| posted | boolean | 是否已過帳 |