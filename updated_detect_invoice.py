import os
import cv2
import numpy as np
import re
import matplotlib.pyplot as plt
from google.cloud import vision
from unidecode import unidecode
from datetime import datetime
import connectdb as conn
# lib for view
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox

# Biến khởi tạo Google Vision
api_path = None
client = None
# Biến lưu trữ đường dẫn đã chọn
img_name = None
selected_path = None
img_path = None
folder_list_path = None
option_state = 0    # 0 for file and 1 for folder

def get_api_path():
    '''Get API path location'''
    current_dir = os.path.dirname(os.path.abspath(__file__))
    api_path = os.path.join(current_dir, 'ocr-version-01-5121e0c17319.json')
    return api_path

def config_google_vision(api_path):
    '''Google Vision API config function (file containing API info)'''
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = api_path
    return vision.ImageAnnotatorClient()

def read_and_preprocess_image(image_path):
    '''Reads and converts images to grayscale'''
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image, gray

def apply_binary_filter(gray_image, threshold_value=150):
    '''Applies a binary filter to highlight the lines'''
    _, binary = cv2.threshold(gray_image, threshold_value, 255, cv2.THRESH_BINARY_INV)
    return binary

# detect table ------------------------------------------------------------------------- 

def detect_table_lines(binary_image):
    '''Creates horizontal and vertical lines using expansion and contraction'''
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 10))
    horizontal_lines = cv2.morphologyEx(binary_image, cv2.MORPH_OPEN, horizontal_kernel)
    vertical_lines = cv2.morphologyEx(binary_image, cv2.MORPH_OPEN, vertical_kernel)
    table_lines = cv2.add(horizontal_lines, vertical_lines)
    return table_lines

