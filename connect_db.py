import pyodbc
from dotenv import load_dotenv
import os

# Tải các biến môi trường từ file .env
load_dotenv()

print("Kiểm tra biến môi trường:")
print("Server:", os.getenv('DB_SERVER'))
print("Database:", os.getenv('DB_NAME'))
print("User:", os.getenv('DB_USER'))
print("Password:", os.getenv('DB_PASSWORD'))
# Đọc thông tin từ .env
server = os.getenv('DB_SERVER')
database = os.getenv('DB_NAME')
username = os.getenv('DB_USER')
password = os.getenv('DB_PASSWORD')

# Kết nối đến SQL Server
try:
    connection = pyodbc.connect(
        f"DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}"
    )
    print("Kết nối thành công!")
except Exception as e:
    print(f"Kết nối thất bại: {e}")

# Gọi Stored Procedure
try:
    cursor = connection.cursor()
    
    # Câu lệnh gọi Stored Procedure
    SP_Invoice_Detail_I = """
    EXEC [dbo].[SP_Invoice_Detail_I]
        @invoice_number = ?,
        @pro_id = ?,
        @quantity = ?,
        @vat = ?,
        @img = ?
    """
    SP_Invoice_I = """
    EXEC [dbo].[SP_Invoice_I]
        @Tin = ?,
        @invoice_number = ?,
        @total_amount = ?
    """
    # Tham số cho Stored Procedure
    params1 = (
        '101',        # Invoice Number
        'NUOC001',     # Product ID
        10,            # Quantity
        0.10,          # VAT
        b''            # Image (binary)
    )
    params2 = (
        '1009012345',        # Tin
        '103',     # invoice number
        70000           # total amount
    )
    # Thực thi Stored Procedure
    cursor.execute(SP_Invoice_I, params2)
    
    # Kiểm tra kết quả trả về
    if cursor.description:  # Có kết quả trả về từ SELECT
        result = cursor.fetchone()
        if result:
            print("Thông báo từ Stored Procedure:", result[0])
    else:  # Không có SELECT, coi như thành công
        print("Stored Procedure thực thi thành công, không có lỗi.")
    
    connection.commit()  # Ghi thay đổi vào database
except Exception as e:
    print(f"Thực thi Stored Procedure thất bại: {e}")
finally:
    # Đóng kết nối
    if connection:
        connection.close()
        print("Đã đóng kết nối!")


#     # Thực thi câu lệnh
#     cursor.execute(SP_Invoice_I, params2)
#     connection.commit()  # Ghi thay đổi vào database
#     cursor.execute(SP_Invoice_Detail_I, params1)
#     connection.commit()  # Ghi thay đổi vào database
    
#     print("Stored Procedure đã được gọi thành công!")
# except Exception as e:
#     print(f"Thực thi Stored Procedure thất bại: {e}")
# finally:
#     # Đóng kết nối
#     if connection:
#         connection.close()
#         print("Đã đóng kết nối!")

