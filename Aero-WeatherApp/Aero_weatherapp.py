import sys
import requests
import json
import os
from functools import partial
from PySide6.QtWidgets import (QApplication, QWidget, QLineEdit, QLabel, 
                               QPushButton, QVBoxLayout, QHBoxLayout, 
                               QMessageBox, QFrame, QScrollArea)
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPixmap, QResizeEvent, QIcon

class WeatherApp(QWidget):
    """
    Main application window for the Weather App.
    Handles UI creation, API calls, dynamic styling, and config persistence.
    """
    
    BASE_URL = "https://api.openweathermap.org/data/2.5/weather" 
    FAVORITES_PANEL_WIDTH = 280
    CONFIG_FILE = "weather_app_config.json"

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Aero-WeatherApp")
        basedir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(basedir, "aero_icon.png")
        self.setWindowIcon(QIcon(icon_path))
        self.resize(850, 550)
        self.setObjectName("WeatherWindow")

        # --- Data ---
        self.api_key = "" 
        self.favorites = {}
        self.favorite_widgets = {}
        self.current_city_data = None 

        # --- UI ---
        self.create_main_panel()
        self.create_favorites_panel()
        
        # --- Style & Config ---
        self.apply_global_styles()
        self.default_window_style = self.styleSheet()
        self.load_config()

    def resizeEvent(self, event: QResizeEvent):
        """Manually reposition panels on window resize."""
        super().resizeEvent(event)
        
        # Main panel always fills the window
        self.main_panel.setGeometry(self.rect())
        
        # Favorites panel "floats" on the left with 10px margins
        self.favorites_panel_widget.setGeometry(
            10, 
            10, 
            self.FAVORITES_PANEL_WIDTH, 
            self.height() - 20 
        )

    def create_favorites_panel(self):
        """Creates the floating panel on the left (Favorites + API Settings)."""
        
        # 1. Main Floating Container
        self.favorites_panel_widget = QFrame(self)
        self.favorites_panel_widget.setObjectName("FavoritesFrame")
        self.favorites_panel_layout = QVBoxLayout(self.favorites_panel_widget)
        self.favorites_panel_layout.setContentsMargins(0,0,0,0)
        self.favorites_panel_layout.setSpacing(0)

        # 2. Favorites List Area (Scrollable)
        title = QLabel("⭐ Favorites")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.favorites_panel_layout.addWidget(title)
        
        self.favorites_scroll_area = QScrollArea()
        self.favorites_scroll_area.setObjectName("FavoritesScroll")
        self.favorites_scroll_area.setWidgetResizable(True)
        
        self.favorites_list_frame = QFrame()
        self.favorites_list_frame.setObjectName("FavoritesListFrame")
        self.favorites_layout = QVBoxLayout(self.favorites_list_frame)
        self.favorites_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.favorites_scroll_area.setWidget(self.favorites_list_frame)
        
        self.favorites_panel_layout.addWidget(self.favorites_scroll_area) # Stretchable area

        # 3. API Settings Area (Fixed at bottom)
        api_settings_frame = QFrame()
        api_settings_frame.setObjectName("ApiSettingsFrame")
        api_settings_layout = QVBoxLayout(api_settings_frame)
        
        api_label = QLabel("API Key Settings")
        api_label.setObjectName("ApiLabel")
        api_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter your API key...")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.api_save_button = QPushButton("Save Key")
        self.api_save_button.setObjectName("ApiSaveButton")
        self.api_save_button.clicked.connect(self.save_api_key)
        
        api_link_label = QLabel(
            '<a href="https://home.openweathermap.org/api_keys">Get your API key here</a>'
        )
        api_link_label.setObjectName("ApiLink")
        api_link_label.setOpenExternalLinks(True)
        api_link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        api_settings_layout.addWidget(api_label)
        api_settings_layout.addWidget(self.api_key_input)
        api_settings_layout.addWidget(self.api_save_button)
        api_settings_layout.addWidget(api_link_label)

        self.favorites_panel_layout.addWidget(api_settings_frame)

    def create_main_panel(self): 
        """Creates the main content panel (search, results) in the background."""
        self.main_panel = QFrame(self)  
        self.main_panel.setObjectName("MainPanel")
        
        main_panel_layout = QVBoxLayout(self.main_panel)
        
        main_panel_layout.setContentsMargins(
            self.FAVORITES_PANEL_WIDTH + 30, # Left margin
            10, 10, 10 
        )
        main_panel_layout.setSpacing(15)

        # --- Search Area ---
        self.input_layout = QHBoxLayout()
        self.city_input = QLineEdit()
        self.city_input.setPlaceholderText("Enter a city name...")
        self.city_input.returnPressed.connect(self.get_weather)
        
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.get_weather)
        
        self.input_layout.addWidget(self.city_input)
        self.input_layout.addWidget(self.search_button)
        
        # --- Results Area ---
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.result_label = QLabel("Weather information will appear here.")
        self.result_label.setObjectName("ResultLabel")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setWordWrap(True)
        
        self.add_favorite_button = QPushButton("⭐ Add to favorites")
        self.add_favorite_button.clicked.connect(self.add_to_favorites)
        self.add_favorite_button.hide()

        # --- Add to layout ---
        main_panel_layout.addLayout(self.input_layout)
        main_panel_layout.addWidget(self.icon_label)
        main_panel_layout.addWidget(self.result_label)
        main_panel_layout.addWidget(self.add_favorite_button)
        main_panel_layout.addStretch()

    def apply_global_styles(self):
        """Applies the base QSS stylesheet."""
        self.setStyleSheet("""
            QWidget#WeatherWindow {
                background-color: #2c3e50;
            }
            QFrame#MainPanel {
                background-color: transparent; border: none;
            }
            /* Default Main Panel Styles */
            QFrame#MainPanel QLabel { color: white; font-size: 16px; }
            QFrame#MainPanel QLabel#ResultLabel { font-size: 18px; font-weight: bold; }
            QFrame#MainPanel QLineEdit {
                padding: 10px; font-size: 14px; border: 1px solid #555;
                border-radius: 5px; background-color: #5D6D7E; color: white;
            }
            QFrame#MainPanel QPushButton {
                background-color: #3498db; color: white; padding: 10px;
                font-size: 14px; font-weight: bold; border: none; border-radius: 5px;
            }
            QFrame#MainPanel QPushButton:hover { background-color: #2980b9; }
            
            /* --- Floating Favorites Panel --- */
            QFrame#FavoritesFrame {
                background-color: rgba(0, 0, 0, 120);
                border-radius: 10px; 
            }
            QFrame#FavoritesFrame > QLabel { /* Title */
                color: white; font-size: 16px; font-weight: bold; padding: 10px;
                border-bottom: 1px solid rgba(255, 255, 255, 50);
            }
            QScrollArea#FavoritesScroll {
                background-color: transparent; border: none;
            }
            QFrame#FavoritesListFrame { background-color: transparent; }
            
            /* Favorite Item Box */
            QFrame[class="FavoriteContainer"] {
                background-color: rgba(255, 255, 255, 30);
                border-radius: 5px; margin: 5px 10px;
            }
            QFrame[class="FavoriteContainer"]:hover {
                background-color: rgba(255, 255, 255, 50);
            }
            /* Favorite Item Contents */
            QFrame[class="FavoriteContainer"] QPushButton {
                background-color: transparent; border: none;
                color: white; font-size: 14px; padding: 5px; text-align: left;
            }
            QFrame[class="FavoriteContainer"] QPushButton:hover { color: #ddd; }
            QFrame[class="FavoriteContainer"] QLabel { padding: 0px; margin: 0px; }
            
            /* --- API Settings Box --- */
            QFrame#ApiSettingsFrame {
                background-color: rgba(0, 0, 0, 50);
                border-top: 1px solid rgba(255, 255, 255, 50);
                padding: 10px;
            }
            QFrame#ApiSettingsFrame QLabel { 
                color: #ccc; font-size: 12px; font-weight: bold; padding: 0;
            }
            QFrame#ApiSettingsFrame QLabel#ApiLink a {
                color: #3498db; text-decoration: none; font-size: 11px; font-weight: normal;
            }
            QFrame#ApiSettingsFrame QLineEdit {
                padding: 5px; font-size: 12px; border-radius: 3px; 
                background-color: #5D6D7E; color: white; border: 1px solid #555;
            }
            QPushButton#ApiSaveButton {
                background-color: #27ae60; color: white; padding: 5px;
                font-size: 12px; font-weight: bold; border: none; border-radius: 3px;
            }
            QPushButton#ApiSaveButton:hover { background-color: #229954; }
        """)
    
    def get_weather_stylesheet(self, weather_main):
        """Returns a dynamic QSS string based on the weather condition."""
        palettes = {
            "Clear": {
                "bg_style": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f1c40f, stop:1 #e67e22);",
                "text_color": "#222;",
                "btn_bg": "#2c3e50;", "btn_hover": "#233140;", "btn_text": "white;",
                "line_bg": "#f0f0f0;", "line_text": "#333;"
            },
            "Clouds": {
                "bg_style": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7f8c8d, stop:1 #95a5a6);",
                "text_color": "white;",
                "btn_bg": "#2c3e50;", "btn_hover": "#233140;", "btn_text": "white;",
                "line_bg": "#bdc3c7;", "line_text": "#333;"
            },
            "Rain": {
                "bg_style": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2c3e50, stop:1 #5D6D7E);",
                "text_color": "white;",
                "btn_bg": "#3498db;", "btn_hover": "#2980b9;", "btn_text": "white;",
                "line_bg": "#5D6D7E;", "line_text": "white;"
            },
            "Snow": {
                "bg_style": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #e0eafc, stop:1 #cfdef3);",
                "text_color": "#333;",
                "btn_bg": "#3498db;", "btn_hover": "#2980b9;", "btn_text": "white;",
                "line_bg": "#ffffff;", "line_text": "#333;"
            }
        }
        
        default_palette = palettes["Rain"] 

        if weather_main in ("Rain", "Drizzle", "Thunderstorm"):
            weather_key = "Rain"
        else:
            weather_key = weather_main
            
        palette = palettes.get(weather_key, default_palette)

        return f"""
            QWidget#WeatherWindow {{
                background-color: {palette['bg_style']}
            }}
            QFrame#MainPanel QLabel {{
                color: {palette['text_color']}
                background-color: transparent;
            }}
            QFrame#MainPanel QLineEdit {{
                background-color: {palette['line_bg']}
                color: {palette['line_text']}
                border: 1px solid gray; border-radius: 5px;
                padding: 10px; font-size: 14px;
            }}
            QFrame#MainPanel QPushButton {{
                background-color: {palette['btn_bg']}
                color: {palette['btn_text']}
                padding: 10px; font-size: 14px; font-weight: bold;
                border: none; border-radius: 5px;
            }}
            QFrame#MainPanel QPushButton:hover {{
                background-color: {palette['btn_hover']}
            }}
        """

    # --- Config (Save/Load) Functions ---

    def save_api_key(self):
        """Saves the API key from the input field."""
        self.api_key = self.api_key_input.text().strip()
        if not self.api_key:
            QMessageBox.warning(self, "API Key", "API key field is empty.")
            return
        
        self.save_config()
        QMessageBox.information(self, "API Key", "API key saved successfully!")
        self.api_key_input.setPlaceholderText("API key is set")
        self.api_key_input.clear()

    def save_config(self):
        """Saves the current API key and favorites to CONFIG_FILE."""
        config_data = {
            "api_key": self.api_key,
            "favorites": self.favorites 
        }
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(config_data, f, indent=4)
            print("Config saved.")
        except Exception as e:
            print(f"Error saving config: {e}")
            QMessageBox.warning(self, "Save Error", f"Could not save config file:\n{e}")

    def load_config(self):
        """Loads API key and favorites from CONFIG_FILE."""
        if not os.path.exists(self.CONFIG_FILE):
            print("Config file not found, starting fresh.")
            return
            
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                config_data = json.load(f)
            
            self.api_key = config_data.get("api_key", "")
            if self.api_key:
                self.api_key_input.setPlaceholderText("API key is set")
            
            self.favorites = config_data.get("favorites", {})
            for city_data in self.favorites.values():
                self.add_favorite_widget(city_data['name'], city_data['icon'])
            
            print(f"Loaded {len(self.favorites)} favorites and API key.")
                
        except Exception as e:
            print(f"Error loading config: {e}")
            self.favorites = {}
            self.api_key = ""

    # --- Core Logic Functions ---

    def get_weather(self, is_from_favorite=False):
        """Fetches weather data from the API."""
        if not self.api_key:
            QMessageBox.warning(self, "API Key Error", 
                                "Please enter and save your OpenWeatherMap API key "
                                "in the panel on the left.")
            return

        city_name = self.city_input.text().strip()
        if not city_name:
            QMessageBox.warning(self, "Error", "Please enter a city name")
            return

        if not is_from_favorite:
            self.city_input.clear()
            
        self.result_label.setText(f"Getting data for {city_name}...")
        self.icon_label.clear() 
        QApplication.processEvents()

        params = {'q': city_name, 'appid': self.api_key, 'units': 'metric', 'lang': 'en'}
        
        try :
            response = requests.get(self.BASE_URL, params=params, timeout=5)
            response.raise_for_status()
            weather_data = response.json()
            self.parse_and_display_weather(weather_data, is_from_favorite)
        except requests.exceptions.HTTPError as err:
            if response.status_code == 404:
                msg = "City not found."
            elif response.status_code == 401:
                msg = "Invalid API Key. Please check your key in the settings."
            else:
                msg = f"HTTP error: {err}"
            QMessageBox.critical(self, "Error", msg)
            self.clear_results()
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "Error", "Internet connection error.")
            self.clear_results()
        except requests.exceptions.RequestException as err:
            QMessageBox.critical(self, "Error", f"An error occurred: {err}")
            self.clear_results()

    def parse_and_display_weather(self, data, is_from_favorite=False):
        """Parses API data, updates UI, and applies dynamic style."""
        try:
            city_name = data['name']
            city_name_lower = city_name.lower()
            temperature = data['main']['temp']
            description = data['weather'][0]['description'].capitalize()
            country = data['sys']['country']
            feels_like = data['main']['feels_like']
            icon_id = data['weather'][0]['icon']
            weather_main = data['weather'][0]['main']
            
            dynamic_style = self.get_weather_stylesheet(weather_main)
            self.setStyleSheet(self.default_window_style + dynamic_style)

            self.result_label.setText(f"{city_name}, {country}\n"
                                      f"{description}\n"
                                      f"Temperature: {temperature:.1f}°C\n"
                                      f"Feels Like: {feels_like:.1f}°C")
            
            self._load_weather_icon(icon_id)
            self.current_city_data = data 
            
            if city_name_lower not in self.favorites and not is_from_favorite:
                self.add_favorite_button.setText(f"⭐ Add {city_name} to favorites")
                self.add_favorite_button.show()
            else:
                self.add_favorite_button.hide()

        except KeyError:
            QMessageBox.critical(self, "Error", "The received data could not be processed.")
            self.clear_results()

    # --- Icon Loading Helpers ---
    
    def _load_icon(self, icon_url, label, size=None):
        """Private helper to fetch an icon from a URL and set it on a QLabel."""
        try:
            image_data = requests.get(icon_url, timeout=5).content
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            
            if size:
                label.setPixmap(pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                label.setPixmap(pixmap)
        except Exception as e:
            print(f"Icon load error: {e}")
            label.setText("[Icon]")

    def _load_weather_icon(self, icon_id):
        """Loads the main (large) weather icon."""
        icon_url = f"https://openweathermap.org/img/wn/{icon_id}@2x.png" 
        self._load_icon(icon_url, self.icon_label)

    def _load_favorite_icon(self, icon_id, label):
        """Loads the small icon for the favorites list."""
        icon_url = f"https://openweathermap.org/img/wn/{icon_id}.png" 
        self._load_icon(icon_url, label, size=40)

    # --- Favorites Management ---

    def add_to_favorites(self):
        """Adds the current city to favorites and saves to config."""
        if not self.current_city_data:
            return
            
        city_name = self.current_city_data['name']
        city_name_lower = city_name.lower()
        
        if city_name_lower in self.favorites:
            return
            
        icon_id = self.current_city_data['weather'][0]['icon']
        
        self.favorites[city_name_lower] = {
            "name": city_name,
            "icon": icon_id
        }
        
        self.add_favorite_widget(city_name, icon_id)
        self.add_favorite_button.hide()
        self.save_config() # Save change
        print(f"Added to favorites: {city_name_lower}")

    def add_favorite_widget(self, city_name, icon_id):
        """Adds a new favorite city widget to the left panel."""
        city_name_lower = city_name.lower()
        
        widget = QFrame()
        widget.setProperty("class", "FavoriteContainer")
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        icon_label = QLabel()
        icon_label.setFixedSize(40, 40)
        self._load_favorite_icon(icon_id, icon_label)
        
        city_button = QPushButton(city_name)
        city_button.clicked.connect(partial(self.on_favorite_clicked, city_name))

        delete_button = QPushButton("❌")
        delete_button.setFixedSize(30, 30)
        delete_button.clicked.connect(partial(self.remove_from_favorites, city_name))

        layout.addWidget(icon_label)
        layout.addWidget(city_button, 1)
        layout.addWidget(delete_button)
        
        self.favorites_layout.addWidget(widget)
        self.favorite_widgets[city_name_lower] = widget

    def on_favorite_clicked(self, city_name):
        """Handles click on a favorite city button."""
        print(f"Favorite clicked: {city_name}")
        self.city_input.setText(city_name)
        self.get_weather(is_from_favorite=True)

    def remove_from_favorites(self, city_name):
        """Removes a city from favorites list, UI, and config."""
        print(f"Removing: {city_name}")
        city_name_lower = city_name.lower()
        
        self.favorites.pop(city_name_lower, None)
            
        widget_to_delete = self.favorite_widgets.pop(city_name_lower, None)
        if widget_to_delete:
            self.favorites_layout.removeWidget(widget_to_delete)
            widget_to_delete.deleteLater()
            
        if self.current_city_data and self.current_city_data['name'].lower() == city_name_lower:
            self.add_favorite_button.setText(f"⭐ Add {city_name} to favorites")
            self.add_favorite_button.show()
            
        self.save_config() # Save change

    def clear_results(self):
        """Resets the main panel to its default state on error."""
        self.result_label.setText("Weather information will appear here.")
        self.icon_label.clear()
        self.add_favorite_button.hide()
        self.current_city_data = None
        self.setStyleSheet(self.default_window_style)


if __name__=="__main__":
    app = QApplication(sys.argv)
    window = WeatherApp()
    window.show()
    sys.exit(app.exec())