import sqlite3
import re
import tkinter as tk
from tkinter import ttk
from .glossary_os_handler import GlossaryOSHandler


class FormatDatabase:
    """Gestisce il database delle opzioni di formattazione"""
    def __init__(self, db_path=None):
        self.os_handler = GlossaryOSHandler()
        self.os_handler.ensure_directories_exist()
        # Se non viene fornito un percorso esplicito, usa quello predefinito
        self.db_path = db_path if db_path else self.os_handler.get_database_path()
        self._create_options_table()
    
    def _create_options_table(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS formatting_options (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER,
                    field_name TEXT,
                    format_type TEXT,
                    is_math_mode BOOLEAN DEFAULT 0,
                    first_letter_bold BOOLEAN DEFAULT 0,
                    FOREIGN KEY (entry_id) REFERENCES entries(id),
                    UNIQUE(entry_id, field_name)
                )
            ''')
            conn.commit()
    
    def save_format(self, entry_id, field_name, format_type, is_math_mode=False, first_letter_bold=False):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO formatting_options 
                (entry_id, field_name, format_type, is_math_mode, first_letter_bold)
                VALUES (?, ?, ?, ?, ?)
            ''', (entry_id, field_name, format_type, is_math_mode, first_letter_bold))
            conn.commit()
    
    def get_format(self, entry_id, field_name):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT format_type, is_math_mode, first_letter_bold
                FROM formatting_options
                WHERE entry_id = ? AND field_name = ?
            ''', (entry_id, field_name))
            result = cursor.fetchone()
            if result:
                return {
                    'format_type': result[0],
                    'is_math_mode': bool(result[1]),
                    'first_letter_bold': bool(result[2])
                }
            return {
                'format_type': 'normal',
                'is_math_mode': False,
                'first_letter_bold': False
            }

class FormatManager:
    """Gestisce la logica di formattazione del testo"""
    FORMAT_OPTIONS = {
        'normal': {'label': 'Normale', 'math': False},
        'textbf': {'label': '\\textbf{}', 'math': False},
        'textit': {'label': '\\textit{}', 'math': False},
        'mathbf': {'label': '\\mathbf{}', 'math': True},
        'mathit': {'label': '\\mathit{}', 'math': True},
        'textbackslash': {'label': '\\textbackslash', 'math': True}
    }
    
    @staticmethod
    def get_format_options(is_math_mode=False):
        """Restituisce le opzioni di formattazione disponibili per la modalità corrente"""
        return {k: v for k, v in FormatManager.FORMAT_OPTIONS.items() 
                if v['math'] == is_math_mode}

    @staticmethod
    def format_text(text, format_type, is_math_mode=False, first_letter_bold=False):
        """Gestione dei menu a cascata e formattazione del testo"""
        if not text:
            return text
            
        print(f"\n=== Debug: Formattazione testo ===")
        print(f"Testo originale: {text}")
        print(f"Formato: {format_type}")
        print(f"Math mode: {is_math_mode}")
        print(f"First letter bold: {first_letter_bold}")

        # Controllo per parentesi con \textbackslash
        if '(' in text and ')' in text:
            print("Rilevate parentesi nel testo")
            before_paren = text[:text.find('(')]
            paren_content = text[text.find('('): text.find(')')+1]
            after_paren = text[text.find(')')+1:]
            
            print(f"Contenuto prima delle parentesi: {before_paren}")
            print(f"Contenuto tra parentesi: {paren_content}")
            print(f"Contenuto dopo le parentesi: {after_paren}")
            
            # Se c'è \textbackslash nelle parentesi, tratta le parti separatamente
            if '\\textbackslash' in paren_content:
                print("Rilevato \\textbackslash nelle parentesi")
                # Formatta il testo prima delle parentesi
                if first_letter_bold and before_paren:
                    print("Applicazione grassetto prima lettera al testo prima delle parentesi")
                    words = before_paren.split()
                    formatted_words = []
                    for word in words:
                        if word:
                            formatted_words.append('\\textbf{' + word[0] + '}' + word[1:])
                            print(f"Parola formattata: {formatted_words[-1]}")
                    before_paren = ' '.join(formatted_words)
                result = before_paren + paren_content + after_paren
                print(f"Risultato con \\textbackslash preservato: {result}")
                print("===============================")
                return result

        # Gestione formato \textbackslash senza dollari
        if format_type == '\\textbackslash':
            print("Applicazione formato \\textbackslash")
            result = f"\\textbackslash {text}"  # Spazio aggiunto
            print(f"Risultato con \\textbackslash: {result}")
            print("===============================")
            return result.strip()  # Rimuove spazi extra


        def should_format(word):
            return not (word.startswith('(') and word.endswith(')'))

        result = text
        
        # Gestisci il grassetto della prima lettera
        if first_letter_bold:
            print("Applicazione grassetto prima lettera")
            words = text.split()
            result = []
            for word in words:
                if should_format(word) and word and not word.startswith('\\textbackslash'):
                    result.append('\\textbf{' + word[0] + '}' + word[1:])
                    print(f"Parola formattata: {result[-1]}")
                else:
                    result.append(word)
                    print(f"Parola non formattata: {word}")
            result = ' '.join(result)
            
        # Altrimenti applica format_type se non è Normale
        elif format_type != 'Normale':
            print(f"Applicazione formato: {format_type}")
            clean_format = format_type.strip('{}')
            result = f"{clean_format}{{{text}}}"

        # Applica la modalità matematica se richiesto e non è \textbackslash
        if is_math_mode and format_type != '\\textbackslash':
            print("Applicazione modalità matematica")
            result = f"${result}$"

        print(f"Risultato finale: {result}")
        print("===============================")
        return result
            
    @staticmethod
    def clean_format(text):
        """Rimuove la formattazione dal testo"""
        if not text:
            return text, 'Normale', False
            
        print(f"\n=== Debug: Pulizia comando LaTeX ===")
        print(f"Testo originale: {text}")
            
        is_math = text.startswith('$') and text.endswith('$')
        if is_math:
            text = text[1:-1]
        
        # Lista dei comandi LaTeX da controllare
        latex_commands = {
            r'\\textbf{([^}]*)}': ('\\textbf', False),
            r'\\textit{([^}]*)}': ('\\textit', False),
            r'\\mathbf{([^}]*)}': ('\\mathbf', True),
            r'\\mathit{([^}]*)}': ('\\mathit', True)
        }
        
        # Controlla i comandi
        for pattern, (format_type, math_mode) in latex_commands.items():
            match = re.search(pattern, text)
            if match:
                clean_text = match.group(1)
                print(f"Testo pulito: {clean_text}")
                print("===============================")
                return clean_text, format_type, math_mode or is_math
        
        print(f"Testo pulito: {text}")
        print("===============================")
        return text, 'Normale', is_math

class FormatWidgets:
    """Gestisce i widget di formattazione nell'interfaccia"""
    def __init__(self, parent, field_name):
        self.parent = parent
        self.field_name = field_name
        self.format_var = tk.StringVar(value='Normale')
        self.is_math_mode = tk.BooleanVar(value=False)
        self.first_letter_bold = tk.BooleanVar(value=False)
        
        # Crea il frame
        self.frame = ttk.Frame(parent)
        self.setup_widgets()
        # Collega il callback per il cambio di modalità matematica
        self.is_math_mode.trace_add('write', self._on_math_mode_change)
    
    def setup_widgets(self):
        """Crea i widget per la formattazione"""
        # Combobox per il formato
        self.format_combo = ttk.Combobox(
            self.frame,
            textvariable=self.format_var,
            values=self.get_format_options(),
            width=15,
            state='readonly'
        )
        self.format_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        if self.field_name == 'first':
            # Checkbox per il grassetto della prima lettera
            self.bold_check = ttk.Checkbutton(
                self.frame,
                text="Grassetto prima lettera",
                variable=self.first_letter_bold
            )
            self.bold_check.pack(side=tk.LEFT, padx=(5, 0))
    
    def _on_math_mode_change(self, *args):
        """Gestisce il cambio della modalità matematica"""
        current_value = self.format_var.get()
        new_options = self.get_format_options()
        
        # Se il valore corrente non è valido nella nuova modalità, resetta a Normale
        if current_value not in new_options:
            self.format_var.set('Normale')
        
        # Aggiorna le opzioni disponibili
        self.format_combo['values'] = new_options
    
    def pack(self, **kwargs):
        """Passa i parametri di pack al frame"""
        self.frame.pack(**kwargs)
     
    def get_format_options(self):
        """Ottiene le opzioni di formattazione disponibili"""
        is_math = self.is_math_mode.get()
        options = ['Normale']
        if is_math:
            options.extend(['\\mathbf{}', '\\mathit{}', '\\textbackslash'])
        else:
            options.extend(['\\textbf{}', '\\textit{}'])
        return options
    
    def update_format_options(self):
        """Aggiorna le opzioni disponibili nel combobox"""
        current = self.format_var.get()
        options = self.get_format_options()
        self.format_combo['values'] = options
        if current not in options:
            self.format_var.set('Normale')
    
    def format_text(self, text, format_type):
        """Formatta il testo in base al tipo di formato"""
        if format_type == 'Normale':
            return text
        return f"{format_type}{{{text}}}"
    
    def set_values(self, format_type='Normale', is_math_mode=False, first_letter_bold=False):
        """Imposta i valori dei widget"""
        self.is_math_mode.set(is_math_mode)
        
        # Rimuovi le graffe se presenti nel format_type
        if format_type.endswith('{}'):
            format_type = format_type[:-2]
        
        self.format_var.set(format_type)
        if hasattr(self, 'bold_check'):
            self.first_letter_bold.set(first_letter_bold)
            
    def get_values(self):
        """Restituisce i valori correnti"""
        format_type = self.format_var.get()
        
        return {
            'format_type': format_type,  # Non aggiungiamo più le graffe
            'is_math_mode': self.is_math_mode.get(),
            'first_letter_bold': self.first_letter_bold.get() if hasattr(self, 'bold_check') else False
        }