def extract_table_from_image(image, table_lines):
    '''Find and cut table'''
    contours, _ = cv2.findContours(table_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        table_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(table_contour)
        cropped_table = image[y:y+h, x:x+w]
        return cropped_table
    return None

def detect_and_filter_columns(cropped_table, min_line_length=50, max_line_gap=10, threshold_distance=20):
    '''Detect and filter the positions of columns'''
    gray_cropped = cv2.cvtColor(cropped_table, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray_cropped, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=min_line_length, maxLineGap=max_line_gap)

    column_positions = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(x1 - x2) < 5:
                column_positions.append(x1)

    column_positions = sorted(list(set(column_positions)))
    filtered_positions = []
    for pos in column_positions:
        if not filtered_positions or pos - filtered_positions[-1] > threshold_distance:
            filtered_positions.append(pos)
    return filtered_positions

def detect_text_in_columns(client, cropped_table, filtered_positions):
    '''Recognize text in each column using Google Vision API and store data in a 2D matrix'''
    data_matrix = []  # Ma trận 2 chiều để lưu dữ liệu

    if len(filtered_positions) > 1:
        for i in range(len(filtered_positions) - 1):
            col_start = filtered_positions[i]
            col_end = filtered_positions[i + 1]
            column = cropped_table[:, col_start:col_end]
            
            _, encoded_column = cv2.imencode('.png', column)
            content = encoded_column.tobytes()
            image = vision.Image(content=content)
            
            response = client.document_text_detection(image=image)
            texts = response.text_annotations
            
            column_data = []  # Danh sách con để lưu dữ liệu của từng cột
            if texts:
                full_text = texts[0].description
                # Chia văn bản theo dòng và lưu từng dòng vào danh sách con của cột
                for line in full_text.splitlines():
                    column_data.append(line.strip())
            
            # Thêm danh sách của cột vào ma trận 2 chiều
            data_matrix.append(column_data)
    else:
        print("Không tìm thấy đủ cột.")
        return False

    # Hiển thị ma trận 2 chiều
    print("\nData Matrix:")
    for row in zip(*data_matrix):  # zip để sắp xếp các dòng theo thứ tự
        print(row)

    return data_matrix  # Trả về ma trận 2 chiều

def process_data_matrix(data_matrix):
    '''Process data in the matrix based on specified rules'''

    for col in range(len(data_matrix)):
        # Kiểm tra nếu hàng đầu tiên của cột chứa từ "Mã hàng"
        if "Mã hàng" in data_matrix[col][0]:
            for row in range(1, len(data_matrix[col])):
                # Xóa tất cả dấu cách trong các hàng còn lại nếu cột có "Mã hàng" ở hàng đầu tiên
                data_matrix[col][row] = unidecode(data_matrix[col][row]).replace(" ", "")

        if "Thành Tiền" in data_matrix[col][0] or "SL" in data_matrix[col][0] or "Đơn giá" in data_matrix[col][0]:
            for row in range(1, len(data_matrix[col])):
                # Xóa tất cả dấu cách trong các hàng còn lại nếu cột có "Thành Tiền" ở hàng đầu tiên
                data_matrix[col][row] = data_matrix[col][row].replace(" ", "")
                data_matrix[col][row] = data_matrix[col][row].replace("o", "0").replace("O", "0").replace("Q", "0")
                data_matrix[col][row] = re.sub(r"[^\d]", "", data_matrix[col][row])
        
        for row in range(len(data_matrix[col])):
            # Loại bỏ các ký tự không thuộc bảng chữ cái tiếng Việt, trừ '-' và ','
            data_matrix[col][row] = re.sub(r"[^a-zA-ZÀ-ỹà-ỹ0-9\s\-,]", "", data_matrix[col][row])
            # Thay thế nhiều dấu cách liên tiếp bằng một dấu cách duy nhất
            data_matrix[col][row] = re.sub(r"\s{2,}", " ", data_matrix[col][row]).strip()

    return data_matrix

def sum_total_amount(data_matrix):
    '''sum the "Thành tiền" column'''
    total_amount = 0
    for col in range(len(data_matrix)):
        if "Thành Tiền" in data_matrix[col][0]:
            for row in range(1, len(data_matrix[col])):
                total_amount += int(data_matrix[col][row])
    return total_amount

def check_equal_column_lengths(data_matrix_processed):
    '''Check if all columns in the data matrix have the same number of elements'''
    if not data_matrix_processed:
        return False  # Nếu ma trận rỗng, coi như có cùng số phần tử

    # Kiểm tra độ dài của ma trận (số cột)
    if len(data_matrix_processed) != 8:
        print("Error: Data matrix does not have enough columns. (!=8)")
        return False
    # Lấy số phần tử của cột đầu tiên
    column_length = len(data_matrix_processed[0])

    # So sánh số phần tử của từng cột với cột đầu tiên
    for col in data_matrix_processed:
        if len(col) != column_length:
            print("Columns dont have the same number of elements")
            return False  # Nếu tìm thấy cột có số phần tử khác, trả về 0

    return True  # Nếu tất cả các cột có cùng số phần tử, trả về 1

def Read_data_matrix(data_matrix_processed):
    """
    Hàm đọc ma trận data_matrix_processed và lưu các cột vào các biến
    với tên tiếng Anh phù hợp, sau đó in ra nội dung của các biến.
    """
    # Gán các cột vào các biến phù hợp
    serial_numbers = data_matrix_processed[0]  # STT
    product_codes = data_matrix_processed[1]  # Mã hàng
    product_names = data_matrix_processed[2]  # Tên hàng hóa, dịch vụ
    units = data_matrix_processed[3]  # ĐVT
    estimated_quantities = data_matrix_processed[4]  # Số lượng theo chứng từ
    actual_quantities = data_matrix_processed[5]  # Số lượng theo thực nhập
    unit_prices = data_matrix_processed[6]  # Đơn giá
    total_prices = data_matrix_processed[7]  # Thành tiền

    # In nội dung của từng biến
    print("Serial Numbers (STT):", serial_numbers)
    print("Product Codes (Mã hàng):", product_codes)
    print("Product Names (Tên hàng hóa, dịch vụ):", product_names)
    print("Units (ĐVT):", units)
    print("Quantities (Số lượng theo chứng từ):", estimated_quantities)
    print("Quantities (Số lượng thực nhập):", actual_quantities)
    print("Unit Prices (Đơn giá):", unit_prices)
    print("Total Prices (Thành tiền):", total_prices)

    # In ví dụ từng giá trị
    for i in range(len(serial_numbers)):
        print(f"Row {i + 1}:")
        print(f"  Serial Number: {serial_numbers[i]}")
        print(f"  Product Code: {product_codes[i]}")
        print(f"  Product Name: {product_names[i]}")
        print(f"  Unit: {units[i]}")
        print(f"  Estimated quantity: {estimated_quantities[i]}")
        print(f"  Actual quantity: {actual_quantities[i]}")
        print(f"  Unit Price: {unit_prices[i]}")
        print(f"  Total Price: {total_prices[i]}")
        text_display.insert("1.0", "\n" + f"Row {i + 1}:\n  Serial Number: {serial_numbers[i]}\n  Product Code: {product_codes[i]}\n  Product Name: {product_names[i]}\n  Unit: {units[i]}\n  Estimated quantity: {estimated_quantities[i]}\n  Actual quantity: {actual_quantities[i]}\n  Price: {unit_prices[i]}\n  Total Price: {total_prices[i]}")
# detect invoice -------------------------------------------------------------------------

def extract_text_from_image(client, image):
    '''Extract text from image using Google Vision API'''
    _, encoded_image = cv2.imencode('.png', image)
    content = encoded_image.tobytes()
    vision_image = vision.Image(content=content)
    response = client.document_text_detection(image=vision_image)
    texts = response.text_annotations
    if texts:
        return texts[0].description
    return ""

def extract_model_number(text):
    '''Extract "Số phiếu" from text'''
    pattern = r"Số phiếu\s*:\s*(.+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return re.sub(r"[^\d]", "", match.group(1))  # Remove non-numeric characters
    return None

import re

def extract_delivery(text):
    '''Extract "Người giao hàng" from text, and replace multiple spaces with one, handle ellipsis'''
    # Pattern tìm kiếm chuỗi "Người giao hàng" với khoảng trắng linh động
    pattern = r"\s*Người\s*giao\s*hàng\s*:?\s*\.*(.+)"
    match = re.search(pattern, text, re.IGNORECASE)  # Tìm kiếm với biểu thức chính quy không phân biệt hoa thường
    
    if match:
        # Loại bỏ khoảng trắng thừa ở đầu và cuối
        delivery = match.group(1).strip()  
        # Thay thế nhiều khoảng trắng liên tiếp bằng một khoảng trắng duy nhất
        delivery = re.sub(r"\s{2,}", " ", delivery)
        # Loại bỏ dấu chấm (và các ký tự không mong muốn như dấu chấm lửng)
        delivery = re.sub(r"[.]+", "", delivery).strip()
        return delivery
    return None


def extract_date(text):
    '''Extract "Ngày", "Tháng", "Năm" based on the structure: "Ngày ....... tháng ........ năm .........", including periods and spaces, replace "o" with "0", and remove non-numeric characters'''
    
    # Điều chỉnh biểu thức chính quy để chấp nhận dấu chấm và khoảng trắng giữa các phần ngày, tháng, năm
    date_pattern = r"Ngày\s*\.*\,*([0-9a-zA-Z\s\.]+)\,*\.*\s*tháng\s*\.*\,*([0-9a-zA-Z\s\.]+)\,*\.*\s*năm\s*\.*\,*([0-9a-zA-Z\s\.]+)"
    
    date_match = re.search(date_pattern, text, re.IGNORECASE)
    
    if date_match:
        # Lấy các phần ngày, tháng, năm từ nhóm bắt được
        day = date_match.group(1).strip()
        month = date_match.group(2).strip()
        year = date_match.group(3).strip()
        
        # Thay "o" và "O" thành "0"
        day = day.replace("o", "0").replace("O", "0")
        month = month.replace("o", "0").replace("O", "0")
        year = year.replace("o", "0").replace("O", "0")
        
        # Loại bỏ tất cả các ký tự không phải là số, chỉ giữ lại số
        day = re.sub(r"[^\d]", "", day)
        month = re.sub(r"[^\d]", "", month)
        year = re.sub(r"[^\d]", "", year)
        
        # Trả về ngày tháng năm dưới dạng yyyy-mm-dd
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    return None



def extract_tax_code(text):
    '''Extract "Mã số thuế" for the seller (Đơn vị bán hàng) based on "Người giao hàng"'''
    # Tìm "Mã số thuế" trong đoạn văn bản
    tax_pattern = r"Mã số thuế[^0-9]*(\d[\d.]*)"  # Chấp nhận dấu "." hoặc ký tự xen giữa
    tax_match = re.search(tax_pattern, text, re.IGNORECASE)
    
    if tax_match:
        # Loại bỏ dấu "." khỏi mã số thuế
        tax_code_clean = re.sub(r"o", "0", tax_match.group(1))
        tax_code_clean = re.sub(r"O", "0", tax_match.group(1))
        tax_code_clean = re.sub(r"[^\d]", "", tax_match.group(1)) # Remove non-numeric characters
        return tax_code_clean
    
    # Trả về None nếu không tìm thấy
    return None

def extract_report_number(text):
    '''Extract "số biên bản bàn giao"'''
    pattern = r"Theo\s*biên\s*bản\s*bàn\s*giao\s*hàng\s*hóa\s*số\s*:\s*(.+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        # Gán lại match sau khi thay thế 'o' và 'O' bằng '0'
        result = re.sub(r"[oO]", "0", match.group(1))  
        # Xóa các ký tự không phải số
        if result != "":
            return re.sub(r"[^\d]", "", result)
    return None

def extract_warehouse(text):
    '''Extract warehouse "Nhập tại kho:"'''
    pattern = r"Nhập\s*tại\s*kho\s*:\s*(.+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        # Loại bỏ ký tự ko thuộc bảng chữ cái và - 
        result = re.sub(r"[^a-zA-ZÀ-ỹà-ỹ0-9\s\-]", "", match.group(1))  
        return result
    return None


# def extract_total_amount(text):
#     '''Extract "Tổng tiền" from text'''
#     pattern = r"Tổng tiền\s*:\s*\.*(.+)"
#     match = re.search(pattern, text, re.IGNORECASE)
#     if match:
#         raw_value = re.sub(r"o", "0", match.group(1))
#         raw_value = re.sub(r"O", "0", raw_value)
#         raw_value = re.sub(r"Q", "0", raw_value)
#         raw_value = re.sub(r"[^\d]", "", raw_value)  # Remove non-numeric characters
#         if raw_value:
#             return int(raw_value)  # Return as integer without spaces
#     return None

def process_invoice(image_path, client):
    '''Process the invoice and extract required information'''
    image, gray = read_and_preprocess_image(image_path)
    text = extract_text_from_image(client, image)
    print("extract from API respone: ")
    print(text)
    model_number = extract_model_number(text)
    tax_code = extract_tax_code(text)
    date_time = extract_date(text)
    delivery = extract_delivery(text)
    report_number = extract_report_number(text)
    warehouse = extract_warehouse(text)
    # total_amount = extract_total_amount(text)

    return model_number, tax_code, date_time, delivery, report_number, warehouse

def check_invoice_infor(model_number, tax_code, date_time, delivery, report_number, warehouse):
    if model_number is None or model_number == "" or tax_code is None or tax_code == "" or date_time is None or date_time == "" or delivery is None or delivery == "" or report_number is None or report_number == "" or warehouse is None or warehouse == "":
        return False
    return True
    
# view code -------------------------------------------------------------------------

def select_folder():
    '''Chọn thư mục, hiển thị tên thư mục trên giao diện và trả về danh sách file hình ảnh'''
    import os

    # Hiển thị hộp thoại chọn thư mục
    select_folder_path = filedialog.askdirectory()
    if select_folder_path:
        # Hiển thị đường dẫn thư mục trên giao diện
        entry_file_name.config(state="normal")
        entry_file_name.delete(0, tk.END)
        entry_file_name.insert(0, select_folder_path)
        entry_file_name.config(state="readonly")

        global selected_path
        global option_state
        global folder_list_path
        selected_path = select_folder_path
        # Update state 1 for select folder
        option_state = 1

        # Duyệt qua thư mục để lấy danh sách các file .jpg và .png
        image_files = [
            os.path.join(select_folder_path, f)
            for f in os.listdir(select_folder_path)
            if f.lower().endswith(('.jpg', '.png'))
        ]
        # In ra danh sách file (nếu cần kiểm tra)
        print("Image files found:")
        for img_path in image_files:
            print(img_path)
        folder_list_path = image_files
    else:
        folder_list_path = []  # Nếu không chọn thư mục, trả về danh sách rỗng

def select_file():
    '''Chọn tệp và hiển thị tên tệp trong ô chỉ đọc'''
    file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.png")])
    if file_path:
        entry_file_name.config(state="normal")
        entry_file_name.delete(0, tk.END)
        entry_file_name.insert(0, file_path)
        entry_file_name.config(state="readonly")

        global selected_path
        global img_path
        global option_state
        global img_name
        selected_path = file_path
        img_path = file_path
        img_name = os.path.basename(file_path)
        # update state 0 for select file
        option_state = 0

def detect_text():
    '''Thực hiện nhận dạng văn bản tệp đã chọn và hiển thị kết quả'''
    global client
    global img_path
    global text_display
    global img_name
    image, gray = read_and_preprocess_image(img_path)
    binary = apply_binary_filter(gray)
    result_text = f"\nfile {img_name}"

    # Detect the infor of invoice
    model_number, tax_code, date_time, delivery, report_number, warehouse = process_invoice(img_path, client)

    if not check_invoice_infor(model_number, tax_code, date_time, delivery, report_number, warehouse):
        result_text += "\n\tKhông nhận dạng đủ thông tin hóa đơn"
        text_display.insert("1.0", result_text)
        return False

    # Detect the infor of table
    table_lines = detect_table_lines(binary)
    cropped_table = extract_table_from_image(image, table_lines)
    if cropped_table is None:
        result_text += f"\n\tNhận dạng bảng không thành công"
        text_display.insert("1.0", result_text)
        return False
    
    filtered_positions = detect_and_filter_columns(cropped_table)
    data_matrix = detect_text_in_columns(client, cropped_table, filtered_positions)
    data_matrix_processed = process_data_matrix(data_matrix)
    total_amount = sum_total_amount(data_matrix)
    # Lấy ngày tháng hiện tại
    current_date = datetime.now().strftime('%Y-%m-%d')

    # check data_matrix
    if not check_equal_column_lengths(data_matrix_processed):
        result_text += f"\n\tBảng sản phẩm không đủ thông tin"
        text_display.insert("1.0", result_text)
        return False

    # # Read data_matrix_processed
    # Read_data_matrix(data_matrix_processed)

    # Connect to db
    connection = conn.connect_to_db()
    # Insert order
    order_status = conn.insert_order(connection, int(model_number), tax_code, date_time, current_date, int(total_amount), "01-VT", int(report_number), delivery, warehouse )
    if order_status == 1:
        result_text += f"\n\tSố hóa đơn: {model_number}"
        # Insert order detail
        serial_numbers = data_matrix_processed[0]           # STT
        product_codes = data_matrix_processed[1]            # Mã hàng
        estimated_quantities = data_matrix_processed[4]     # Số lượng theo chứng từ
        actual_quantities = data_matrix_processed[5]        # Số lượng theo thực nhập
        total_prices = data_matrix_processed[7]             # Thành tiền
        for i in range(1,len(serial_numbers)):
            detail_status = conn.insert_order_detail(connection, int(model_number), product_codes[i], int(estimated_quantities[i]), int(actual_quantities[i]), int(total_prices[i]))
            if detail_status == 1:
                result_text += f"\n\t\t{serial_numbers[i]}: thành công"
            elif detail_status == 0:
                result_text += f"\n\t\t{serial_numbers[i]}: không thành công"
    else:
        result_text += f"\n\tThêm thất bại."
    connection.commit()
    # Disconnect to db
    conn.disconnect_from_db(connection)
    text_display.insert("1.0", result_text) #chèn thông tin hóa đơn

def detect():
    global option_state
    global folder_list_path
    global img_path
    global client
    global img_name

    # Bật chế độ chỉnh sửa của view
    text_display.config(state="normal")
    text_display.insert("1.0", "\n---------------------------------------")

    print(option_state)
    if option_state == 0:   # select file 0
        # Detect the table
        detect_text()
    else:   # select folder 1
        for path in folder_list_path:
            img_path = path
            img_name = os.path.basename(path)
            detect_text()

    text_display.config(state="disabled")  # Đặt lại chế độ chỉ đọc

def create_interface():
    # Tạo cửa sổ chính
    root = tk.Tk()
    root.title("Image Detection Interface")
    root.geometry("700x700")

    # Tạo khung cho các nút
    frame_buttons = tk.Frame(root)
    frame_buttons.pack(pady=10)

    # Nút "folder"
    btn_folder = tk.Button(frame_buttons, text="folder", width=10, command=select_folder)
    btn_folder.grid(row=0, column=0, padx=5)

    # Nút "file"
    btn_file = tk.Button(frame_buttons, text="file", width=10, command=select_file)
    btn_file.grid(row=0, column=1, padx=5)

    # Nút "DETECT"
    btn_detect = tk.Button(frame_buttons, text="DETECT", width=10, command=detect)
    btn_detect.grid(row=0, column=2, padx=5)

    # Ô hiển thị tên folder/file (chế độ chỉ đọc)
    label_file = tk.Label(root, text="Folder/File name:")
    label_file.pack()
    
    global entry_file_name
    entry_file_name = tk.Entry(root, width=60, state="readonly")
    entry_file_name.pack(pady=5)

    # Khung lớn nhất để hiển thị các thông báo có thanh cuộn (chế độ chỉ đọc)
    global text_display
    text_frame = tk.Frame(root, bd=2, relief="solid")
    text_frame.pack(padx=20, pady=10, fill="both", expand=True)

    text_display = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, width=50, height=10)
    text_display.pack(pady=5, padx=5, fill="both", expand=True)
    text_display.config(state="disabled")  # Đặt chế độ chỉ đọc cho vùng hiển thị

    # Các nút điều hướng
    btn_prev = tk.Button(root, text="<<", width=5)
    btn_prev.pack(side="left", padx=10, pady=10)

    btn_next = tk.Button(root, text=">>", width=5)
    btn_next.pack(side="right", padx=10, pady=10)

    root.mainloop()


def main():
    global api_path
    global client
    api_path = get_api_path()
    client = config_google_vision(api_path)
    create_interface()
    

main()
