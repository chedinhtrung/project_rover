import sys
import os
path = os.path.abspath(__file__)
sys.path.append(os.path.dirname(os.path.dirname(path)))
import time
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QPen
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import (QLabel, QTextEdit, QProgressBar, \
                             QApplication, QHBoxLayout, QVBoxLayout, 
                             QWidget, QSizePolicy, QGridLayout, QPushButton, 
                             QMenuBar, QDialog, QAction, QSpacerItem, QRadioButton,
                             QDoubleSpinBox, QSpinBox, QComboBox, QLineEdit,
                             QTabWidget, QTabBar, QMenu)
from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from CoreTcp import MissionControlCore
from Network.config import *
import sys
from Command import Command
from Tools.network.NetworkGrapher import NetworkGraphTab
from Tools.qterminal.widget import QTerminalTab
from confidential import *

class VideoDisplay(QLabel):

    def __init__(self, video_source=None):   
        QLabel.__init__(self)
        self.video_source = video_source
        self.frame = "ROVER NOT CONNECTED"
        self.setText(self.frame)
        #self.resize(640, 480)
        self.setStyleSheet("border:2px solid #2A2A2A; background-color:#181818;")
        self.setAlignment(Qt.AlignCenter)
        if self.video_source is not None:
            self.video_source.frame_signal.connect(self.update_frame)
    
    def update_frame(self, image):
        #TODO: adjust frame to current screen size
        scaled_img = image.scaled(
            int(self.width()*0.999), int(self.height()*0.99), Qt.KeepAspectRatio)
        self.setPixmap(QPixmap.fromImage(scaled_img))
    
    def set_videosource(self, videosource):
        self.video_source = videosource
        self.video_source.frame_signal.connect(self.update_frame)

class Line(QWidget):
    def __init__(self, start_pos, end_pos):
        super().__init__()
        self.start_pos = start_pos
        self.end_pos = end_pos

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Set pen for drawing the line
        pen = QPen(Qt.black, 2, Qt.SolidLine)
        painter.setPen(pen)
        
        # Draw line using start and end positions
        painter.drawLine(self.start_pos[0], self.start_pos[1], self.end_pos[0], self.end_pos[1])

class Ruler(QWidget):
    def __init__(self, picture):
        super().__init__()
    
    def paintEvent(self, event):
        pass

