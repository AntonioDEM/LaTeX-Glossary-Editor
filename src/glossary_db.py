import sqlite3
import os
import re
from datetime import datetime
from .latex_parser import parse_glossary_entry  # Aggiunto il punto per l'importazione relativa
from .glossary_os_handler import GlossaryOSHandler


#costante di default per import e export
DEFAULT_GLOSSARY_ENTRY = '''%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% DEFINIZIONI Generale
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Inserire definizioni di default

\\newglossaryentry{}{
        type=\\acronymtype,
        name={\\textbf{}},
        first={},
        text={},
        description={},
        group={}
    }
'''

class GlossaryDatabase:
    def __init__(self, db_path=None):
        self.os_handler = GlossaryOSHandler()
        self.os_handler.ensure_directories_exist()
        self.db_path = db_path or self.os_handler.get_database_path()
        self._create_database()
        # Aggiungi qui la chiamata per correggere gli ID NULL
        self.fix_null_category_ids()

    def fix_null_category_ids(self):
        """Controlla e corregge eventuali category_id NULL, assegna un category_id se non presente"""
        print("\n=== Controllo category_id NULL ===")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Trova tutte le categorie con category_id NULL
                cursor.execute('''
                    SELECT id, name 
                    FROM categories 
                    WHERE category_id IS NULL
                ''')
                
                null_categories = cursor.fetchall()
                print(f"Trovate {len(null_categories)} categorie senza ID")
                
                # Per ogni categoria senza ID
                for cat_id, cat_name in null_categories:
                    # Genera un nuovo category_id
                    new_category_id = f"CAT_{os.urandom(4).hex()}"
                    
                    # Aggiorna la categoria
                    cursor.execute('''
                        UPDATE categories 
                        SET category_id = ? 
                        WHERE id = ?
                    ''', (new_category_id, cat_id))
                    
                    print(f"Aggiornata categoria '{cat_name}' con nuovo ID: {new_category_id}")
                
                conn.commit()
                print("Aggiornamento completato")
                return True
                
        except sqlite3.Error as e:
            print(f"Errore durante la correzione degli ID: {str(e)}")
            return False
 
    def _create_database(self):
        print("Creazione database...")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Tabella categories
            cursor.execute('''
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

            # Tabella entries 
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    definition_id TEXT UNIQUE,
                    category_id INTEGER,
                    key TEXT NOT NULL,
                    type TEXT NOT NULL DEFAULT '\\acronymtype',
                    name TEXT NOT NULL,
                    first TEXT NOT NULL,
                    text TEXT NOT NULL,
                    description TEXT,
                    is_math BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
                    UNIQUE(category_id, key COLLATE NOCASE)
                )
            ''')

            # Tabella formatting_options
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS formatting_options (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER,
                    field_name TEXT,
                    format_type TEXT,
                    is_math_mode BOOLEAN DEFAULT 0,
                    first_letter_bold BOOLEAN DEFAULT 0,     
                    FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE,
                    UNIQUE(entry_id, field_name)
                )
            ''')

            # Categoria default con ID predefinito
            generale_id = "CAT_GEN_001"
            cursor.execute('''
                INSERT OR IGNORE INTO categories 
                (name, category_id) 
                VALUES ("Generale", ?)
            ''', (generale_id,))
            conn.commit()
            print("Database creato correttamente")
            # Verifica e correggi eventuali category_id NULL
            self.fix_null_category_ids()
    
    def add_category(self, name, comment=None):
        """Aggiunge una nuova categoria con commento opzionale"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('INSERT INTO categories (name, comment) VALUES (?, ?)', 
                             (name, comment))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                print(f"Errore: la categoria {name} esiste già")
                return False
            except sqlite3.Error as e:
                print(f"Errore database: {e}")
                return False
    
    def delete_category(self, category_name):
        """Elimina una categoria e tutte le sue entries"""
        if category_name == "Generale":
            return False, "Non è possibile eliminare la categoria Generale"
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                # Inizia la transazione
                cursor.execute("BEGIN IMMEDIATE")
                
                # Ottieni l'ID della categoria
                cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
                result = cursor.fetchone()
                
                if not result:
                    return False, "Categoria non trovata"
                
                category_id = result[0]
                
                # Elimina tutte le formatting_options associate alle entries della categoria
                cursor.execute('''
                    DELETE FROM formatting_options 
                    WHERE entry_id IN (
                        SELECT id FROM entries WHERE category_id = ?
                    )
                ''', (category_id,))
                
                # Elimina tutte le entries della categoria
                cursor.execute('DELETE FROM entries WHERE category_id = ?', (category_id,))
                
                # Elimina la categoria
                cursor.execute('DELETE FROM categories WHERE id = ?', (category_id,))
                
                conn.commit()
                return True, "Categoria eliminata con successo"
                
            except sqlite3.Error as e:
                conn.rollback()
                return False, f"Errore durante l'eliminazione: {str(e)}"
    
    def update_category_comment(self, category_name, comment):
        """Aggiorna il commento di una categoria"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE categories SET comment = ? WHERE name = ?', 
                         (comment, category_name))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_category_comment(self, category_name):
        """Ottiene il commento di una categoria"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT comment FROM categories WHERE name = ?', 
                         (category_name,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def get_categories(self):
        """Restituisce tutte le categorie"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT name FROM categories ORDER BY name')
            return [row[0] for row in cursor.fetchall()]
    
    def cleanup_group_names(self):
        """Pulisce la colonna group_name da \group{}"""
        print("\n=== Pulizia group_name nel database ===")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Trova tutte le categorie con \group{}
                cursor.execute('SELECT id, name, group_name FROM categories WHERE group_name LIKE "%\\group{%"')
                groups_to_clean = cursor.fetchall()
                
                print(f"Trovate {len(groups_to_clean)} categorie da pulire")
                
                for cat_id, cat_name, group_name in groups_to_clean:
                    # Estrai il valore interno
                    match = re.search(r'\\group{(.*?)}', group_name)
                    if match:
                        clean_value = match.group(1)
                        cursor.execute('''
                            UPDATE categories 
                            SET group_name = ? 
                            WHERE id = ?
                        ''', (clean_value, cat_id))
                        print(f"Categoria '{cat_name}': {group_name} -> {clean_value}")
                
                conn.commit()
                print("Pulizia completata")
                return True
            
        except sqlite3.Error as e:
            print(f"Errore durante la pulizia: {str(e)}")
            return False
    
    def add_entry(self, category_name, entry_data):
        """Aggiunge o aggiorna una definizione"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                # Ottieni l'ID della categoria
                cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
                category_id = cursor.fetchone()
                
                if not category_id:
                    return False
                
                # Crea l'entry LaTeX
                latex_key = f"\\newglossaryentry{{{entry_data['key']}}}"
                
                # Aggiunge l'entry nel database
                cursor.execute('''
                    INSERT OR REPLACE INTO entries
                    (category_id, key, type, name, first, text, description, is_math)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    category_id[0],
                    latex_key,
                    entry_data.get('type', '\\acronymtype'),
                    entry_data['name'],
                    entry_data['first'],
                    entry_data['text'],
                    entry_data['description'],
                    entry_data.get('is_math', False)
                ))
                
                conn.commit()
                return True
            except sqlite3.Error as e:
                print(f"Errore database: {e}")
                return False
    
    def get_entries(self, category_name):
        """Restituisce tutte le definizioni per una categoria"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT e.* FROM entries e
                JOIN categories c ON e.category_id = c.id
                WHERE c.name = ?
                ORDER BY e.key
            ''', (category_name,))
            
            columns = [desc[0] for desc in cursor.description]
            entries = []
            for row in cursor.fetchall():
                entry = dict(zip(columns, row))
                # Pulisci la chiave rimuovendo \newglossaryentry{...}
                if entry['key'].startswith('\\newglossaryentry{'):
                    entry['key'] = entry['key'][16:-1]  # Rimuovi \newglossaryentry{ e }
                entries.append(entry)
            return entries
    
    def get_all_entries(self):
        """Restituisce tutte le entries nel database con i nomi delle categorie"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    c.name as category_name,
                    e.key,
                    e.type,
                    e.name,
                    e.first,
                    e.text,
                    e.description,
                    e.created_at,
                    e.updated_at
                FROM entries e
                JOIN categories c ON e.category_id = c.id
                ORDER BY c.name, e.key
            ''')
            
            columns = [description[0] for description in cursor.description]
            entries = []
            for row in cursor.fetchall():
                entries.append(dict(zip(columns, row)))
            
            return entries
    
    def delete_entry(self, category_name, key):
        """Elimina una definizione dal database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                # Ottieni l'ID della categoria
                cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
                category_id = cursor.fetchone()
                
                if not category_id:
                    return False
                
                # Crea la chiave LaTeX completa
                latex_key = f"\\newglossaryentry{{{key}}}"
                
                # Elimina l'entry
                cursor.execute('''
                    DELETE FROM entries 
                    WHERE category_id = ? AND key = ?
                ''', (category_id[0], latex_key))
                
                conn.commit()
                return cursor.rowcount > 0
            except sqlite3.Error as e:
                print(f"Errore database: {e}")
                return False
            
    def export_to_latex(self):
        """Esporta tutte le definizioni in formato LaTeX"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            content = ""
            
            # Prima controlla se la categoria Generale ha entries
            cursor.execute('''
                SELECT EXISTS(
                    SELECT 1 FROM entries e 
                    JOIN categories c ON e.category_id = c.id 
                    WHERE c.name = 'Generale'
                )
            ''')
            has_generale_entries = cursor.fetchone()[0]
            
            # Ottieni tutte le categorie con i loro commenti
            cursor.execute('''
                SELECT c.name, c.comment 
                FROM categories c
                WHERE (c.name != 'Generale' OR (c.name = 'Generale' AND ?))
                ORDER BY 
                    CASE WHEN c.name = 'Generale' THEN 0 ELSE 1 END,
                    c.name
            ''', (has_generale_entries,))
            
            for category_name, comment in cursor.fetchall():
                content += "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n"
                content += f"% DEFINIZIONI {category_name}\n"
                content += "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n"
                
                if comment and comment.strip():
                    content += f"% {comment}\n"
                    
                content += "\n"
                
                cursor.execute('''
                    SELECT e.key, e.type, e.name, e.first, e.text, e.description, c.group_name
                    FROM entries e
                    JOIN categories c ON e.category_id = c.id
                    WHERE c.name = ?
                    ORDER BY e.key
                ''', (category_name,))
                
                rows = cursor.fetchall()
                for entry in rows:
                    # Definisci group_text qui, prima di qualsiasi logica condizionale
                    group_text = ""
                    
                    key = entry[0]
                    if key.startswith('\\newglossaryentry{'):
                        key = key[len('\\newglossaryentry{'):-1]
                    
                    # Gestione separata del gruppo
                    group_name = entry[6]
                    if group_name is not None:
                        group_name = group_name.strip()
                        if group_name:
                            # Cerca pattern \group{...}
                            match = re.search(r'\\group{(.*?)}', group_name)
                            if match:
                                # Usa il contenuto di \group{...}
                                group_text = f",\n    group={{{match.group(1)}}}"
                            else:
                                # Usa il valore così com'è
                                group_text = f",\n    group={{{group_name}}}"
                    # Genera l'entry LaTeX
                    content += f"""\\newglossaryentry{{{key}}}{{
        type={entry[1]},
        name={{{entry[2]}}},
        first={{{entry[3]}}},
        text={{{entry[4]}}},
        description={{{entry[5]}}}{group_text}
    }}\n\n"""
                
            return content

    def import_from_latex(self, content):
        print("Inizio importazione...")
        sections = content.split("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
        current_category = None
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for i, section in enumerate(sections):
                if not section.strip():
                    continue
                    
                lines = section.strip().split('\n')
                
                for line in lines:
                    if "DEFINIZIONI" in line:
                        current_category = line.replace('%', '').replace('DEFINIZIONI', '').strip()
                        category_id = f"CAT_{os.urandom(4).hex()}"
                        print(f"\nProcesso categoria: {current_category}")
                        
                        # Gestione commento
                        if i + 1 < len(sections):
                            next_lines = sections[i+1].strip().split('\n')
                            if next_lines and next_lines[0].strip().startswith('%'):
                                category_comment = next_lines[0].strip()[1:].strip()
                                print(f"Commento: {category_comment}")
                        
                            cursor.execute('''
                                INSERT OR REPLACE INTO categories 
                                (name, category_id, comment)
                                VALUES (?, ?, ?)
                            ''', (current_category, category_id, category_comment))
                        break
                
                if not lines[0].strip().startswith('% DEFINIZIONI'):
                    cursor.execute('SELECT id FROM categories WHERE name = ?', (current_category,))
                    category_id = cursor.fetchone()[0]
                    group_value = None  
                    
                    pos = 0
                    while True:
                        pos = section.find('\\newglossaryentry', pos)
                        if pos == -1:
                            break
                            
                        entry = parse_glossary_entry(section, pos)
                        if entry:
                            try:
                                # Gestione Gruppo
                                if 'group' in entry:
                                    group_value = entry['group']
                                    # Rimuovi eventuali \group{} esistenti
                                    match = re.search(r'\\group{(.*?)}', group_value)
                                    if match:
                                        group_value = match.group(1)
                                    cursor.execute('''
                                        UPDATE categories 
                                        SET group_name = ?
                                        WHERE id = ?
                                    ''', (group_value, category_id))

                                definition_id = f"DEF_{os.urandom(4).hex()}"
                                cursor.execute('''
                                    INSERT INTO entries (
                                        definition_id, category_id, key, type, name,
                                        first, text, description, is_math
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ''', (
                                    definition_id,
                                    category_id,
                                    entry['key'],
                                    entry['type'] or '\\acronymtype',
                                    entry['name'],
                                    entry['first'],
                                    entry['text'],
                                    entry['description'],
                                    entry.get('is_math', False)
                                ))
                                entry_id = cursor.lastrowid

                                # Formatting Options
                                format_fields = ['name', 'first', 'text']
                                for field in format_fields:
                                    value = entry[field]
                                    
                                    # Controlla prima \textbackslash
                                    has_textbackslash = '\\textbackslash' in value
                                    if has_textbackslash:
                                        format_type = '\\textbackslash'
                                        is_math_mode = True  # \textbackslash implica modalità matematica
                                    else:
                                        is_math = value.startswith('$') and value.endswith('$')
                                        has_textbf = '\\textbf{' in value
                                        has_textit = '\\textit{' in value
                                        has_mathbf = '\\mathbf{' in value
                                        has_mathit = '\\mathit{' in value
                                        
                                        # Aggiungi controllo per first_letter_bold
                                        first_letter_bold = False
                                        if field == 'first':
                                            words = value.split()
                                            if any(word.startswith('\\textbf{') and '}' in word for word in words):
                                                first_letter_bold = True

                                        format_type = 'Normale'
                                        if has_textbf: format_type = '\\textbf{}'
                                        elif has_textit: format_type = '\\textit{}'
                                        elif has_mathbf: format_type = '\\mathbf{}'
                                        elif has_mathit: format_type = '\\mathit{}'

                                    cursor.execute('''
                                        INSERT INTO formatting_options
                                        (entry_id, field_name, format_type, is_math_mode, first_letter_bold)
                                        VALUES (?, ?, ?, ?, ?)
                                    ''', (
                                        entry_id, 
                                        field,
                                        format_type,
                                        is_math_mode if has_textbackslash else is_math,
                                        first_letter_bold
                                    ))
                                print(f"Entry {entry['key']} salvata")
                            except Exception as e:
                                print(f"Errore: {entry['key']} - {str(e)}")
                        pos += 1
                        
            conn.commit()
        print("Importazione completata")
            
    
    