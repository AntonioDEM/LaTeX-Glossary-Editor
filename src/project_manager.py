# src/project_manager.py

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox,filedialog
from datetime import datetime
from pathlib import Path
from .glossary_os_handler import GlossaryOSHandler
from .glossary_db import GlossaryDatabase

class ProjectManager:
    def __init__(self):
        self.os_handler = GlossaryOSHandler()
        self.os_handler.ensure_directories_exist()
        self.projects_db_path = self.os_handler.get_database_path("glossary_projects.db")
        self._create_projects_database()

    def _create_projects_database(self):
        """Crea il database principale dei progetti"""
        with sqlite3.connect(self.projects_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    latex_file_path TEXT,
                    database_name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_imported BOOLEAN DEFAULT 0
                )
            ''')
            conn.commit()
    
    def get_all_projects(self):
        """Recupera tutti i progetti dal database"""
        try:
            with sqlite3.connect(self.projects_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM projects 
                    ORDER BY last_modified DESC
                ''')
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Errore nel recupero dei progetti: {e}")
            return []

    def create_project_from_import(self, latex_file_path, description=""):
        """Crea un nuovo progetto da un file LaTeX importato"""
        try:
            # Usa il nome del file LaTeX come nome del progetto e del database
            file_name = Path(latex_file_path).stem
            database_name = f"{file_name}.db"
            
            # Crea il progetto nel database principale
            with sqlite3.connect(self.projects_db_path) as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute('''
                        INSERT INTO projects 
                        (name, description, latex_file_path, database_name, is_imported)
                        VALUES (?, ?, ?, ?, 1)
                    ''', (file_name, description, latex_file_path, database_name))
                    conn.commit()
                except sqlite3.IntegrityError:
                    # Se il progetto esiste già, genera un nome univoco
                    counter = 1
                    while True:
                        try:
                            new_name = f"{file_name}_{counter}"
                            database_name = f"{new_name}.db"
                            cursor.execute('''
                                INSERT INTO projects 
                                (name, description, latex_file_path, database_name, is_imported)
                                VALUES (?, ?, ?, ?, 1)
                            ''', (new_name, description, latex_file_path, database_name))
                            conn.commit()
                            break
                        except sqlite3.IntegrityError:
                            counter += 1

            # Inizializza il database del progetto e importa i dati
            db_path = self.os_handler.get_database_path(database_name)
            db = GlossaryDatabase(db_path)
            
            # Legge e importa il contenuto del file LaTeX
            with open(latex_file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                db.import_from_latex(content)
            
            return db_path
                    
        except Exception as e:
            print(f"Errore nella creazione del progetto: {e}")
            raise

    def create_project(self, name, description=""):
        """Crea un nuovo progetto vuoto"""
        try:
            database_name = f"{name.lower().replace(' ', '_')}.db"
            
            with sqlite3.connect(self.projects_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO projects 
                    (name, description, database_name, is_imported)
                    VALUES (?, ?, ?, 0)
                ''', (name, description, database_name))
                conn.commit()
                
                # Inizializza il database del progetto
                db_path = self.os_handler.get_database_path(database_name)
                with sqlite3.connect(db_path) as project_conn:
                    project_cursor = project_conn.cursor()
                    
                    # Crea le tabelle necessarie
                    project_cursor.execute('''
                        CREATE TABLE IF NOT EXISTS categories (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            category_id TEXT UNIQUE,
                            name TEXT NOT NULL,
                            comment TEXT,
                            group_name TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(name COLLATE NOCASE)
                        )
                    ''')
                    
                    # Inserisci la categoria "Generale" di default
                    project_cursor.execute('''
                        INSERT INTO categories (name, category_id)
                        VALUES ("Generale", "CAT_GEN_001")
                    ''')
                    
                    project_conn.commit()
                
                return db_path
                
        except sqlite3.IntegrityError:
            raise ValueError(f"Un progetto con il nome '{name}' esiste già")
            
    def delete_project(self, name):
        """Elimina un progetto e il suo database"""
        try:
            with sqlite3.connect(self.projects_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT database_name FROM projects WHERE name = ?', (name,))
                result = cursor.fetchone()
                
                if result:
                    database_path = self.os_handler.get_database_path(result[0])
                    if database_path.exists():
                        database_path.unlink()
                    
                cursor.execute('DELETE FROM projects WHERE name = ?', (name,))
                conn.commit()
                return True
        except Exception as e:
            print(f"Errore nell'eliminazione del progetto: {e}")
            return False
            
    def get_project(self, name):
        """Recupera i dettagli di un progetto specifico"""
        with sqlite3.connect(self.projects_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM projects WHERE name = ?', (name,))
            return cursor.fetchone()
        
    def update_project(self, name, description=None, latex_file_path=None):
        """Aggiorna i dettagli di un progetto esistente"""
        try:
            update_fields = []
            values = []
            
            if description is not None:
                update_fields.append("description = ?")
                values.append(description)
                
            if latex_file_path is not None:
                update_fields.append("latex_file_path = ?")
                values.append(latex_file_path)
                
            if not update_fields:
                return False
                
            update_fields.append("last_modified = CURRENT_TIMESTAMP")
            values.append(name)  # per la clausola WHERE
            
            with sqlite3.connect(self.projects_db_path) as conn:
                cursor = conn.cursor()
                query = f'''
                    UPDATE projects 
                    SET {", ".join(update_fields)}
                    WHERE name = ?
                '''
                cursor.execute(query, values)
                conn.commit()
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            print(f"Errore nell'aggiornamento del progetto: {e}")
            return False


class ProjectDialog:
    def __init__(self, parent, project_manager):
        self.window = tk.Toplevel(parent)
        self.window.title("Gestione Progetti")
        self.window.geometry("700x500")
        self.project_manager = project_manager
        self.parent = parent
        
        self.window.transient(parent)
        self.window.grab_set()
        
        self._create_widgets()
        self._update_project_list()
    
    def _create_widgets(self):
        # Frame principale
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame superiore per i pulsanti principali
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(top_frame, text="Nuovo Progetto", 
                   command=self._new_project).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Nuovo Progetto da LaTeX", 
                   command=self._import_latex).pack(side=tk.LEFT, padx=5)
        
        # Lista progetti e dettagli
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Lista progetti (sinistra)
        list_frame = ttk.LabelFrame(content_frame, text="Progetti", padding="5")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.project_list = ttk.Treeview(list_frame, columns=('type',), show='tree')
        self.project_list.heading('#0', text='Nome')
        self.project_list.heading('type', text='Tipo')
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", 
                                 command=self.project_list.yview)
        self.project_list.configure(yscrollcommand=scrollbar.set)
        
        self.project_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Dettagli progetto (destra)
        details_frame = ttk.LabelFrame(content_frame, text="Dettagli Progetto", 
                                      padding="5")
        details_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ttk.Label(details_frame, text="Nome:").pack(anchor=tk.W)
        self.name_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=self.name_var).pack(fill=tk.X, pady=2)
        
        ttk.Label(details_frame, text="Descrizione:").pack(anchor=tk.W)
        self.desc_text = tk.Text(details_frame, height=4)
        self.desc_text.pack(fill=tk.X, pady=2)
        
        self.file_path_var = tk.StringVar()
        self.file_path_label = ttk.Label(details_frame, 
                                        textvariable=self.file_path_var, 
                                        wraplength=250)
        self.file_path_label.pack(anchor=tk.W, pady=5)
        
        # Pulsanti azioni
        btn_frame = ttk.Frame(details_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="Apri", 
                   command=self._open_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Salva", 
                   command=self._save_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Elimina", 
                   command=self._delete_project).pack(side=tk.LEFT, padx=2)
        
        # Eventi
        self.project_list.bind('<<TreeviewSelect>>', self._on_project_select)
    
    def _import_latex(self):
        """Importa un file LaTeX creando un nuovo progetto e importando i dati"""
        file_path = filedialog.askopenfilename(
            filetypes=[("File LaTeX", "*.tex"), ("Tutti i file", "*.*")]
        )
        if file_path:
            try:
                # Usa il nome del file come nome del progetto
                file_name = Path(file_path).stem
                
                # Crea il progetto e importa i dati usando il project_manager
                db_path = self.project_manager.create_project_from_import(file_path)
                
                self._update_project_list()
                messagebox.showinfo("Successo", "File LaTeX importato correttamente come nuovo progetto")
                
            except Exception as e:
                messagebox.showerror("Errore", f"Errore durante l'importazione: {str(e)}")
    
    def _update_project_list(self):
        """Aggiorna la lista dei progetti nel Treeview"""
        # Pulisci la lista esistente
        for item in self.project_list.get_children():
            self.project_list.delete(item)
            
        # Inserisci i progetti
        for project in self.project_manager.get_all_projects():
            project_type = "Importato" if project[7] else "Nuovo"  # Controlla is_imported
            self.project_list.insert('', 'end', 
                                   text=project[1],  # nome del progetto
                                   values=(project_type,))  # tipo di progetto
    
    def _new_project(self):
        """Pulisce i campi per un nuovo progetto"""
        self.name_var.set("")
        self.desc_text.delete('1.0', tk.END)
        self.file_path_var.set("")
    
    def _open_project(self):
        """Apre il progetto selezionato"""
        selected_items = self.project_list.selection()
        if not selected_items:
            messagebox.showwarning("Attenzione", "Seleziona un progetto da aprire")
            return
            
        item = selected_items[0]
        project_name = self.project_list.item(item)['text']
        
        if self.parent.load_project(project_name):
            self.window.destroy()  # Chiude la finestra di dialogo
        else:
            messagebox.showerror("Errore", "Impossibile aprire il progetto")

    def _save_project(self):
        """Salva o aggiorna il progetto"""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Errore", "Il nome del progetto è obbligatorio")
            return
            
        description = self.desc_text.get('1.0', tk.END).strip()
        
        try:
            # Verifica se il progetto esiste già
            existing_project = self.project_manager.get_project(name)
            if existing_project:
                # Aggiorna il progetto esistente
                self.project_manager.update_project(name, description)
                messagebox.showinfo("Successo", "Progetto aggiornato correttamente")
            else:
                # Crea nuovo progetto
                self.project_manager.create_project(name, description)
                messagebox.showinfo("Successo", "Nuovo progetto creato correttamente")
            
            self._update_project_list()
            
        except Exception as e:
            messagebox.showerror("Errore", str(e))
    
    def _delete_project(self):
        """Elimina il progetto selezionato"""
        selected_items = self.project_list.selection()
        if not selected_items:
            messagebox.showwarning("Attenzione", "Seleziona un progetto da eliminare")
            return
            
        item = selected_items[0]
        project_name = self.project_list.item(item)['text']
        
        if messagebox.askyesno("Conferma", f"Vuoi davvero eliminare il progetto '{project_name}'?"):
            if self.project_manager.delete_project(project_name):
                self._update_project_list()
                # Pulisci i campi
                self.name_var.set("")
                self.desc_text.delete('1.0', tk.END)
                self.file_path_var.set("")
                messagebox.showinfo("Successo", "Progetto eliminato correttamente")
            else:
                messagebox.showerror("Errore", "Impossibile eliminare il progetto")

    def _on_project_select(self, event):
        """Gestisce la selezione di un progetto dal Treeview"""
        selected_items = self.project_list.selection()  # Usa selection() invece di curselection()
        if selected_items:  # Se c'è un item selezionato
            item = selected_items[0]  # Prendi il primo item selezionato
            project_name = self.project_list.item(item)['text']  # Ottieni il nome del progetto
            
            project = self.project_manager.get_project(project_name)
            if project:
                # Aggiorna i campi con i dettagli del progetto
                self.name_var.set(project[1])  # nome
                self.desc_text.delete('1.0', tk.END)
                self.desc_text.insert('1.0', project[2] or "")  # descrizione
                
                # Aggiorna il percorso del file LaTeX se presente
                if project[3]:  # latex_file_path
                    self.file_path_var.set(f"File LaTeX: {project[3]}")
                else:
                    self.file_path_var.set("")