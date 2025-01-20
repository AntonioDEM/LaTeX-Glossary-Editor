import os
import platform
from pathlib import Path

class GlossaryOSHandler:
    def __init__(self):
        self.system = platform.system().lower()
        
    def is_windows(self):
        return self.system == 'windows'
        
    def is_mac(self):
        return self.system == 'darwin'
        
    def is_linux(self):
        return self.system == 'linux'
    
    def get_app_name(self):
        """Returns the application name for creating folders"""
        return "GlossaryEditor"
    
    def get_base_directory(self):
        """Returns the base directory for the application based on OS"""
        if self.is_windows():
            # Windows: Documents/GlossaryEditor
            docs = os.path.join(os.path.expanduser("~"), "Documents")
            return Path(docs) / self.get_app_name()
        elif self.is_mac():
            # macOS: ~/Documents/GlossaryEditor
            return Path(os.path.expanduser("~/Documents")) / self.get_app_name()
        else:
            # Linux: ~/.local/share/GlossaryEditor
            return Path(os.path.expanduser("~/.local/share")) / self.get_app_name()
    
    def get_database_directory(self):
        """Returns the directory where database files should be stored"""
        return self.get_base_directory() / "database"
    
    def get_database_path(self, filename="glossary.db"):
        """Returns the full path for the database file"""
        db_dir = self.get_database_directory()
        # Crea la directory se non esiste
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / filename
    
    def get_export_directory(self):
        """Returns the directory for exported files"""
        return self.get_base_directory() / "exports"
    
    def get_temp_directory(self):
        """Returns the directory for temporary files"""
        return self.get_base_directory() / "temp"
    
    def ensure_directories_exist(self):
        """Creates all necessary directories if they don't exist"""
        directories = [
            self.get_database_directory(),
            self.get_export_directory(),
            self.get_temp_directory()
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_file_path(self, filename, directory_type="database"):
        """
        Gets a file path in the specified directory type
        
        Args:
            filename (str): Name of the file
            directory_type (str): Type of directory ("database", "export", "temp")
        
        Returns:
            Path: Full path to the file
        """
        directory_map = {
            "database": self.get_database_directory,
            "export": self.get_export_directory,
            "temp": self.get_temp_directory
        }
        
        if directory_type not in directory_map:
            raise ValueError(f"Unknown directory type: {directory_type}")
            
        return directory_map[directory_type]() / filename
    
    def get_log_directory(self):
        """Returns the directory for log files"""
        if self.is_windows():
            return Path(os.getenv('APPDATA')) / self.get_app_name() / "logs"
        elif self.is_mac():
            return Path(os.path.expanduser("~/Library/Logs")) / self.get_app_name()
        else:
            return Path(os.path.expanduser("~/.local/share")) / self.get_app_name() / "logs"
    
    def get_log_directory(self):
        """Returns the directory for log files"""
        if self.is_windows():
            return Path(os.getenv('APPDATA')) / self.get_app_name() / "logs"
        elif self.is_mac():
            return Path(os.path.expanduser("~/Library/Logs")) / self.get_app_name()
        else:
            return Path(os.path.expanduser("~/.local/share")) / self.get_app_name() / "logs"
    
    def get_default_save_directory(self):
        """Returns the default directory for saving files"""
        return self.get_base_directory() / "documents"