class MapDisplay(QWebEngineView):
    def __init__(self):
        QWebEngineView.__init__(self)
        local_path = os.path.dirname(os.path.abspath(__file__))
        relative_path = 'googlemaps2.html'
        map_path = os.path.join(local_path, relative_path)
        #self.load(QUrl.fromLocalFile(map_path))
        html = self.load_html_with_api_key(map_path, GGMAP_API_KEY)
        self.setHtml(html, QUrl.fromLocalFile(map_path))            # Needs map_path as base URL to resolve resource locations
        self.last_update = time.time()

    def updateDroneLocation(self, data):
        if not data["Online"]:
            return
        time_elapsed = time.time() - self.last_update
        if not (data["Lon"] == 0 and data["Lat"] == 0) and time_elapsed > 1: #Check for null glitch
            self.last_update = time.time()
            script = f"update_location({data['Lon']}, {data['Lat']});"
            # Update the marker on the map to reflect the new drone location
            self.page().runJavaScript(script) 
    
    def set_mapupdater(self, mapupdater):
        self.updater = mapupdater
        mapupdater.signal_telemetry.connect(self.updateDroneLocation)

    def load_html_with_api_key(self, file_path, api_key):
        with open(file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        html_content = html_content.replace("API_KEY_PLACEHOLDER", api_key)
        #print(html_content)
        return html_content

class ServerLogDisplay(QTextEdit):
    def __init__(self):
        QTextEdit.__init__(self)
        self.setReadOnly(True)
        self.setStyleSheet("border:2px solid #2A2A2A; background-color:#181818; padding:10px; color: #CCCCBB;")
        self.log("Initializing...")

    def log(self, message):
        self.append(f"{time.strftime('%H:%M:%S', time.localtime())} {message}")


    def update(self, data):
        if not data is None:
            self.text.setText(str(data))
            self.text.adjustSize()

class ClickableWidget(QWidget):
    # Define a custom clicked signal
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        # Emit the clicked signal when the widget is clicked
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

class ControlThrottleDisplay(QVBoxLayout):
    def __init__(self):
        QVBoxLayout.__init__(self)
        self.label = QLabel()
        self.label.setStyleSheet("font-size: 30px")
        self.label.setText("NO JOYSTICK FOUND")
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.addWidget(self.label, 1)
        self.throttleL = QProgressBar()
        self.throttleL.setValue(50)
        self.throttleR = QProgressBar()
        self.throttleR.setValue(50)
        self.throttleL.setOrientation(Qt.Vertical)
        self.throttleR.setOrientation(Qt.Vertical)
        self.throttleL.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.throttleR.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.throttleL.setStyleSheet("QProgressBar::chunk {background-color: #22A4F1;} QProgressBar{color: transparent; background-color:#292B2D}")
        self.throttleR.setStyleSheet("QProgressBar::chunk {background-color: #22A4F1;} QProgressBar{color: transparent; background-color: #292B2D}")

        row2 = QHBoxLayout()
        row2.addWidget(self.throttleL, 1)
        row2.addWidget(self.throttleR, 1)
        
        self.addLayout(row2, 7)
    
    def update_status(self, status):
        self.label.setText(str(status))
    
    def update_throttle(self, throttle):
        if throttle[0] == "M":
            self.throttleL.setValue(int(50 - throttle[1]*50))
            self.throttleR.setValue(int(50 - throttle[2]*50))
    
    def set_controlsource(self, control_source:Command):
        self.control_source = control_source
        self.control_source.command_sig.connect(self.update_throttle)
        self.control_source.status_sig.connect(self.update_status)

class RoverStatusDisplay(QGridLayout):
    signal_cammode = pyqtSignal(str)
    def __init__(self, parent = None):
        self.parent = parent
        QGridLayout.__init__(self)
        #self.setSpacing(10)
        self.voltage = RoverParameter("Voltage")
        self.voltage.label.clicked.connect(self.show_power_graph)
        self.current = RoverParameter("Current")
        self.current.label.clicked.connect(self.show_power_graph)
        self.gps = RoverParameter("GPS")
        self.camera = RoverParameter("Camera")
        self.camera.mode = "Normal"
        self.camera.state = "--"
        self.camera.label.clicked.connect(self.switch_camera_mode)
        self.control = RoverParameter("Control")
        self.status = RoverParameter("Status")
        self.addWidget(self.voltage, 0, 0)
        self.addWidget(self.current, 0, 1)
        self.addWidget(self.gps, 0, 2)
        self.addWidget(self.camera, 1, 0)
        self.addWidget(self.control, 1, 1)
        self.addWidget(self.status, 1, 2)
    
    def update(self, telemetry_data):
        try: 
            if not telemetry_data["Online"]:
                self.status.update("Offline")
                self.status.value.setStyleSheet("font-size: 40px; font-weight:bold; background-color:red;")
                return
            
            #print(telemetry_data)
            
            self.status.update("Online")
            self.status.value.setStyleSheet("font-size: 40px; font-weight:bold; background-color:green;")
            self.voltage.update(str(telemetry_data["Vol"]) + " V")
            self.voltage.value.setStyleSheet("font-size: 40px; font-weight:bold;")
            if telemetry_data["Vol"] < 7.4: 
                self.voltage.value.setStyleSheet("font-size: 40px; font-weight:bold; background-color:orange;")
            elif telemetry_data["Vol"] < 6.4: 
                self.voltage.value.setStyleSheet("font-size: 40px; font-weight:bold; background-color:red;")
            else:
                self.voltage.value.setStyleSheet("font-size: 40px; font-weight:bold; background-color:green;")

            self.current.update(str(telemetry_data["Cur"]) + " mA") 
            if telemetry_data["GPS"]:
                self.gps.update("Waiting...")
            if not (telemetry_data["Lon"] == 0 and telemetry_data["Lat"] == 0):
                self.gps.update("Receiving")
            if telemetry_data["Ctl"]:
                self.control.update("OK")
                self.control.value.setStyleSheet("font-size: 40px; font-weight:bold; background-color:green;")
            else:
                self.control.update("Offline")
                self.control.value.setStyleSheet("font-size: 40px; font-weight:bold; background-color:red;")
            if telemetry_data["Cam"] == "Normal":
                self.camera.update("Normal")
                self.camera.mode = "Normal"
                self.camera.value.setStyleSheet("font-size: 40px; font-weight:bold; background-color:green;")
            elif telemetry_data["Cam"] == "Data saving":
                self.camera.update("Data saving")
                self.camera.mode = "Data saving"
                self.camera.value.setStyleSheet("font-size: 40px; font-weight:bold; background-color:orange;")
            elif telemetry_data["Cam"] == "Offline":
                self.camera.update("Offline")
                self.camera.value.setStyleSheet("font-size: 40px; font-weight:bold; background-color:red;")
        except:
            pass

    def set_updater(self, updater):
        updater.signal_telemetry.connect(self.update)

    def show_power_graph(self):
        print("To be implemented: power graph")
    
    def switch_camera_mode(self):
        if self.camera.mode == "Normal":
            self.signal_cammode.emit("Data saving")
        
        elif self.camera.mode == "Data saving":
            self.signal_cammode.emit("Normal")


class RoverParameter(QWidget):
    def __init__(self, label, init_value="--"):
        super().__init__()
        layout = QVBoxLayout()
        layout.setSpacing(0)
        self.label = QPushButton(label)
        self.label.setStyleSheet("QPushButton {background-color:#181818; padding:10px; font-size: 30px} QPushButton:hover {background-color: #595958;}")
        self.label.setSizePolicy( QSizePolicy.Expanding,  QSizePolicy.Expanding)
        #self.label.setAlignment(Qt.AlignCenter)
        #self.label.setStyleSheet("font-size: 30px")
        self.value = QLabel(init_value)
        self.value.setAlignment(Qt.AlignCenter)
        self.value.setStyleSheet("font-size: 40px; font-weight:bold;")
        layout.addWidget(self.label, 1)
        layout.addWidget(self.value, 1)
        self.setLayout(layout)
        self.setStyleSheet("background-color: #181818")
    
    def update(self, value):
        self.value.setText(str(value))

class RoverConfigDialog(QDialog):
    def __init__(self, configurator):
        super().__init__()
        self.configurator = configurator

        self.setWindowTitle("Rover configuration")
        layout = QVBoxLayout()

        row1 = QGridLayout()
        row1.setSpacing(10)
        self.sleep_enabled = QRadioButton()
        row1.addWidget(QLabel("Go to sleep"), 0, 0)
        row1.addWidget(self.sleep_enabled, 0, 1)
        row1.addWidget(QLabel("After"), 0, 2)
        self.sleep_after_duration = QDoubleSpinBox()
        row1.addWidget(self.sleep_after_duration, 0, 3)

        row1.addWidget(QLabel("Main camera: "), 1, 0)
        row1.addWidget(QLabel("Resolution"), 2, 1)
        self.resolutions = QComboBox()
        self.resolutions.addItem("640x480")
        self.resolutions.addItem("1080x720")
        row1.addWidget(self.resolutions, 2, 2)
        row1.addWidget(QLabel("Framerate"), 3, 1)
        self.framerate = QSpinBox()
        row1.addWidget(self.framerate, 3, 2)
        self.picture_qual = QSpinBox()
        row1.addWidget(QLabel("Image quality"), 4, 1)
        row1.addWidget(self.picture_qual, 4, 2)

        row1.addWidget(QLabel("Hosts:"), 5, 0)
        row1.addWidget(QLabel("Video"), 6, 1)
        self.videohost = QLineEdit()
        row1.addWidget(self.videohost, 6,2)
        self.videoport = QLineEdit()
        row1.addWidget(self.videoport, 6,3)
        row1.addWidget(QLabel("Telemetry"), 7, 1)
        self.telemetryhost = QLineEdit()
        row1.addWidget(self.telemetryhost, 7,2)
        self.telemetryport = QLineEdit()
        row1.addWidget(self.telemetryport, 7,3)

        layout.addLayout(row1)

        bottom_row = QHBoxLayout()
        bottom_row.addItem(QSpacerItem(20, 40, QSizePolicy.Expanding, QSizePolicy.Minimum))
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        ok_button.setFixedWidth(100)
        bottom_row.addWidget(ok_button)
        bottom_row.addItem(QSpacerItem(20, 40, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(bottom_row)

        self.setLayout(layout)   
        self.action = QAction(self)
    
    def accept(self) -> None:
        
        return super().accept()

class ToolsMenu(QMenu):
    def __init__(self, title, parent):
        super().__init__(title, parent)
        self.setTitle(title)
        self.parent = parent
        menu_style = """
            QMenu {
                background-color: #1F1F1F;
                color: #CCCCBB;
            }
            QMenu::item {
                background-color: 1F1F1F;
            }
            QMenu::item:selected {
                background-color: #37373D;
            }
        """
        network_view = QAction("Network monitor", self)
        self.setStyleSheet(menu_style)
        network_view.triggered.connect(self.show_network_monitor) #TODO: add network view
        self.addAction(network_view)
        recorder = QAction("Recorder", self)
        self.addAction(recorder)
        ssh = QAction("SSH", self)
        ssh.triggered.connect(self.show_ssh_commandline)
        self.addAction(ssh)
    
    def show_network_monitor(self):
        self.parent.tabbar.addTab(NetworkGraphTab(), "Network")

    def show_ssh_commandline(self):
        terminal = QTerminalTab()
        self.parent.tabbar.addTab(terminal, "SSH")   

class MenuBar(QMenuBar):
    configurator = None
    def __init__(self, parent):
        QMenuBar.__init__(self)
        self.parent = parent
        self.tools = self.addMenu(ToolsMenu("Tools", self.parent))
        self.config = self.addMenu("Config")
        self.view = self.addMenu("View")
        self.setFixedHeight(60)
        self.setStyleSheet("""
            QMenuBar {
                background-color: #181818;
                color: #CCCCBB;
                padding-left: 20px;
                padding-top: 10px;
            }
            QMenuBar::item:selected {
                background-color: #37373D;
                color: #CCCCBB;
            }
            QMenuBar::item:pressed {
                background-color: #37373D;
                color: #CCCCBB;
            }
        """)
        menu_style = """
            QMenu {
                background-color: #1F1F1F;
                color: #CCCCBB;
            }
            QMenu::item {
                background-color: 1F1F1F;
            }
            QMenu::item:selected {
                background-color: #37373D;
            }
        """
        self.config.setStyleSheet(menu_style)
        config = QAction("Rover", self)
        config.triggered.connect(self.show_config)
        # Add the action to the Help menu
        self.config.addAction(config)

    def show_config(self):
        dialog = RoverConfigDialog(self.configurator)
        dialog.exec_()

class TopBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(MenuBar(self.parent), 1)
        minimize = QPushButton()
        minimize.setFixedSize(90,60)
        minimize.setText("__")
        minimize.setStyleSheet("QPushButton:hover {background-color: #595958;} QPushButton{font-weight:bold}")
        minimize.clicked.connect(self.parent.minimizeWindow)
        layout.addWidget(minimize)
        close_button = QPushButton()
        close_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "close.png")))
        close_button.setStyleSheet("QPushButton {background-color:darkred; padding:10px} QPushButton:hover {background-color: red;}")
        icon_size = close_button.iconSize()
        icon_size.setWidth(18)  # Set the desired width
        icon_size.setHeight(18)  # Set the desired height
        close_button.setIconSize(icon_size)
        close_button.clicked.connect(self.parent.close)
        layout.addWidget(close_button, 1)
        close_button.setFixedSize(90,60)
        self.setLayout(layout)

