# customer table (客戶資料表)
| Field Name | Data Type | Description |
| ------- | ------ | --- |
| id | int | 客戶ID |
| car_number | int | 車次 |
| name | string | 名稱 |
| checkout_code | int | 結帳代碼 |
| phone1 | string | 電話1 |
| phone2 | string | 電話2 |
| market | int | 市場代碼 |

# supplier table (廠商資料表)
| Field Name | Data Type | Description |
| ------ | ------ | ---- |
| id | int | 廠商ID |
| name | string | 名稱 |
| phone1 | string | 電話1 |
| phone2 | string | 電話2 |
 
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
| frequent | boolean | 常用產品 |

# order table (訂單資料表)
正式訂單資料。使用者輸入時不直接寫入本表；執行過帳後，才用當下工作日期寫入 `order_date`。

| Field Name | Data Type | Description |
| ---------- | --------- | ----------- |
| customer_id | int | 客戶ID (foreign key: customer.id) |
| product_id | int | 產品ID (foreign key: product.id) |
| quantity | int | 數量 |
| order_date | date | 過帳時的工作日期 |
| is_return | boolean | 最後一筆是否為退貨 |
| posting_batch_id | int | 過帳批次ID |
| purchase_price | int | 過帳時進價快照 |
| sale_price | int | 過帳時售價快照 |
| posted_at | string | 過帳時間 |

# order_draft table (訂單暫存資料表)
使用者在客戶訂單畫面輸入中的資料。暫存資料不屬於任何工作日期；執行過帳後才會寫入正式訂單。

| Field Name | Data Type | Description |
| ---------- | --------- | ----------- |
| customer_id | int | 客戶ID (foreign key: customer.id) |
| product_id | int | 產品ID (foreign key: product.id) |
| quantity | int | 數量 |
| is_return | boolean | 是否為退貨 |
| created_at | string | 建立時間 |
| updated_at | string | 更新時間 |

# posting_batch table (過帳批次資料表)
每次執行過帳會建立一筆批次資料。

| Field Name | Data Type | Description |
| ---------- | --------- | ----------- |
| work_date | date | 過帳使用的工作日期 |
| status | string | 過帳狀態 |
| note | string | 備註 |
| posted_at | string | 過帳時間 |

# customer_product table (客戶產品資料表)
| Field Name | Data Type | Description |
| ---------- | --------- | ----------- |
| customer_id | int | 客戶ID (foreign key: customer.id) |
| product_id | int | 產品ID (foreign key: product.id) |
| sale_price | int | 售價 |

# customer_freq_product (客戶常用產品資料表)
| Field Name | Data Type | Description |
| ---------- | --------- | ----------- |
| customer_id | int | 客戶ID (foreign key: customer.id) |
| product_id | int | 產品ID (foreign key: product.id) |

# supplier_freq_product (廠商常用產品資料表)
| Field Name | Data Type | Description |
| ---------- | --------- | ----------- |
| supplier_id | int | 廠商ID (foreign key: supplier.id) |
| product_id | int | 產品ID (foreign key: product.id) |

# purchase_order (廠商進退貨資料表)
| Field Name | Data Type | Description |
| ---------- | --------- | ----------- |
| supplier_id | int | 廠商ID (foreign key: supplier.id) |
| product_id | int | 產品ID (foreign key: product.id) |
| quantity | int | 數量 |
| is_return | boolean | 是否為退貨 |
| order_date | date | 進退貨日期 |


# 代碼表
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
