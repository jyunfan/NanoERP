選單操作
* 可以使用方向鍵上下移動選單
* 可以按數字鍵快速選擇選單項目

Header 功能：顯示 WORK_DATE (預設是今天)，按 F10 可以更改 WORK_DATE


# 客戶資料
| id | car_number | name  | checkout_code | phone1 | phone2 |
| -- | ---------- | ----- | ------------- | ------ | ------ |
| 1  | 123        | 張三  | 1          | 0912345678 | 0987654321 |

操作：可以用方向鍵上下移動，按下Enter鍵進入編輯模式，按下Esc鍵離開編輯模式。
說明：在編輯模式下，按下Enter鍵可以儲存修改，按下Esc鍵可以放棄修改。
說明：checkout_code欄位有特定的選項，按下Enter鍵後會顯示"結帳代碼"的下拉選單供選擇。

# 產品資料
Table: product (產品資料表)

| id | detailed_name | short_name | purchase_price | sale_price | safety_stock | return_unit | frequent |
| -- | ---------- | ------------- | ---------- | -------------- | ---------- | ------------ | --------- |
| 1  | 甜不辣         | 甜不辣          | 100            | 150        | 10           |           | Y |

* 在"常用"的欄位顯示 "V" 表示該產品為常用產品，空白表示非常用。按下Enter鍵可以切換常用狀態。

# 訂單資料

Left panel: 客戶名稱選單，可以上下移動選擇客戶，按下Enter鍵進入該客戶的訂單資料。
Right panel: 顯示選定客戶的訂單資料，可以上下移動選擇訂單，按下Enter鍵進入編輯模式，按下Esc鍵離開編輯模式。

## 訂單編輯頁面
| product_id (col 1) | quantity | product_id (col 2) | quantity | product_id (col 3) | quantity |
| ---------- | -------- | ---------- | -------- | ---------- | -------- |
| 1          | 5        | 2          | 10       | 3          | 15       |
| 4          | 20       |            |          |            |          |