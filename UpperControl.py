import sys
import socket
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGroupBox, QSlider, QLabel, 
                             QPushButton, QLineEdit, QSpinBox, QGridLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QTimer

class ServoControlApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.socket = None
        self.SERVO_COUNT = 4  # 只控制4路舵机
        # 添加通道映射：界面通道 -> 实际硬件通道
        self.channel_mapping = {0: 0, 1: 1, 2: 2, 3: 3}  # 通道3映射到硬件通道4
        # 添加动作预设角度
        self.action_presets = {
            '趴下': [0, 180, 180, 0],  # 通道0-3的预设角度
            '站立': [90, 90, 90, 90],
            '挥手': [45, 135, 45, 135],
            '前进步骤1': [60, 120, 60, 120],  # 第一步
            '前进步骤2': [120, 60, 120, 60],  # 第二步
            '前进步骤3': [90, 90, 90, 90]     # 回归中立位置
        }
        self.forward_sequence = ['前进步骤1', '前进步骤2', '前进步骤3']
        self.current_step = 0
        self.forward_timer = None  # 用于控制动作时序的定时器
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

        # 新增动作控制组
        self.setup_action_group()
        layout.addWidget(self.action_group)

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
        
        self.ip_input = QLineEdit('192.168.1.24')
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
        # 通过映射获取实际的硬件通道
        hardware_channel = self.channel_mapping[channel]
        value = self.servo_spinboxes[channel].value()
        
        if self.send_command(f"{hardware_channel},{value}"):
            self.status_label.setText(f'通道{channel} 设置为 {value}°')
            
    def set_all_servos(self):
        # 构建映射后的命令
        angles_dict = {}
        for ui_channel in range(self.SERVO_COUNT):
            hardware_channel = self.channel_mapping[ui_channel]
            value = self.global_spinboxes[ui_channel].value()
            
            actual_value = value
                
            angles_dict[hardware_channel] = str(actual_value)
        
        # 按照硬件通道顺序构建命令字符串
        command = "ALL," + ",".join([angles_dict.get(i, "0") for i in range(5)])
        
        if self.send_command(command):
            angle_text = ", ".join([f"界面通道{i}→硬件通道{self.channel_mapping[i]}:{angles_dict[self.channel_mapping[i]]}°" 
                                    for i in range(self.SERVO_COUNT)])
            self.status_label.setText(f'设置完成: {angle_text}')
            
    def send_reset(self):
        if self.forward_timer and self.forward_timer.isActive():
            self.forward_timer.stop()
            self.forward_timer = None
            
        if self.send_command("RESET"):
            self.status_label.setText('系统复位完成')
            # 重置界面显示和前进状态
            for i in range(self.SERVO_COUNT):
                self.servo_spinboxes[i].setValue(90)
                self.global_spinboxes[i].setValue(90)
            self.current_step = 0
            # 确保重置后显示状态页
            self.show_status_page()

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

    def setup_action_group(self):
        self.action_group = QGroupBox('动作控制')
        grid = QGridLayout()
        
        # 创建动作按钮
        actions = ['趴下', '站立', '挥手', '前进', '停止前进']  # 添加前进和停止前进按钮
        self.action_buttons = []
        
        for i, action_name in enumerate(actions):
            button = QPushButton(action_name)
            if action_name == '前进':
                button.clicked.connect(self.start_forward_sequence)
            elif action_name == '停止前进':
                button.clicked.connect(self.stop_forward_sequence)
            else:
                button.clicked.connect(lambda checked, a=action_name: self.send_action(a))
            grid.addWidget(button, i // 2, i % 2)
            self.action_buttons.append(button)
        
        self.action_group.setLayout(grid)

    def start_forward_sequence(self):
        """开始前进动作序列"""
        if not self.socket:
            self.status_label.setText('未连接，无法执行前进动作')
            return

        # 设置表情为SMILEY
        self.send_expression_command('SMILEY')

        self.current_step = 0
        # 创建定时器控制动作时序
        self.forward_timer = QTimer()
        self.forward_timer.timeout.connect(self.execute_next_forward_step)
        self.forward_timer.start(500)  # 每500毫秒执行一步
        self.status_label.setText('开始前进动作序列...')

    def stop_forward_sequence(self):
        """停止前进动作序列"""
        if self.forward_timer and self.forward_timer.isActive():
            self.forward_timer.stop()
            self.forward_timer = None
            # 回归站立姿势
            self.send_action('站立')
            # 恢复显示舵机状态
            self.show_status_page()
            self.status_label.setText('前进动作已停止')

    def execute_next_forward_step(self):
        """执行前进序列的下一步"""
        if self.current_step >= len(self.forward_sequence):
            # 序列完成，回归第一步实现循环
            self.current_step = 0
            
        step_name = self.forward_sequence[self.current_step]
        if step_name in self.action_presets:
            # 发送当前步骤的角度
            angles = self.action_presets[step_name]
            
            # 构建映射后的命令
            angles_dict = {}
            for ui_channel in range(self.SERVO_COUNT):
                hardware_channel = self.channel_mapping[ui_channel]
                value = angles[ui_channel]
                angles_dict[hardware_channel] = str(value)
            
            command = "ALL," + ",".join([angles_dict.get(i, "0") for i in range(5)])
            
            if self.send_command(command):
                # 更新界面显示
                for i in range(self.SERVO_COUNT):
                    self.servo_spinboxes[i].setValue(angles[i])
                    self.global_spinboxes[i].setValue(angles[i])
                
                self.status_label.setText(f'前进步骤 {self.current_step + 1}/{len(self.forward_sequence)}')
                self.current_step += 1
        else:
            self.stop_forward_sequence()
            self.status_label.setText(f'未找到步骤: {step_name}')
            
    # 通用的动作发送方法
    def send_action(self, action_name):
        """发送指定动作命令"""
        if action_name not in self.action_presets:
            self.status_label.setText(f'未找到动作: {action_name}')
            return
            
        # 获取预设的角度值
        angles = self.action_presets[action_name]
        
        # 构建映射后的命令
        angles_dict = {}
        for ui_channel in range(self.SERVO_COUNT):
            hardware_channel = self.channel_mapping[ui_channel]
            value = angles[ui_channel]
            
            # 移除正负映射逻辑，直接使用原始值
            actual_value = value
                
            angles_dict[hardware_channel] = str(actual_value)
        
        # 按照硬件通道顺序构建命令字符串
        command = "ALL," + ",".join([angles_dict.get(i, "0") for i in range(5)])
        
        if self.send_command(command):
            # 更新界面显示
            for i in range(self.SERVO_COUNT):
                self.servo_spinboxes[i].setValue(angles[i])
                self.global_spinboxes[i].setValue(angles[i])
            
            angle_text = ", ".join([f"通道{i}:{angles_dict[self.channel_mapping[i]]}°" 
                                    for i in range(self.SERVO_COUNT)])
            self.status_label.setText(f'{action_name}动作完成: {angle_text}')
            
    def closeEvent(self, event):
        """重写关闭事件，确保定时器被正确清理"""
        if self.forward_timer and self.forward_timer.isActive():
            self.forward_timer.stop()
        if self.socket:
            self.socket.close()
        event.accept()
        
def main():
    app = QApplication(sys.argv)
    window = ServoControlApp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()