import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import ctypes
import os

# Biến toàn cục
original_image = None
processed_image = None
canny_edges = None
original_contours = None
blurred_image = None
ycrcb_image = None
original_image_with_contours = None
canny_with_contours = None

# Bật DPI scaling
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception as e:
    print(f"Could not set DPI awareness: {e}")

# Palette màu hiện đại
COLORS = {
    'primary': '#2E7D32',      # Xanh lá đậm
    'secondary': '#66BB6A',    # Xanh lá nhạt
    'accent': '#FFA726',       # Cam
    'background': '#F5F5F5',   # Xám nhạt
    'card': '#FFFFFF',         # Trắng
    'text_dark': '#212121',    # Đen
    'text_light': '#757575',   # Xám
    'border': '#E0E0E0',       # Xám viền
    'success': '#4CAF50',      # Xanh success
    'hover': '#43A047'         # Hover color
}

def create_rounded_rectangle(canvas, x1, y1, x2, y2, radius=20, **kwargs):
    """Tạo hình chữ nhật bo góc"""
    points = [
        x1+radius, y1,
        x1+radius, y1,
        x2-radius, y1,
        x2-radius, y1,
        x2, y1,
        x2, y1+radius,
        x2, y1+radius,
        x2, y2-radius,
        x2, y2-radius,
        x2, y2,
        x2-radius, y2,
        x2-radius, y2,
        x1+radius, y2,
        x1+radius, y2,
        x1, y2,
        x1, y2-radius,
        x1, y2-radius,
        x1, y1+radius,
        x1, y1+radius,
        x1, y1
    ]
    return canvas.create_polygon(points, **kwargs, smooth=True)

class ModernButton(tk.Canvas):
    """Nút bấm hiện đại với hiệu ứng hover"""
    def __init__(self, parent, text, command, bg_color, fg_color='white', **kwargs):
        super().__init__(parent, height=50, highlightthickness=0, **kwargs)
        self.command = command
        self.bg_color = bg_color
        self.hover_color = COLORS['hover']
        self.fg_color = fg_color
        self.text = text
        
        self.configure(bg=parent['bg'])
        self.bind('<Button-1>', lambda e: self.command())
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
        
        self.draw_button(self.bg_color)
    
    def draw_button(self, color):
        self.delete('all')
        width = self.winfo_width() if self.winfo_width() > 1 else 200
        height = 50
        
        create_rounded_rectangle(self, 0, 0, width, height, radius=25, 
                                fill=color, outline='')
        self.create_text(width/2, height/2, text=self.text, 
                        fill=self.fg_color, font=('Segoe UI', 12, 'bold'))
    
    def on_enter(self, e):
        self.draw_button(self.hover_color)
        self.configure(cursor='hand2')
    
    def on_leave(self, e):
        self.draw_button(self.bg_color)
        self.configure(cursor='')

def browse_file():
    global original_image, processed_image, canny_edges, original_contours
    global blurred_image, ycrcb_image, original_image_with_contours, canny_with_contours
    
    filepath = filedialog.askopenfilename(
        filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")],
        title="Chọn ảnh lá cây"
    )
    if not filepath:
        return
    
    if not os.path.exists(filepath):
        show_status("File không tồn tại!", "error")
        return
    
    try:
        pil_image = Image.open(filepath)
        original_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        
        # Reset các biến
        processed_image = None
        canny_edges = None
        original_contours = None
        blurred_image = None
        ycrcb_image = None
        original_image_with_contours = None
        canny_with_contours = None
        
        load_image(filepath)
        show_status("Đã tải ảnh thành công", "success")
        
        # Hiện nút tiền xử lý
        preprocess_btn.grid(row=1, column=1, pady=10, padx=10, sticky="ew")
        detect_btn.grid_forget()
    
    except Exception as e:
        show_status(f"Lỗi khi tải ảnh: {e}", "error")

def load_image(filepath):
    img = Image.open(filepath)
    original_width, original_height = img.size
    display_width, display_height = 450, 450
    aspect_ratio = min(display_width / original_width, display_height / original_height)
    new_width = int(original_width * aspect_ratio)
    new_height = int(original_height * aspect_ratio)
    
    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    img_tk = ImageTk.PhotoImage(img)
    image_labels['original'].config(image=img_tk)
    image_labels['original'].image = img_tk

