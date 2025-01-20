# abt/about_window.py

import tkinter as tk
from tkinter import ttk
import webbrowser
import os
from pathlib import Path
from .info import APP_SETTINGS

class AboutWindow:
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("About")
        self.window.geometry("400x600")
        
        # Rendi la finestra modale
        self.window.transient(parent)
        self.window.grab_set()
        
        # Centra la finestra
        self.window.geometry("+%d+%d" % (
            parent.winfo_rootx() + parent.winfo_width()/2 - 200,
            parent.winfo_rooty() + parent.winfo_height()/2 - 300
        ))
        
        self._create_widgets()
        
    def _create_widgets(self):
        """Crea i widget della finestra about"""
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Logo (se disponibile)
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")
            if os.path.exists(logo_path):
                logo = tk.PhotoImage(file=logo_path)
                logo_label = ttk.Label(main_frame, image=logo)
                logo_label.image = logo  # Mantiene riferimento
                logo_label.pack(pady=10)
        except Exception as e:
            print(f"Errore caricamento logo: {e}")
        
        # Titolo
        title_label = ttk.Label(
            main_frame,
            text=APP_SETTINGS["app_name"],
            font=("Helvetica", 16, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Info progetto
        project_frame = self._create_info_section(
            main_frame,
            "Informazioni Progetto",
            [f"Versione: {APP_SETTINGS['version']}",
             f"Data rilascio: {APP_SETTINGS['release_date']}",
             APP_SETTINGS["description"]]
        )
        project_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Info sviluppatore
        dev_frame = self._create_info_section(
            main_frame,
            "Sviluppatore",
            [f"Nome: {APP_SETTINGS['developer']['name']}",
             f"Email: {APP_SETTINGS['developer']['email']}"]
        )
        dev_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Github link se disponibile
        if "github_url" in APP_SETTINGS:
            ttk.Button(
                main_frame,
                text="GitHub Repository",
                command=lambda: webbrowser.open(APP_SETTINGS["github_url"])
            ).pack(fill=tk.X, pady=2)
        
        # Pulsante chiusura
        ttk.Button(
            main_frame,
            text="Chiudi",
            command=self.window.destroy
        ).pack(pady=(20, 0))
        
    def _create_info_section(self, parent, title, items):
        """Crea una sezione di informazioni"""
        frame = ttk.LabelFrame(parent, text=title, padding="10")
        
        for item in items:
            ttk.Label(
                frame,
                text=item,
                wraplength=300
            ).pack(anchor="w", pady=2)
            
        return frame