import sys
import socket
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGroupBox, QSlider, QLabel, 
                             QPushButton, QLineEdit, QSpinBox, QGridLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class ServoControlApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.socket = None
        self.SERVO_COUNT = 4  # 只控制4路舵机
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('LU9685 舵机控制器 (4路)')
        self.setGeometry(100, 100, 600, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 连接设置
        self.setup_connection_group()
        layout.addWidget(self.connection_group)
        
        # 单路控制
        self.setup_single_control_group()
        layout.addWidget(self.single_control_group)
        
        # 全局控制
        self.setup_global_control_group()
        layout.addWidget(self.global_control_group)

        # 新增表情控制组
        self.setup_expression_group()
        layout.addWidget(self.expression_group)

        # 新增显示模式控制组
        self.setup_display_mode_group()
        layout.addWidget(self.display_mode_group)

        # 状态显示
        self.status_label = QLabel('未连接')
        layout.addWidget(self.status_label)
        
    def setup_connection_group(self):
        self.connection_group = QGroupBox('连接设置')
        layout = QHBoxLayout()
        
        self.ip_input = QLineEdit('192.168.1.3')
        self.port_input = QLineEdit('8080')
        self.connect_btn = QPushButton('连接')
        self.disconnect_btn = QPushButton('断开')
        
        layout.addWidget(QLabel('IP:'))
        layout.addWidget(self.ip_input)
        layout.addWidget(QLabel('端口:'))
        layout.addWidget(self.port_input)
        layout.addWidget(self.connect_btn)
        layout.addWidget(self.disconnect_btn)
        
        self.connection_group.setLayout(layout)
        
        self.connect_btn.clicked.connect(self.connect_to_esp32)
        self.disconnect_btn.clicked.connect(self.disconnect)
        
    def setup_single_control_group(self):
        self.single_control_group = QGroupBox('单路舵机控制')
        grid = QGridLayout()
        
        self.servo_sliders = []
        self.servo_labels = []
        self.servo_spinboxes = []
        self.servo_buttons = []
        
        for i in range(self.SERVO_COUNT):
            # 通道标签
            label = QLabel(f'通道 {i}:')
            grid.addWidget(label, i, 0)
            
            # 滑动条
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 180)
            slider.setValue(90)
            grid.addWidget(slider, i, 1)
            
            # 角度显示
            spinbox = QSpinBox()
            spinbox.setRange(0, 180)
            spinbox.setValue(90)
            grid.addWidget(spinbox, i, 2)
            
            # 确定按钮
            button = QPushButton('确定')
            grid.addWidget(button, i, 3)
            
            # 连接信号
            slider.valueChanged.connect(spinbox.setValue)
            spinbox.valueChanged.connect(slider.setValue)
            button.clicked.connect(lambda checked, ch=i: self.send_single_command(ch))
            
            self.servo_sliders.append(slider)
            self.servo_spinboxes.append(spinbox)
            self.servo_buttons.append(button)
            
        self.single_control_group.setLayout(grid)
        
    def setup_global_control_group(self):
        self.global_control_group = QGroupBox('全局控制 (4路独立设置)')
        main_layout = QVBoxLayout()
        
        # 创建4个独立的控制行
        grid = QGridLayout()
        self.global_spinboxes = []
        
        for i in range(self.SERVO_COUNT):
            label = QLabel(f'通道 {i} 角度:')
            grid.addWidget(label, i, 0)
            
            spinbox = QSpinBox()
            spinbox.setRange(0, 180)
            spinbox.setValue(90)
            grid.addWidget(spinbox, i, 1)
            
            self.global_spinboxes.append(spinbox)
        
        main_layout.addLayout(grid)
        
        # 按钮行
        button_layout = QHBoxLayout()
        self.set_all_btn = QPushButton('设置所有舵机')
        self.reset_btn = QPushButton('软复位')
        
        button_layout.addWidget(self.set_all_btn)
        button_layout.addWidget(self.reset_btn)
        
        main_layout.addLayout(button_layout)
        self.global_control_group.setLayout(main_layout)
        
        self.set_all_btn.clicked.connect(self.set_all_servos)
        self.reset_btn.clicked.connect(self.send_reset)
        
    def connect_to_esp32(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.ip_input.text(), int(self.port_input.text())))
            self.socket.settimeout(2.0)
            self.status_label.setText('连接成功')
        except Exception as e:
            self.status_label.setText(f'连接失败: {str(e)}')
            
    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.socket = None
        self.status_label.setText('已断开')
        
    def send_command(self, command):
        if not self.socket:
            self.status_label.setText('未连接')
            return False
            
        try:
            self.socket.sendall((command + '\n').encode())
            response = self.socket.recv(1024).decode().strip()
            return response == 'OK'
        except Exception as e:
            self.status_label.setText(f'发送失败: {str(e)}')
            return False
            
    def send_single_command(self, channel):
        value = self.servo_spinboxes[channel].value()
        if self.send_command(f"{channel},{value}"):
            self.status_label.setText(f'通道 {channel} 设置为 {value}°')
            
    def set_all_servos(self):
        angles = [str(spinbox.value()) for spinbox in self.global_spinboxes]
        command = "ALL," + ",".join(angles)
        if self.send_command(command):
            angle_text = ", ".join([f"通道{i}:{angles[i]}°" for i in range(self.SERVO_COUNT)])
            self.status_label.setText(f'设置完成: {angle_text}')
            
    def send_reset(self):
        if self.send_command("RESET"):
            self.status_label.setText('系统复位完成')
            # 重置界面显示
            for i in range(self.SERVO_COUNT):
                self.servo_spinboxes[i].setValue(90)
                self.global_spinboxes[i].setValue(90)

    def setup_expression_group(self):
        self.expression_group = QGroupBox('表情显示控制')
        grid = QGridLayout()

        # 定义可用表情
        expressions = ['SMILEY', 'CRYING', 'SLEEPY'] # 与ESP32端定义一致

        # 创建表情按钮
        self.expression_buttons = []
        for i, expr in enumerate(expressions):
            button = QPushButton(expr)
            button.clicked.connect(lambda checked, e=expr: self.send_expression_command(e))
            grid.addWidget(button, i // 3, i % 3) # 每行3个按钮
            self.expression_buttons.append(button)

        # 添加返回状态页按钮
        self.status_page_btn = QPushButton('显示舵机状态')
        self.status_page_btn.clicked.connect(self.show_status_page)
        grid.addWidget(self.status_page_btn, (len(expressions) // 3) + 1, 0, 1, 3) # 跨列

        self.expression_group.setLayout(grid)

    def send_expression_command(self, expression_type):
        command = f"EXPRESSION,{expression_type}"
        if self.send_command(command):
            self.status_label.setText(f'显示表情: {expression_type}')

    def show_status_page(self):
        # 发送RESET命令会触发ESP32显示默认状态页
        if self.send_command("RESET"):
            self.status_label.setText('返回舵机状态显示')

    def setup_display_mode_group(self):
        self.display_mode_group = QGroupBox('显示模式控制')
        layout = QHBoxLayout()
        
        # 创建模式切换按钮
        self.clock_btn = QPushButton('时钟模式')
        self.weather_btn = QPushButton('天气模式')
        self.status_btn = QPushButton('状态模式')
        
        layout.addWidget(self.clock_btn)
        layout.addWidget(self.weather_btn)
        layout.addWidget(self.status_btn)
        
        self.display_mode_group.setLayout(layout)
        
        # 连接按钮信号
        self.clock_btn.clicked.connect(lambda: self.send_display_mode("CLOCK"))
        self.weather_btn.clicked.connect(lambda: self.send_display_mode("WEATHER"))
        self.status_btn.clicked.connect(lambda: self.send_display_mode("STATUS"))

    def send_display_mode(self, mode):
        command = f"MODE_{mode}"
        if self.send_command(command):
            self.status_label.setText(f'切换到{mode}模式')

def main():
    app = QApplication(sys.argv)
    window = ServoControlApp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()