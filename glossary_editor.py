import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import time
from datetime import datetime
import sqlite3
import re
import os
from src.glossary_db import GlossaryDatabase
from src.db_manager import DatabaseManager
from src.options_write import FormatDatabase, FormatManager, FormatWidgets
from src.glossary_os_handler import GlossaryOSHandler
from src.project_manager import ProjectDialog
from src.project_manager import ProjectManager
from abt.about_window import AboutWindow  # Updated import path
# In abt/about_window.py
from abt.info import APP_SETTINGS


class DatabaseViewer(ttk.Frame):
    def __init__(self, parent, db):
            ttk.Frame.__init__(self, parent)
            self.db = db
            print("\n=== Debug: Inizializzazione DatabaseViewer ===")
            print(f"Database path: {self.db.db_path if self.db else 'None'}")
            self.setup_ui()
            print("===============================")
    
    def setup_ui(self):
        """Configura l'interfaccia per la visualizzazione del database"""
        # Frame principale con scrollbar
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Crea il Treeview
        columns = ('ID', 'Categoria', 'Chiave', 'Tipo', 'Nome', 'First', 'Testo', 'Descrizione', 'Gruppo', 'Commento')
        self.tree = ttk.Treeview(main_frame, columns=columns, show='headings')
        self.tree = ttk.Treeview(main_frame, columns=columns, show='headings')
        
        # Configura le colonne
        widths = {
            'ID': 50,
            'Categoria': 100,
            'Chiave': 100,
            'Tipo': 100,
            'Nome': 150,
            'First': 200,
            'Testo': 150,
            'Descrizione': 300,
            'Gruppo':20,
            'Commento': 150
        }
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=widths[col])
        
        # Aggiungi scrollbar
        vsb = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(main_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Disponi gli elementi
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        # Configura il grid
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        
        # Pulsante di aggiornamento
        ttk.Button(self, text="Aggiorna Vista", 
                  command=self.update_view).pack(pady=5)
        
        # Carica i dati iniziali
        self.update_view()
    
    def update_view(self):
        """Aggiorna la vista con i dati più recenti dal database"""
        if not self.db:
            print("Database non disponibile per update_view")
            return
        print("\n=== Debug: Aggiornamento vista database ===")
                
        for item in self.tree.get_children():
            self.tree.delete(item)
                
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT e.id, c.name, e.key, e.type, e.name, 
                        e.first, e.text, e.description, 
                        c.group_name, c.comment
                    FROM entries e
                    JOIN categories c ON e.category_id = c.id
                    ORDER BY c.name, e.key
                ''')
                
                rows = cursor.fetchall()
                print(f"Recuperate {len(rows)} righe")
                for row in rows:
                    values = [
                        row[0],              # ID
                        row[1],              # Categoria
                        row[2],              # Chiave
                        row[3],              # Tipo
                        row[4],              # Nome
                        row[5],              # First
                        row[6],              # Testo
                        row[7],              # Descrizione
                        row[8],              # Gruppo (dalla tabella categories)
                        row[9]               # Commento
                    ]
                    print(f"Inserimento riga - Categoria: {values[1]}, Chiave: {values[2]}, Gruppo: {values[8]}")
                    self.tree.insert('', 'end', values=values)
                        
            print("Aggiornamento vista completato")
                    
        except sqlite3.Error as e:
                error_msg = f"Errore nel caricamento dei dati: {str(e)}"
                print(f"ERRORE: {error_msg}")
                messagebox.showerror("Errore Database", error_msg)
            
                print("===============================\n")

class GlossaryEditor(tk.Tk):
    def __init__(self):
        super().__init__()

        self.os_handler = GlossaryOSHandler()
        self.os_handler.ensure_directories_exist()
        
        self.title("LaTeX Glossary Editor - V2.3.0")
        self.geometry("1000x800")

        # Inizializza il project manager
       
        self.project_manager = ProjectManager()
        self.os_handler = GlossaryOSHandler()
        self.os_handler.ensure_directories_exist()
        self.db_manager = DatabaseManager()
        self.db_manager.connect()

        # Il database e db_manager verranno inizializzati quando si apre un progetto
        self.db = None # Sarà inizializzato quando si carica un progetto
        self.db_manager = None
        self.current_project = None
        
        # Inizializza le variabili
        self.category_var = tk.StringVar()
        self.type_var = tk.StringVar(value="\\acronymtype")
        self.math_mode = tk.BooleanVar(value=False)
        self.first_bold = tk.BooleanVar(value=False)
        self.current_category = self.category_var
        self.current_file = tk.StringVar(value="Nessun file selezionato")


        # Initialize database
        self.db = GlossaryDatabase()

        # Initialize formattazione
        self.format_db = FormatDatabase()
        
        # Contenitore per i campi di input
        self.fields = {}
        
        # Crea l'interfaccia
        self.create_menu()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create main editor tab
        self.editor_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.editor_frame, text="Editor")
        self.create_main_interface(self.editor_frame)
        
        # Create database viewer tab
        self.db_viewer_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.db_viewer_frame, text="Database")
        self.db_viewer = DatabaseViewer(self.db_viewer_frame, self.db)
        self.db_viewer.pack(fill=tk.BOTH, expand=True)
        
        # Carica le categorie iniziali
        self.update_category_list()
        
        # Aggiungi il gestore per la chiusura della finestra
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

         # Se non c'è nessun progetto aperto, mostra il dialog dei progetti
        self.show_project_dialog()
    
    def open_data_folder(self):
        """Apre la cartella dei dati dell'applicazione"""
        import os
        import subprocess
        path = self.os_handler.get_base_directory()
        if os.name == 'nt':  # Windows
            os.startfile(str(path))
        elif os.name == 'posix':  # macOS e Linux
            if os.system('which xdg-open') == 0:  # Linux
                subprocess.run(['xdg-open', str(path)])
            else:  # macOS
                subprocess.run(['open', str(path)])
  
    def create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Gestione Progetti", command=self.show_project_dialog)  # Aggiunto
        file_menu.add_separator()  # Aggiunto
        #file_menu.add_command(label="Importa da LaTeX", command=self.import_latex_file)
        file_menu.add_command(label="Esporta in LaTeX", command=self.export_latex_file)
        file_menu.add_separator()
        file_menu.add_command(label="Nuova Categoria", command=self.new_category)
        file_menu.add_command(label="Elimina Categoria", command=self.delete_category)
        file_menu.add_command(label="Pulisci Gruppi", command=self.db.cleanup_group_names)
        file_menu.add_separator()
        file_menu.add_command(label="Apri Cartella Dati", command=self.open_data_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Esci", command=self.quit)

        # Menu Help
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def load_project(self, project_name):
        # Close existing connections
        if self.db_manager:
            self.db_manager.close()
        if hasattr(self, 'db_viewer') and self.db_viewer.db:
            self.db_viewer.db = None
        """Carica un progetto esistente"""
        project = self.project_manager.get_project(project_name)
        if project:
            # Aggiorna il titolo con il nome del progetto
            self.title(f"LaTeX Glossary Editor - {project[1]}")

            # Pulisci tutti i campi dell'editor
            self.clear_fields()
            # Pulisci anche il campo commento
            self.category_comment.delete(0, tk.END)
            
            # Ottieni il percorso del database del progetto
            db_path = self.os_handler.get_database_path(project[4])  # project[4] è database_name
            
            # Inizializza database e manager con il path corretto
            self.db = GlossaryDatabase(db_path)
            self.db_manager = DatabaseManager(db_path)
            self.db_manager.connect()
            
            # Aggiorna l'interfaccia 
            self.update_category_list()
            
            # Salva il riferimento al progetto corrente
            self.current_project = project
            
            # Aggiorna la vista del database
            if hasattr(self, 'db_viewer'):
                self.db_viewer.db = self.db  # Aggiorna il riferimento al database
                self.db_viewer.update_view()
                
            return True
        return False

    def show_project_dialog(self):
        """Mostra la finestra di gestione progetti"""
        from src.project_manager import ProjectDialog
        dialog = ProjectDialog(self, self.project_manager)

        # Imposta la dimensione della finestra (larghezza x altezza)
        dialog.window.geometry("800x350")  # Modifica le dimensioni secondo necessità

        self.wait_window(dialog.window)  # Aspetta che la finestra venga chiusa

        # Se non c'è nessun progetto aperto dopo la chiusura del dialog, esci
        if not self.current_project:
            self.quit()
        
        # Aggiungi un callback per quando viene selezionato un progetto
        # dialog.project_list.bind('<<TreeviewSelect>>', lambda e: self._on_project_selected(dialog))
    
    def _on_project_selected(self, dialog):
        """Gestisce la selezione di un progetto dalla finestra di dialogo"""
        selected_items = dialog.project_list.selection()
        if selected_items:
            item = selected_items[0]
            project_name = dialog.project_list.item(item)['text']
            self.load_project(project_name)

    def show_about(self):
        """Mostra la finestra About"""
        from abt.about_window import AboutWindow
        AboutWindow(self)

    def create_input_field(self, parent, label_text, field_name, has_format=False):
        """Crea un campo di input con etichetta e opzionalmente un menu formato"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        
        # Etichetta
        ttk.Label(frame, text=label_text).pack(side=tk.LEFT)
        
        # Frame per input e formato
        input_frame = ttk.Frame(frame)
        input_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Campo di input
        entry = ttk.Entry(input_frame)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.fields[field_name] = entry

        if has_format:
            # Crea widget di formattazione
            format_widget = FormatWidgets(input_frame, field_name)
            format_widget.pack(side=tk.RIGHT)
            setattr(self, f'{field_name}_format', format_widget)
            
        return entry

    def create_main_interface(self, parent):
        """Crea l'interfaccia principale dell'editor"""
        # Frame principale
        main_container = ttk.Frame(parent)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Frame per categoria e commento
        category_frame = ttk.Frame(main_container)
        category_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Categoria con label
        cat_label_frame = ttk.Frame(category_frame)
        cat_label_frame.pack(fill=tk.X)
        ttk.Label(cat_label_frame, text="Categoria:").pack(side=tk.LEFT)
        self.category_combo = ttk.Combobox(cat_label_frame, textvariable=self.category_var)
        self.category_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.category_combo.bind('<<ComboboxSelected>>', self.on_category_select)
        
        # Commento categoria
        comment_frame = ttk.Frame(category_frame)
        comment_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(comment_frame, text="Commento:").pack(side=tk.LEFT)
        self.category_comment = ttk.Entry(comment_frame)
        self.category_comment.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        ttk.Button(comment_frame, text="Salva commento", 
                command=self.save_category_comment).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Aggiungi il campo per il gruppo qui, dopo che left_frame è stato creato
        group_frame = ttk.Frame(category_frame)
        group_frame.pack(fill=tk.X, pady=2)
        ttk.Label(group_frame, text="Gruppo:").pack(side=tk.LEFT)
        self.fields['group'] = ttk.Entry(group_frame)
        self.fields['group'].pack(side=tk.LEFT, fill=tk.X, expand=False, padx=(5, 0))
        ttk.Button(group_frame, text="Salva gruppo", 
        command=self.save_category_group).pack(side=tk.LEFT, padx=(5, 0))

        # Checkbox per modalità matematica
        ttk.Checkbutton(category_frame, text="Modalità matematica", 
                    variable=self.math_mode,
                    command=self.on_math_mode_change).pack(side=tk.LEFT,pady=5)

        # Frame per i controlli principali
        controls_frame = ttk.Frame(main_container)
        controls_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Pannello sinistro - Input fields
        left_frame = ttk.Frame(controls_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Campi di input
        self.fields['key'] = self.create_input_field(left_frame, "Chiave:", 'key')
        self.fields['name'] = self.create_input_field(left_frame, "Nome:", 'name', has_format=True)
        self.fields['first'] = self.create_input_field(left_frame, "Prima occorrenza:", 'first', has_format=True)
        self.fields['text'] = self.create_input_field(left_frame, "Testo:", 'text', has_format=True)

        # Frame per descrizione e anteprima
        desc_preview_frame = ttk.Frame(left_frame)
        desc_preview_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # Descrizione (ridotta)
        desc_frame = ttk.LabelFrame(desc_preview_frame, text="Descrizione")
        desc_frame.pack(fill=tk.BOTH, expand=False, pady=(5, 0))  # expand=False per ridurre l'altezza
        self.fields['description'] = tk.Text(desc_frame, wrap=tk.WORD, height=2)  # height ridotta a 2 righe
        self.fields['description'].pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Anteprima LaTeX
        preview_frame = ttk.LabelFrame(desc_preview_frame, text="Anteprima LaTeX")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self.latex_preview = tk.Text(preview_frame, wrap=tk.NONE, height=6)
        self.latex_preview.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Aggiungi scrollbar orizzontale all'anteprima
        preview_scroll = ttk.Scrollbar(preview_frame, orient="horizontal", command=self.latex_preview.xview)
        preview_scroll.pack(fill=tk.X, side=tk.BOTTOM)
        self.latex_preview.configure(xscrollcommand=preview_scroll.set)
        
        
        # Pannello destro - Lista definizioni
        right_frame = ttk.Frame(controls_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Lista con scrollbar
        list_frame = ttk.Frame(right_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(list_frame, text="Definizioni esistenti:").pack(fill=tk.X)
        
        list_scroll = ttk.Scrollbar(list_frame)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.entries_list = tk.Listbox(list_frame, height=10)
        self.entries_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.entries_list.config(yscrollcommand=list_scroll.set)
        list_scroll.config(command=self.entries_list.yview)
        
        self.entries_list.bind('<<ListboxSelect>>', self.on_entry_select)
        
        # Pulsanti
        button_frame = ttk.Frame(main_container)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Pulisci", 
                command=self.clear_fields).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Salva", 
                command=self.save_entry).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Elimina", 
                command=self.delete_entry).pack(side=tk.LEFT, padx=5)

        # Bind per aggiornamento anteprima
        for field_name, field in self.fields.items():
            if isinstance(field, tk.Text):
                field.bind('<KeyRelease>', self.update_preview)
            else:
                field.bind('<KeyRelease>', self.update_preview)

    def on_math_mode_change(self):
        """Gestisce il cambio della modalità matematica"""
        is_math = self.math_mode.get()
        
        # Aggiorna la modalità matematica per tutti i widget di formattazione
        for field_name in ['name', 'text', 'first']:
            if hasattr(self, f'{field_name}_format'):
                format_widget = getattr(self, f'{field_name}_format')
                format_widget.is_math_mode.set(is_math)
     
    def update_category_list(self):
        """Aggiorna la lista delle categorie nel menu a tendina"""
        if self.db and self.db_manager:  # Verifica entrambi i riferimenti
            print("\n=== Debug: Aggiornamento Lista Categorie ===")
            categories = self.db.get_categories()
            print(f"Categorie trovate: {categories}")
            
            self.category_combo['values'] = categories
            if categories and not self.category_var.get():
                self.category_var.set(categories[0])
                print(f"Categoria selezionata: {categories[0]}")
                self.update_entries_list()
            print("===============================")

    def update_entries_list(self):
        """Aggiorna la lista delle definizioni per la categoria selezionata"""
        self.entries_list.delete(0, tk.END)
        category = self.category_var.get()
        if category:
            entries = self.db.get_entries(category)
            for entry in entries:
                self.entries_list.insert(tk.END, entry['key'])
    
    def on_category_select(self, event=None):
        """Gestisce la selezione di una categoria"""
        print("\n=== Debug: Inizio on_category_select ===")
        category = self.category_var.get()
        print(f"Categoria selezionata: {category}")
        print(f"Database object: {self.db}")
        print(f"Database path: {self.db.db_path if self.db else 'None'}")
        
        if not category:
            print("Nessuna categoria selezionata")
            return
        
        if not self.db:
            print("Nessun database disponibile")
            return
            
        # Aggiorna la lista delle entries
        self.update_entries_list()
        
        # Ottieni il commento dalla categoria selezionata
        try:
            print(f"Tentativo di connessione al database: {self.db.db_path}")
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT comment, group_name FROM categories WHERE name = ?', (category,))
                result = cursor.fetchone()
                
                # Aggiorna il campo commento e gruppo
                print(f"Result from query: {result}")
                self.category_comment.delete(0, tk.END)
                self.fields['group'].delete(0, tk.END)
                if result:
                    comment, group_name = result
                    if comment:
                        self.category_comment.insert(0, comment)
                    if group_name:
                        # Prima controlla se ha \group{}
                        match = re.search(r'\\group{(.*?)}', group_name)
                        if match:
                            cleaned_group = match.group(1)
                        else:
                            cleaned_group = group_name
                        
                        self.fields['group'].insert(0, cleaned_group)
                        print(f"Gruppo caricato: {cleaned_group} (originale: {group_name})")
                    print(f"Commento caricato: {result[0]}")
                    print(f"Gruppo caricato: {result[1]}")
                else:
                    print("Nessun commento trovato nel database")
        except sqlite3.Error as e:
            print(f"Errore SQL: {str(e)}")
        except Exception as e:
            print(f"Errore generico: {str(e)}")
        
        print("=== Fine on_category_select ===")

    def save_category_comment(self):
        """Salva il commento della categoria"""
        category = self.category_var.get()
        comment = self.category_comment.get().strip()
        
        if not category:
            messagebox.showwarning("Attenzione", "Seleziona prima una categoria")
            return
            
        print(f"\n=== Debug: Salvataggio Commento ===")
        print(f"Categoria: {category}")
        print(f"Commento da salvare: {comment}")
        
        if self.db_manager.save_category_comment(category, comment):
            messagebox.showinfo("Successo", "Commento salvato correttamente")
            print("Commento salvato con successo")
        else:
            messagebox.showerror("Errore", "Impossibile salvare il commento")
            print("Errore nel salvataggio del commento")
        print("===============================")

    def new_category(self):
        """Crea una nuova categoria"""
        name = tk.simpledialog.askstring("Nuova Categoria", 
                                    "Nome della nuova categoria:")
        if name:
            try:
                # Genera un nuovo category_id
                category_id = f"CAT_{os.urandom(4).hex()}"
                
                # Inserisci la nuova categoria con il suo ID
                with sqlite3.connect(self.db.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO categories 
                        (name, category_id) 
                        VALUES (?, ?)
                    ''', (name, category_id))
                    conn.commit()
                    
                    print(f"Creata nuova categoria: {name} con ID: {category_id}")
                    
                    # Pulisci i campi correlati
                    self.category_comment.delete(0, tk.END)
                    self.fields['group'].delete(0, tk.END)
                    self.latex_preview.delete('1.0', tk.END)
                    self.clear_fields()
    
              
                    # Aggiorna le liste
                    self.update_category_list()
                    self.category_var.set(name)
                    self.update_entries_list()

                    # Aggiorna la vista del database se presente
                    if hasattr(self, 'db_viewer'):
                        self.db_viewer.update_view()
                        
            except sqlite3.IntegrityError:
                messagebox.showerror("Errore", 
                                f"Una categoria con il nome '{name}' esiste già")
            except Exception as e:
                messagebox.showerror("Errore", 
                                f"Errore durante la creazione della categoria: {str(e)}")
    
    def delete_category(self):
        """Elimina la categoria selezionata"""
        category = self.category_var.get()
        
        if not category:
            messagebox.showwarning("Attenzione", "Seleziona prima una categoria")
            return
            
        if category == "Generale":
            messagebox.showwarning("Attenzione", "Non è possibile eliminare la categoria Generale")
            return
        
        if messagebox.askyesno("Conferma", 
                            f"Vuoi davvero eliminare la categoria '{category}' e tutte le sue definizioni?"):
            success, message = self.db.delete_category(category)
            
            if success:
                messagebox.showinfo("Successo", message)
                self.clear_fields()
                self.update_category_list()
                if hasattr(self, 'db_viewer'):
                    self.db_viewer.update_view()
            else:
                messagebox.showerror("Errore", message)
                
    def save_category_group(self):
        """Salva il gruppo della categoria selezionata"""
        category = self.category_var.get()
        group = self.fields['group'].get().strip()
        
        if not category:
            messagebox.showwarning("Attenzione", "Seleziona prima una categoria")
            return
        
        try:
            # Salva il gruppo
            if self.db_manager.save_category_group(category, group):
                # Aggiorna entrambe le viste
                self.update_entries_list()
                if hasattr(self, 'db_viewer'):
                    self.db_viewer.update_view()
                messagebox.showinfo("Successo", "Gruppo salvato correttamente")
            else:
                messagebox.showerror("Errore", "Impossibile salvare il gruppo")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante il salvataggio: {str(e)}")
 
    def clean_latex_commands(self, text):
        """Pulisce i comandi LaTeX dal testo per la visualizzazione"""
        if not text:
            return ""
            
        print(f"\n=== Debug: Pulizia comando LaTeX ===")
        print(f"Testo originale: {text}")
        
        # Rimuovi i simboli del dollaro per la modalità matematica
        if text.startswith('$') and text.endswith('$'):
            text = text[1:-1]
        
        # Lista dei comandi LaTeX da rimuovere
        latex_commands = [
            (r'\\textbf{([^}]*)}', r'\1'),
            (r'\\textit{([^}]*)}', r'\1'),
            (r'\\mathbf{([^}]*)}', r'\1'),
            (r'\\mathit{([^}]*)}', r'\1'),
            (r'\\text{([^}]*)}', r'\1'),
        ]
        
        # Applica le sostituzioni
        result = text
        for pattern, replacement in latex_commands:
            result = re.sub(pattern, replacement, result)
        
        print(f"Testo pulito: {result}")
        print("===============================")
        
        return result

    def clean_group_value(self, group_text):
        """Rimuove \group{} per la visualizzazione nell'editor"""
        if not group_text:
            return ""
        match = re.search(r'\\group{(.*?)}', group_text)
        return match.group(1) if match else group_text

    def log_debug(self, method_name, message):
        """Salva i messaggi di debug in un file"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Ottieni il percorso base dell'applicazione
            base_dir = self.os_handler.get_base_directory()
            log_dir = base_dir / "logs"
            log_path = log_dir / "debug_log.txt"
            
            # Crea la directory dei log se non esiste
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Stampa il percorso del file di log
            #print(f"\nSalvataggio log in: {log_path}\n")
            
            with open(log_path, "a", encoding='utf-8') as f:
                f.write(f"\n[{timestamp}] {method_name}:\n{message}\n{'='*50}\n")
                
        except Exception as e:
            print(f"Errore durante il salvataggio del log: {str(e)}")
            print(f"Tentativo di salvare in: {log_path}")

    def on_entry_select(self, event):
        """Gestisce la selezione di una definizione dalla lista"""
        try:
            selection = self.entries_list.curselection()
            if not selection:
                return
                    
            key = self.entries_list.get(selection[0])
            category = self.category_var.get()
            format_db = FormatDatabase(self.db.db_path)

            #self.log_debug("on_entry_select", f"Selezione entry:\nKey: {key}\nCategoria: {category}")

            try:
                with sqlite3.connect(self.db.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT 
                            e.id,
                            e.key,
                            e.name,
                            e.first,
                            e.text,
                            e.description,
                            c.comment,
                            c.group_name,
                            fo.format_type,
                            fo.first_letter_bold,
                            fo.is_math_mode,
                            fo.format_type,
                            fo.first_letter_bold,
                            fo.is_math_mode
                        FROM entries e
                        JOIN categories c ON e.category_id = c.id
                        LEFT JOIN formatting_options fo ON e.id = fo.entry_id AND fo.field_name = 'name'
                        WHERE c.name = ? AND e.key = ?
                    ''', (category, key))
                        
                    entry = cursor.fetchone()
                    if entry:
                        # self.log_debug("on_entry_select", f"""
                        # Dati recuperati dal DB:
                        # ID: {entry[0]}
                        # Key: {entry[1]}
                        # Name: {entry[2]}
                        # First: {entry[3]}
                        # Text: {entry[4]}
                        # Description: {entry[5]}
                        # Comment: {entry[6]}
                        # Group: {entry[7]}
                        # Format Type: {entry[8]}
                        # First Letter Bold: {entry[9]}
                        # Is Math Mode: {entry[10]}
                        # First Format Type: {entry[11]}
                        # First Letter Bold Setting: {entry[12]}
                        # First Math Mode: {entry[13]}
                        # """)

                        # Pulisci tutti i campi
                        self.clear_fields()

                        # 1. Gestione campi base
                        # Chiave
                        self.fields['key'].insert(0, entry[1])

                        # 2. Gestione name con formattazione
                        name_settings = format_db.get_format(entry[0], 'name')
                        name_text = entry[2]
                        if name_settings['format_type'] == '\\textbackslash':
                            name_text = name_text.replace('\\textbackslash ', '')
                        else:
                            # Se è in modalità matematica, rimuovi i $ solo per l'editor
                            if name_settings['is_math_mode'] and name_text.startswith('$') and name_text.endswith('$'):
                                name_text = name_text[1:-1]  # Rimuovi $ solo per l'editor
                            else:
                                name_text = self.clean_latex_commands(name_text)
                        self.fields['name'].insert(0, name_text)
                        self.name_format.set_values(**name_settings)

                        # 3. Gestione first con formattazione speciale
                        first_settings = {
                            'format_type': entry[11] or 'Normale',
                            'first_letter_bold': bool(entry[12]),
                            'is_math_mode': bool(entry[13])
                        }
                        # Pulizia del testo first mantenendo eventuali contenuti matematici
                        first_text = entry[3]
                        if '($' in first_text:  # Se contiene formule matematiche in parentesi
                            first_text = self.clean_latex_commands(first_text)
                        else:
                            first_text = self.clean_latex_commands(first_text)
                        self.fields['first'].insert(0, first_text)
                        self.first_format.set_values(**first_settings)

                        # 4. Gestione text con formattazione
                        text_settings = format_db.get_format(entry[0], 'text')
                        text_text = entry[4]
                        if text_settings['format_type'] == '\\textbackslash':
                            text_text = text_text.replace('\\textbackslash ', '')
                        else:
                            # Se è in modalità matematica, rimuovi i $ solo per l'editor
                            if text_settings['is_math_mode'] and text_text.startswith('$') and text_text.endswith('$'):
                                text_text = text_text[1:-1]  # Rimuovi $ solo per l'editor
                            else:
                                text_text = self.clean_latex_commands(text_text)
                        self.fields['text'].insert(0, text_text)
                        self.text_format.set_values(**text_settings)

                        # 5. Gestione descrizione
                        self.fields['description'].delete('1.0', tk.END)
                        self.fields['description'].insert('1.0', entry[5] or '')

                        # 6. Gestione commento categoria
                        self.category_comment.delete(0, tk.END)
                        if entry[6]:  # comment
                            self.category_comment.insert(0, entry[6])

                        # 7. Gestione gruppo
                        self.fields['group'].delete(0, tk.END)
                        if entry[7]:  # group_name
                            group_match = re.search(r'\\group{(.*?)}', entry[7])
                            group_value = group_match.group(1) if group_match else entry[7]
                            self.fields['group'].insert(0, group_value)

                        # 8. Impostazione modalità matematica globale
                        self.math_mode.set(bool(entry[10]))

                        # 9. Aggiornamento formattazioni finali
                        for field_name in ['name', 'text', 'first']:
                            format_widget = getattr(self, f'{field_name}_format', None)
                            if format_widget:
                                settings = format_db.get_format(entry[0], field_name)
                                #self.log_debug("on_entry_select", f"Formattazione per {field_name}: {settings}")
                                format_widget.set_values(**settings)

                        # 10. Aggiorna l'anteprima
                        self.update_preview(use_original=True)
                        
            except sqlite3.Error as e:
                error_msg = f"Errore nel recupero dei dati: {str(e)}"
                #self.log_debug("on_entry_select", f"ERRORE: {error_msg}")
                messagebox.showerror("Errore Database", error_msg)
        
        except Exception as e:
            #self.log_debug("on_entry_select", f"ERRORE GENERALE: {str(e)}")
            raise

    def format_field(self, text, format_settings):
        """Applica la formattazione appropriata al testo"""
        if not text:
            return text
            
        format_type = format_settings.get('format_type', 'Normale')
        is_math_mode = format_settings.get('is_math_mode', False)
  
        # Correzione per gestire '\\textbf' e '\\textit' senza parentesi graffe
        if format_type == '\\textbf':
            format_type = '\\textbf{}'
        elif format_type == '\\textit':
            format_type = '\\textit{}'
        
        # Prima applica la formattazione base
        if format_type == 'Normale':
            formatted_text = text
        elif format_type == '\\textbackslash':
            formatted_text = f"\\textbackslash {text}"
            # Se è textbackslash, non applicare la modalità matematica
            is_math_mode = False
        elif format_type == '\\textbf{}':
            formatted_text = f"\\textbf{{{text}}}"
        elif format_type == '\\textit{}':
            formatted_text = f"\\textit{{{text}}}"
        elif format_type == '\\mathbf{}':
            formatted_text = f"\\mathbf{{{text}}}"
        elif format_type == '\\mathit{}':
            formatted_text = f"\\mathit{{{text}}}"
        else:
            formatted_text = text
        
        # Applica la modalità matematica solo se necessario e se non è un textbackslash
        if is_math_mode and format_type != '\\textbackslash':
            # Se il testo non contiene già $
            if not (formatted_text.startswith('$') and formatted_text.endswith('$')):
                formatted_text = f"${formatted_text}$"
        
        return formatted_text

    def update_preview(self, event=None, use_original=False):
        """Aggiorna l'anteprima LaTeX con i valori correnti dei campi"""
        try:
            # Se non c'è una chiave, mostra il template base
            if not self.fields['key'].get().strip():
                base_template = '''\\newglossaryentry{}{
        type=\\acronymtype,
        name={},
        first={},
        text={},
        description={},
        group={}
    }'''
                self.latex_preview.delete('1.0', tk.END)
                self.latex_preview.insert('1.0', base_template)
                return

            # Formatta name e text
            name = self.fields['name'].get().strip()
            text = self.fields['text'].get().strip()
            first = self.fields['first'].get().strip()

            # Ottieni e logga le impostazioni di formato
            name_settings = self.name_format.get_values()
            text_settings = self.text_format.get_values()
            first_settings = self.first_format.get_values()

            print("Name Settings:", name_settings)
            print("Text Settings:", text_settings)
            print("First Settings:", first_settings)

            # Applica la formattazione
            formatted_name = self.format_field(name, name_settings)
            formatted_text = self.format_field(text, text_settings)

            # Gestione speciale per il campo first
            if first_settings.get('first_letter_bold', False):
                words = first.split()
                formatted_words = []
                for word in words:
                    if '(' in word and ')' in word:
                        before_paren = word[:word.index('(')]
                        paren_content = word[word.index('('):]
                        if before_paren:
                            formatted_words.append(f'\\textbf{{{before_paren[0]}}}{before_paren[1:]}{paren_content}')
                        else:
                            formatted_words.append(word)
                    elif word.startswith('$') and word.endswith('$'):
                        formatted_words.append(word)
                    else:
                        if word:
                            first_letter = word[0]
                            rest = word[1:] if len(word) > 1 else ''
                            formatted_words.append(f'\\textbf{{{first_letter}}}{rest}')
                formatted_first = ' '.join(formatted_words)
            else:
                formatted_first = self.format_field(first, first_settings)
                print("Formatted First:", formatted_first)

            # Gestione del gruppo
            category_name = self.category_var.get()
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT group_name FROM categories WHERE name = ?', (category_name,))
                result = cursor.fetchone()
                group_value = result[0] if result else None

            # Se il gruppo esiste, estrai solo il valore interno
            group_text = ""
            if group_value:
                match = re.search(r'\\group{(.*?)}', group_value)
                if match:
                    group_text = f",\n    group={{{match.group(1)}}}"
                else:
                    group_text = f",\n    group={{{group_value}}}"


            # Genera il codice LaTeX
            latex_code = f"""\\newglossaryentry{{{self.fields['key'].get().strip()}}}{{
        type=\\acronymtype,
        name={{{formatted_name}}},
        first={{{formatted_first}}},
        text={{{formatted_text}}},
        description={{{self.fields['description'].get('1.0', tk.END).strip()}}}{group_text}
    }}"""
            
            print("Generated LaTeX Code:", latex_code)

            self.latex_preview.delete('1.0', tk.END)
            self.latex_preview.insert('1.0', latex_code)

        except Exception as e:
            #self.log_debug("update_preview", f"ERRORE: {str(e)}")
            print(f"Errore anteprima: {str(e)}")
            self.latex_preview.delete('1.0', tk.END)
            self.latex_preview.insert('1.0', f"Errore anteprima: {str(e)}")
   
    def save_entry(self):
        """Salva la definizione nel database"""
        if not self.db or not self.db_manager:
            messagebox.showerror("Errore", "Nessun progetto aperto. Aprire prima un progetto.")
            return

        category = self.category_var.get()
        if not category:
            messagebox.showerror("Errore", "Seleziona una categoria")
            return

        print("\n=== Debug: Salvataggio Entry ===")
        print(f"Categoria: {category}")
        print(f"Database path: {self.db.db_path}")

        key = self.fields['key'].get().strip()
        if not key:
            messagebox.showerror("Errore", "La chiave è obbligatoria")
            return

        try:
            self.db_manager = DatabaseManager(self.db.db_path)
            self.db_manager.connect()
            self.db_manager.begin_transaction()

            print("Inizio transazione database")

            # Salva il commento
            comment = self.category_comment.get().strip()
            if category:
                print(f"Salvataggio commento per categoria {category}: {comment}")
                self.db_manager.execute(
                    'UPDATE categories SET comment = ? WHERE name = ?',
                    (comment, category)
                )

            # Ottieni l'ID della categoria
            cursor = self.db_manager.execute('''
                SELECT id FROM categories WHERE name = ?
            ''', (category,))
            result = cursor.fetchone()
            
            if not result:
                print(f"Errore: categoria '{category}' non trovata nel database: {self.db.db_path}")
                messagebox.showerror("Errore", f"Categoria '{category}' non trovata nel database")
                self.db_manager.rollback()
                return
                
            category_id = result[0]
            print(f"ID Categoria trovato: {category_id}")

            # Salva il gruppo nella tabella categories
            # Ottieni e formatta il valore del gruppo
            group_value = self.fields['group'].get().strip()
            
            # Se c'è un valore per il gruppo
            if group_value:
                # Se non ha già il comando \group{}, aggiungilo
                if not group_value.startswith('\\group{'):
                    group_text = f"\\group{{{group_value}}}"
                else:
                    group_text = group_value
                    
                print(f"Salvataggio gruppo per categoria {category}: {group_text}")

            # Genera un nuovo definition_id
            definition_id = f"DEF_{os.urandom(4).hex()}"
            print(f"Nuovo definition_id generato: {definition_id}")

            # Prima cerca ed elimina l'entry esistente (case insensitive)
            print(f"Eliminazione entry esistente per key: {key}")
            self.db_manager.execute('''
                DELETE FROM entries 
                WHERE category_id = ? AND LOWER(key) = LOWER(?)
            ''', (category_id, key))

            # Ottieni i widget di formattazione e i loro valori
            print("Elaborazione formattazione testi")
            widgets_info = {
                'name': (self.name_format, self.fields['name'].get().strip()),
                'text': (self.text_format, self.fields['text'].get().strip()),
                'first': (getattr(self, 'first_format', None), self.fields['first'].get().strip())
            }

            # Formatta i testi
            formatted_texts = {}
            for field, (widget, text) in widgets_info.items():
                if widget:
                    values = widget.get_values()
                    if field == 'first':
                        formatted_texts[field] = FormatManager.format_text(
                            text,
                            values['format_type'],
                            False,  # Forza is_math_mode a False per 'first'
                            values.get('first_letter_bold', False)
                        )
                    elif values['format_type'] == '\\textbackslash':
                        # Gestione speciale per \textbackslash
                        formatted_texts[field] = f"\\textbackslash {text.strip()}"
                    else:
                        formatted_texts[field] = FormatManager.format_text(
                            text,
                            values['format_type'], 
                            values['is_math_mode'],
                            values.get('first_letter_bold', False)
                        )
                    print(f"Formattazione {field}: {text} -> {formatted_texts[field]}")
                else:
                    formatted_texts[field] = text

            description = self.fields['description'].get('1.0', tk.END).strip()
            print(f"Descrizione: {description[:50]}...")  # Primi 50 caratteri

            # Salva la nuova entry
            print("Salvataggio nuova entry")
            cursor = self.db_manager.execute('''
                INSERT INTO entries 
                (definition_id, category_id, key, type, name, first, text, description, is_math)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                definition_id,
                category_id,
                key,
                '\\acronymtype',
                formatted_texts['name'],
                formatted_texts['first'],
                formatted_texts['text'],
                description,
                0
            ))
            entry_id = cursor.lastrowid
            print(f"Nuovo entry_id: {entry_id}")

            # Aggiorna le opzioni di formattazione
            print("Salvataggio opzioni di formattazione")
            for field_name in ['name', 'text', 'first']:
                format_widget = getattr(self, f'{field_name}_format', None)
                if format_widget:
                    values = format_widget.get_values()
                    self.db_manager.execute('''
                        INSERT OR REPLACE INTO formatting_options 
                        (entry_id, field_name, format_type, is_math_mode, first_letter_bold)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        entry_id,
                        field_name,
                        values['format_type'],
                        values['is_math_mode'],
                        values.get('first_letter_bold', False)
                    ))
                    print(f"Formattazione salvata per {field_name}")

            self.db_manager.end_transaction()
            print("Transazione completata con successo")
            
            messagebox.showinfo("Successo", "Definizione salvata correttamente")
            self.update_entries_list()
            if hasattr(self, 'db_viewer'):
                self.db_viewer.update_view()
                # Aggiorna l'anteprima
            self.update_preview()

        except sqlite3.Error as e:
            print(f"Errore durante il salvataggio: {str(e)}")
            self.db_manager.rollback()
            messagebox.showerror("Errore Database", f"Errore durante il salvataggio: {str(e)}")
        finally:
            print("=== Fine Salvataggio Entry ===")
              
    def on_closing(self):
        """Gestisce la chiusura dell'applicazione"""
        if messagebox.askokcancel("Esci", "Vuoi davvero uscire?"):
            self.db_manager.close()
            self.quit()

    def clean_format(self, text):
        """Pulisce la formattazione dal testo"""
        for cmd in ['\\textbf{', '\\textit{', '\\mathbf{', '\\mathit{']:
            if cmd in text:
                text = text.replace(cmd, '').replace('}', '')
        if text.startswith('$') and text.endswith('$'):
            text = text[1:-1]
        return text
    
    def clear_fields(self):
        for field in self.fields.values():
            if field == self.fields['group']:
                continue
            if isinstance(field, tk.Text):
                field.delete('1.0', tk.END)
            else:
                field.delete(0, tk.END)
                
        # Reset formattazioni
        for field_name in ['name', 'text', 'first']:
            if hasattr(self, f'{field_name}_format'):
                format_widget = getattr(self, f'{field_name}_format')
                format_widget.set_values(
                    format_type='Normale',
                    is_math_mode=False,
                    first_letter_bold=False
                )
                
        self.math_mode.set(False)
        self.type_var.set('\\acronymtype')
        
        # Template base senza formattazione
        base_template = '''\\newglossaryentry{}{
            type=\\acronymtype,
            name={},
            first={},
            text={},
            description={},
            group={}
        }'''
        
        self.latex_preview.delete('1.0', tk.END)
        self.latex_preview.insert('1.0', base_template)
    
    def delete_entry(self):
        """Elimina la definizione selezionata"""
        selection = self.entries_list.curselection()
        if not selection:
            messagebox.showwarning("Attenzione", "Seleziona una definizione da eliminare")
            return
        
        if messagebox.askyesno("Conferma", "Vuoi davvero eliminare questa definizione?"):
            key = self.entries_list.get(selection[0])
            category = self.category_var.get()
            
            try:
                if self.db_manager.delete_entry(category, key):
                    self.entries_list.delete(selection[0])
                    self.clear_fields()
                    messagebox.showinfo("Successo", "Definizione eliminata")
                    
                    # Aggiorna anche la vista del database se presente
                    if hasattr(self, 'db_viewer'):
                        self.db_viewer.update_view()
                else:
                    messagebox.showerror("Errore", "Impossibile trovare la definizione da eliminare")
                    
            except sqlite3.Error as e:
                messagebox.showerror("Errore Database", 
                                f"Impossibile eliminare la definizione: {str(e)}")
    
    def import_latex_file(self):
        """Importa definizioni da un file LaTeX"""
        if not self.current_project:
            messagebox.showerror("Errore", "Aprire prima un progetto")
            return
            
        filename = filedialog.askopenfilename(
            filetypes=[("File TEX", "*.tex"), ("Tutti i file", "*.*")])
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                # Importa il contenuto nel database del progetto corrente
                self.db.import_from_latex(content)
                
                # Aggiorna l'interfaccia
                self.update_category_list()
                messagebox.showinfo("Successo", "File importato correttamente")
            except Exception as e:
                messagebox.showerror("Errore", f"Errore durante l'importazione: {str(e)}")
    
    def export_latex_file(self):
        """Esporta le definizioni in un file LaTeX"""
        filename = filedialog.asksaveasfilename(
            initialdir=self.os_handler.get_export_directory(),
            defaultextension=".tex",
            filetypes=[("File TEX", "*.tex"), ("Tutti i file", "*.*")]
        )
        if filename:
            try:
                # Genera il contenuto LaTeX dal database
                content = self.db.export_to_latex()
                
                # Salva su file
                with open(filename, 'w', encoding='utf-8') as file:
                    file.write(content)
                
                messagebox.showinfo("Successo", 
                                  "File esportato correttamente")
            except Exception as e:
                messagebox.showerror("Errore", 
                                   f"Errore durante l'esportazione: {str(e)}")


if __name__ == "__main__":
    app = GlossaryEditor()
    app.mainloop()