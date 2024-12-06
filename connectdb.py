import pyodbc
from dotenv import load_dotenv
import os

# Tải các biến môi trường từ file .env
load_dotenv()

# Đọc thông tin từ .env
server = os.getenv('DB_SERVER')
database = os.getenv('DB_NAME')
username = os.getenv('DB_USER')
password = os.getenv('DB_PASSWORD')

# Hàm kết nối đến cơ sở dữ liệu SQL Server
def connect_to_db():
    try:
        connection = pyodbc.connect(
            f"DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}"
        )
        print("Kết nối thành công!")
        return connection
    except Exception as e:
        print(f"Kết nối thất bại: {e}")
        return None

# Hàm ngắt kết nối
def disconnect_from_db(connection):
    try:
        if connection:
            connection.close()
            print("Đã đóng kết nối!")
        else:
            print("Không thể đóng kết nối vì không có kết nối.")
    except Exception as e:
        print(f"Lỗi khi ngắt kết nối: {e}")

# Hàm insert order
def insert_order(connection, order_id, TAX, order_date, create_at, total_amount, order_type, report_number, delivery, warehouse_name):
    try:
        cursor = connection.cursor()

        # Câu lệnh gọi Stored Procedure với tham số OUTPUT
        SP_ORDER_I = """
        DECLARE @result INT;  -- Khai báo biến để chứa giá trị OUTPUT

        EXEC [dbo].[SP_ORDER_I]
            @order_id = ?,
            @TAX = ?,
            @order_date = ?,
            @create_at = ?,
            @total_amount = ?,
            @order_type = ?,
            @report_number = ?,
            @delivery = ?,
            @warehouse_name = ?,
            @result = @result OUTPUT;  -- Truyền OUTPUT vào biến @result

        SELECT @result AS result;  -- Trả lại giá trị của OUTPUT
        """

        # Tham số cho Stored Procedure
        params_SP_ORDER_I = (
            order_id,           # order_id
            TAX,                # TAX
            order_date,         # order_date
            create_at,          # create_at
            total_amount,       # total_amount
            order_type,         # order_type
            report_number,      # report_number
            delivery,           # delivery
            warehouse_name        # warehouse_id
        )

        # Thực thi Stored Procedure
        print("Đang thực thi Stored Procedure...")
        cursor.execute(SP_ORDER_I, params_SP_ORDER_I)

        # Lấy kết quả trả về từ OUTPUT
        return_value = cursor.fetchone()  # Nhận kết quả trả về từ câu SELECT @result

        if return_value:
            result = return_value[0]  # Lấy giá trị trả về
            if result == 1:
                print("Insert order successful")
                return 1
            elif result == 0:
                print("Order already exists or error")
                return 0
            else:
                print(f"Unexpected return value: {result}")
                return 0
        else:
            print("Không nhận được giá trị trả về từ Stored Procedure.")
            return 0

        # Ghi thay đổi vào database
        # connection.commit()

    except pyodbc.ProgrammingError as e:
        print(f"Lỗi lập trình SQL: {e}")
    except pyodbc.DataError as e:
        print(f"Lỗi dữ liệu SQL: {e}")
    except Exception as e:
        print(f"Thực thi Stored Procedure thất bại: {e}")
    return 0

def insert_order_detail(connection, order_id, product_id, estimated_quantity, actual_quantity, total_price):
    try:
        cursor = connection.cursor()

        # Câu lệnh gọi Stored Procedure với tham số OUTPUT
        SP_ORDERDETAIL_I = """
        DECLARE @result INT;  -- Khai báo biến để chứa giá trị OUTPUT

        EXEC [dbo].[SP_ORDERDETAIL_I]
            @order_id = ?,
            @product_id = ?,
            @estimated_quantity = ?,
            @actual_quantity = ?,
            @total_price = ?,
            @result = @result OUTPUT;  -- Truyền OUTPUT vào biến @result

        SELECT @result AS result;  -- Trả lại giá trị của OUTPUT
        """

        # Tham số cho Stored Procedure
        params_SP_ORDERDETAIL_I = (
            order_id,              # order_id
            product_id,            # product_id
            estimated_quantity,    # estimated_quantity
            actual_quantity,       # actual_quantity
            total_price            # total_price
        )

        # Thực thi Stored Procedure
        print("Đang thực thi Stored Procedure SP_ORDERDETAIL_I...")
        cursor.execute(SP_ORDERDETAIL_I, params_SP_ORDERDETAIL_I)

        # Lấy kết quả trả về từ OUTPUT
        return_value = cursor.fetchone()  # Nhận kết quả trả về từ câu SELECT @result

        if return_value:
            result = return_value[0]  # Lấy giá trị trả về
            if result == 1:
                print("Insert order detail successful")
                return 1
            elif result == 0:
                print("Order ID does not exist or error")
                return 0
            else:
                print(f"Unexpected return value: {result}")
                return 0
        else:
            print("Không nhận được giá trị trả về từ Stored Procedure.")
            return 0
        # Ghi thay đổi vào database
        # connection.commit()

    except pyodbc.ProgrammingError as e:
        print(f"Lỗi lập trình SQL: {e}")
    except pyodbc.DataError as e:
        print(f"Lỗi dữ liệu SQL: {e}")
    except Exception as e:
        print(f"Thực thi Stored Procedure thất bại: {e}")
    return 0

## TEST FUNCTION
## Kết nối đến cơ sở dữ liệu
# connection = connect_to_db()
# if connection:
    # insert_order(
    #     connection,
    #     7,                  # order_id
    #     '1234567890',       # supplier_id
    #     '2024-12-05',       # order_date
    #     '2024-12-05',       # create_at
    #     1500.00,            # total_amount
    #     '01-VT',            # order_type
    #     5,                  # report_number
    #     'Nguyễn Văn A',     # delivery
    #     'Kho chính'         # warehouse_id
    # )
    # insert_order_detail(
    #     connection, 
    #     2, 
    #     'SG002', 
    #     50, 
    #     40, 
    #     600000.00
    # )
# Ngắt kết nối
# disconnect_from_db(connection)