class MainTab(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.setStyleSheet("background-color: #1F1F1F;")
        rootlayout = QHBoxLayout()
        rootlayout.setSpacing(30)
        rootlayout.setContentsMargins(20, 10, 20, 10)
        col1 = QVBoxLayout()
        col1.setSpacing(30)
        self.videodisplay = VideoDisplay()
        col1.addWidget(self.videodisplay, 5)
        self.throttledisplay = ControlThrottleDisplay()
        self.roverstatusdisplay = RoverStatusDisplay(parent=self.parent)
        col1row1 = QHBoxLayout()
        col1row1.addLayout(self.throttledisplay, 1)
        col1row1.addLayout(self.roverstatusdisplay, 4)
        
        #col1row1.addLayout(self.throttledisplay, 1)
        col1.addLayout(col1row1, 3)

        col2 = QVBoxLayout()
        col2.setSpacing(30)
        self.mapdisplay = MapDisplay()
        col2.addWidget(self.mapdisplay, 5)
        self.serverlog = ServerLogDisplay()
        col2.addWidget(self.serverlog, 3)

        rootlayout.addLayout(col1, 4)
        rootlayout.addLayout(col2, 3)
        self.setLayout(rootlayout)

class Tabbar(QTabWidget):
    def __init__(self):
        super().__init__()
        self.tabCloseRequested.connect(self.on_tab_close)
    
    def on_tab_close(self, index):
        widget = self.widget(index)
        widget.close()
    
    def addTab(self, widget:QWidget, title:str):
        super().addTab(widget, title)
        self.setCurrentIndex(self.count()-1)
        widget.index = self.count()-1
        widget.tabber = self

class Window(QWidget):
    def __init__(self):
        super().__init__()
        # Create a QHBoxLayout instance
        self.init_UI()
        self.init_logic()
        self.setWindowFlags(self.windowFlags() | 
                            Qt.FramelessWindowHint)
    
    def init_UI(self):

        window = QVBoxLayout()
        window.setSpacing(0)
        window.setContentsMargins(0, 0, 0, 0)
        
        window.addWidget(TopBar(self))

        self.setStyleSheet("background-color: #1F1F1F; margin:0px; padding:0px;")
        
    
        self.tabbar = Tabbar()
        self.tabbar.setTabsClosable(True)
        self.maintab = MainTab(parent=self)
        self.tabbar.addTab(self.maintab, "Mission Control")
        self.tabbar.tabBar().setTabButton(0, QTabBar.RightSide, None)
        self.tabbar.tabCloseRequested.connect(self.close_tab)
        window.addWidget(self.tabbar)
        #window.addLayout(rootlayout)
        self.setLayout(window)
    
    def init_logic(self):  
        self.core = MissionControlCore(ui=self.maintab)
        self.core.start()
    
    def closeEvent(self, event):
        self.core.stop()
        for i in range(self.tabbar.count()):
            widget = self.tabbar.widget(i)
            widget.close()
        event.accept()
    
    def minimizeWindow(self):
        self.setWindowState(Qt.WindowMinimized)

    def showEvent(self, event):
        self.setWindowState(Qt.WindowMaximized)
        super().showEvent(event)
    
    def close_tab(self, index):
        self.tabbar.removeTab(index)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet("QLabel { color : #CCCCBB; font-size:30px; } QPushButton { color : #CCCCBB; } \
                      QTextEdit{color : #CCCCBB;} QDialog {background-color: #37373D;} \
                      QTabWidget::pane { background-color: #1F1F1F; } QTabBar { font-size: 25px; } \
                      QTabBar::tab:selected { color: #CCCCBB; background-color: #1F1F1F; border-top: 3px solid #22A4F1; padding: 10px 10px 10px 20px;} \
                      QTabBar::tab { color: #CCCCBB; background-color: #181818; padding: 10px 10px 10px 20px;} \
                      QLineEdit {color: #CCCCBB; padding: 10px; font-size: 30px}")
    window = Window()
    window.showMaximized()
    sys.exit(app.exec_())