def preprocess_image():
    global original_image, processed_image, canny_edges, blurred_image, ycrcb_image
    
    if original_image is None:
        show_status("Vui lòng chọn ảnh trước", "warning")
        return
    
    show_status("Đang xử lý ảnh...", "info")
    root.update()
    
    # Làm mờ ảnh
    blurred = cv2.GaussianBlur(original_image, (3, 3), 0)
    blurred_image = blurred
    show_image_in_label(blurred, image_labels['blur'])
    
    # Chuyển đổi sang không gian màu YCrCb
    ycrcb_image_cv = cv2.cvtColor(blurred, cv2.COLOR_BGR2YCrCb)
    ycrcb_image = ycrcb_image_cv
    show_image_in_label(ycrcb_image_cv, image_labels['ycrcb'])
    
    # Tách kênh và sử dụng kênh Cr
    _, cr, _ = cv2.split(ycrcb_image_cv)
    
    # Ngưỡng Otsu
    _, mask_cv = cv2.threshold(cr, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Áp dụng mask
    result = cv2.bitwise_and(original_image, original_image, mask=mask_cv)
    processed_image = result
    show_image_in_label(result, image_labels['processed'])
    
    # Phát hiện biên Canny
    gray_processed = cv2.cvtColor(processed_image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray_processed, 75, 125)
    canny_edges = edges
    show_image_in_label(edges, image_labels['canny'], grayscale=True)
    
    show_status("Tiền xử lý hoàn tất", "success")
    
    # Hiện nút phát hiện bệnh
    preprocess_btn.grid_forget()
    detect_btn.grid(row=1, column=2, pady=10, padx=10, sticky="ew")

def show_image_in_label(img_cv, label, grayscale=False):
    if grayscale:
        img_pil = Image.fromarray(img_cv).convert("L")
    else:
        img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
    
    display_width, display_height = 450, 450
    original_width, original_height = img_pil.size
    aspect_ratio = min(display_width / original_width, display_height / original_height)
    new_width = int(original_width * aspect_ratio)
    new_height = int(original_height * aspect_ratio)
    
    img_pil = img_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
    img_tk = ImageTk.PhotoImage(img_pil)
    label.config(image=img_tk)
    label.image = img_tk

def detect_disease_regions():
    global processed_image, canny_edges, original_contours, canny_with_contours
    global original_image, original_image_with_contours
    
    if processed_image is None or canny_edges is None:
        show_status("Vui lòng tiền xử lý ảnh trước", "warning")
        return
    
    show_status("Đang phát hiện vùng bệnh...", "info")
    root.update()
    
    contours, _ = cv2.findContours(canny_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    original_contours = contours
    
    # Ước lượng diện tích lá (contour lớn nhất)
    if contours:
        leaf_area_contour = max(contours, key=cv2.contourArea)
        leaf_area = cv2.contourArea(leaf_area_contour)
    else:
        leaf_area = 0
        show_status("Không tìm thấy contour nào", "error")
        return
    
    output = processed_image.copy()
    disease_area = 0
    filtered_contours = []
    
    for contour in contours:
        area = cv2.contourArea(contour)
        
        # BỎ QUA contour lá chính (contour lớn nhất)
        if np.array_equal(contour, leaf_area_contour):
            continue
        
        perimeter = cv2.arcLength(contour, True)
        
        if perimeter > 0 and area > 0:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = float(w) / h if h > 0 else 0
            
            # Lọc các vùng bệnh: phải nhỏ hơn 80% diện tích lá và lớn hơn 0.5%
            if (0.005 * leaf_area) < area < (0.8 * leaf_area):
                hull = cv2.convexHull(contour)
                hull_area = cv2.contourArea(hull)
                solidity = float(area) / hull_area if hull_area > 0 else 0
                
                if solidity > 0.2:
                    if 0.2 <= aspect_ratio <= 6:
                        filtered_contours.append(contour)
                        disease_area += area
    
    # Vẽ contour lên ảnh gốc
    original_with_contours = original_image.copy()
    cv2.drawContours(original_with_contours, filtered_contours, -1, (255, 50, 50), 3)
    original_image_with_contours = original_with_contours
    
    # Vẽ contour lên ảnh Canny
    canny_with_contours = cv2.cvtColor(canny_edges, cv2.COLOR_GRAY2BGR)
    cv2.drawContours(canny_with_contours, filtered_contours, -1, (255, 50, 50), 3)
    
    show_image_in_label(canny_with_contours, image_labels['canny_contours'])
    show_image_in_label(original_with_contours, image_labels['original_contours'])
    
    # Hiển thị kết quả
    num_regions = len(filtered_contours)
    disease_percentage = (disease_area / leaf_area * 100) if leaf_area > 0 else 0
    
    result_text = f"Phát hiện: {num_regions} vùng bệnh"
 
    if disease_percentage < 10:
        status_color = "success"
        result_text += "\nLá khỏe mạnh"
    elif disease_percentage < 30:
        status_color = "warning"
        result_text += "\nNhiễm bệnh nhẹ"
    else:
        status_color = "error"
        result_text += "\nNhiễm bệnh nặng"
    
    show_status(result_text, status_color)

def show_status(message, status_type="info"):
    """Hiển thị trạng thái với màu sắc"""
    color_map = {
        "success": COLORS['success'],
        "error": "#F44336",
        "warning": COLORS['accent'],
        "info": COLORS['primary']
    }
    
    status_label.config(text=message, fg=color_map.get(status_type, COLORS['text_dark']))

def create_image_card(parent, title, row, col):
    """Tạo card hiển thị ảnh với thiết kế đẹp"""
    card = tk.Frame(parent, bg=COLORS['card'], relief='flat')
    card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
    
    # Thêm shadow effect bằng border
    shadow = tk.Frame(card, bg=COLORS['border'], relief='flat')
    shadow.place(relx=0.02, rely=0.02, relwidth=1, relheight=1)
    
    content = tk.Frame(card, bg=COLORS['card'], relief='flat')
    content.place(relx=0, rely=0, relwidth=1, relheight=1)
    
    # Tiêu đề
    title_label = tk.Label(
        content, 
        text=title, 
        bg=COLORS['card'], 
        fg=COLORS['text_dark'],
        font=('Segoe UI', 11, 'bold'),
        pady=10
    )
    title_label.pack(fill='x')
    
    # Khung ảnh
    img_frame = tk.Frame(
        content, 
        width=450, 
        height=450, 
        bg=COLORS['background'],
        relief='flat',
        highlightbackground=COLORS['border'],
        highlightthickness=1
    )
    img_frame.pack(padx=10, pady=(0, 10), expand=True, fill='both')
    img_frame.pack_propagate(False)
    
    img_label = tk.Label(img_frame, bg=COLORS['background'], text="")
    img_label.pack(expand=True)
    
    return img_label

# Tạo cửa sổ chính
root = tk.Tk()
root.title("Ứng dụng Phát hiện Bệnh Lá Cây")
root.state('zoomed')
root.configure(bg=COLORS['background'])

# Header
header_frame = tk.Frame(root, bg=COLORS['primary'], height=100)
header_frame.grid(row=0, column=0, columnspan=4, sticky="ew")
header_frame.grid_propagate(False)

title_label = tk.Label(
    header_frame,
    text="Ứng Dụng Phát Hiện Bệnh Lá Cây",
    font=('Segoe UI', 26, 'bold'),
    bg=COLORS['primary'],
    fg='white',
    pady=25
)
title_label.pack()

subtitle_label = tk.Label(
    header_frame,
    font=('Segoe UI', 11),
    bg=COLORS['primary'],
    fg='#E8F5E9'
)
subtitle_label.pack()

# Control panel
control_frame = tk.Frame(root, bg=COLORS['background'], pady=15)
control_frame.grid(row=1, column=0, columnspan=4, sticky="ew")

for i in range(4):
    control_frame.grid_columnconfigure(i, weight=1)

# Nút chọn ảnh
browse_btn = ModernButton(
    control_frame,
    "Chọn Ảnh",
    browse_file,
    COLORS['primary']
)
browse_btn.grid(row=1, column=0, pady=10, padx=10, sticky="ew")

# Nút tiền xử lý
preprocess_btn = ModernButton(
    control_frame,
    "Tiền Xử Lý",
    preprocess_image,
    COLORS['secondary']
)
preprocess_btn.grid_forget()

# Nút phát hiện bệnh
detect_btn = ModernButton(
    control_frame,
    "Phát Hiện Vùng Bệnh",
    detect_disease_regions,
    COLORS['accent']
)
detect_btn.grid_forget()

# Status bar
status_frame = tk.Frame(root, bg=COLORS['card'], height=80, relief='flat')
status_frame.grid(row=2, column=0, columnspan=4, sticky="ew", padx=20, pady=(10, 5))
status_frame.grid_propagate(False)

status_label = tk.Label(
    status_frame,
    text="Chào mừng! Vui lòng chọn ảnh để bắt đầu",
    font=('Segoe UI', 12),
    bg=COLORS['card'],
    fg=COLORS['text_light'],
    wraplength=800,
    justify='center'
)
status_label.pack(expand=True)

# Image display area
image_display_frame = tk.Frame(root, bg=COLORS['background'])
image_display_frame.grid(row=3, column=0, columnspan=4, sticky="nsew", padx=15, pady=15)

for i in range(4):
    root.grid_columnconfigure(i, weight=1)
    image_display_frame.grid_columnconfigure(i, weight=1)

for i in range(2):
    image_display_frame.grid_rowconfigure(i, weight=1)

root.grid_rowconfigure(3, weight=1)

# Tạo các card hiển thị ảnh
image_labels = {}
image_labels['original'] = create_image_card(image_display_frame, "Ảnh Gốc", 0, 0)
image_labels['blur'] = create_image_card(image_display_frame, "Ảnh Làm Mờ", 0, 1)
image_labels['ycrcb'] = create_image_card(image_display_frame, "Không Gian YCrCb", 0, 2)
image_labels['processed'] = create_image_card(image_display_frame, "Ảnh Đã Xử Lý", 0, 3)
image_labels['canny'] = create_image_card(image_display_frame, "Biên Canny", 1, 0)
image_labels['canny_contours'] = create_image_card(image_display_frame, "Canny + Contour", 1, 1)
image_labels['original_contours'] = create_image_card(image_display_frame, "Phát Hiện Bệnh", 1, 2)

# Footer
footer_frame = tk.Frame(root, bg=COLORS['primary'], height=40)
footer_frame.grid(row=4, column=0, columnspan=4, sticky="ew")
footer_frame.grid_propagate(False)

footer_label = tk.Label(
    footer_frame,
    font=('Segoe UI', 9),
    bg=COLORS['primary'],
    fg='white'
)
footer_label.pack(pady=10)

# Vòng lặp chính
root.mainloop()

