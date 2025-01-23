import sqlite3
from datetime import datetime
from .latex_parser import parse_glossary_entry  # Aggiunto il punto per l'importazione relativa
from .glossary_os_handler import GlossaryOSHandler

class GlossaryDatabase:
    def __init__(self, db_path=None):
        self.os_handler = GlossaryOSHandler()
        self.os_handler.ensure_directories_exist()
        self.db_path = db_path or self.os_handler.get_database_path()
        self._create_database()
    
    def _create_database(self):
        """Crea o aggiorna lo schema del database"""
        print("Creo/verifico il database...")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Crea tabella categorie
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Controlla se la colonna comment esiste
            cursor.execute("PRAGMA table_info(categories)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Aggiungi la colonna comment se non esiste
            if 'comment' not in columns:
                print("Aggiorno la struttura del database: aggiungo colonna comment...")
                cursor.execute('ALTER TABLE categories ADD COLUMN comment TEXT')
            
            # Crea tabella entries
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER,
                    key TEXT NOT NULL,
                    type TEXT NOT NULL DEFAULT '\\acronymtype',
                    name TEXT NOT NULL,
                    first TEXT NOT NULL,
                    text TEXT NOT NULL,
                    description TEXT,
                    group_name TEXT,
                    is_math BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(id),
                    UNIQUE(category_id, key)
                )
            ''')
            # Controlla se la colonna group_name esiste
            cursor.execute("PRAGMA table_info(entries)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Aggiungi la colonna group_name se non esiste
            if 'group_name' not in columns:
                print("Aggiorno la struttura del database: aggiungo colonna group_name...")
                cursor.execute('ALTER TABLE entries ADD COLUMN group_name TEXT')

            # Crea tabella formatting_options
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
            
            # Inserisce categoria "Generale" di default
            cursor.execute('INSERT OR IGNORE INTO categories (name) VALUES ("Generale")')
            
            conn.commit()
            print("Database creato/verificato correttamente")
    
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
            
            cursor.execute('''
                SELECT c.name, c.comment 
                FROM categories c
                WHERE c.name != "Generale" 
                ORDER BY c.name
            ''')
            
            for category_name, comment in cursor.fetchall():
                content += "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n"
                content += f"% DEFINIZIONI {category_name}\n"
                content += "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n"
                
                if comment and comment.strip():
                    content += f"% {comment}\n"
                
                content += "\n"
                
                cursor.execute('''
                    SELECT e.key, e.type, e.name, e.first, e.text, e.description, e.group_name
                    FROM entries e
                    JOIN categories c ON e.category_id = c.id
                    WHERE c.name = ?
                    ORDER BY e.key
                ''', (category_name,))
                
                for entry in cursor.fetchall():
                    key = entry[0]
                    if key.startswith('\\newglossaryentry{'):
                        key = key[len('\\newglossaryentry{'):-1]
                    if entry[6]:  # Se c'è un gruppo
                        # Estrai il valore del gruppo rimuovendo \group{}
                        group_value = entry[6]
                        if group_value.startswith('\\group{') and group_value.endswith('}'):
                            group_value = group_value[7:-1]  # Rimuove \group{ e }
                        content += f"""\\newglossaryentry{{{key}}}{{
        type={entry[1]},
        name={{{entry[2]}}},
        first={{{entry[3]}}},
        text={{{entry[4]}}},
        description={{{entry[5]}}},
        group={{{group_value}}}
    }}\n\n"""
                    else:  # Se non c'è gruppo
                        content += f"""\\newglossaryentry{{{key}}}{{
        type={entry[1]},
        name={{{entry[2]}}},
        first={{{entry[3]}}},
        text={{{entry[4]}}},
        description={{{entry[5]}}}
    }}\n\n"""
                
            return content

    def import_from_latex(self, content):
        """Importa definizioni da contenuto LaTeX"""
        print("Inizio importazione...")
        sections = content.split("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
        current_category = "Generale"
        category_comment = None
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for i, section in enumerate(sections):
                if not section.strip():
                    continue
                    
                lines = section.strip().split('\n')
                
                for line in lines:
                    if "DEFINIZIONI" in line:
                        current_category = line.replace('%', '').replace('DEFINIZIONI', '').strip()
                        print(f"\nProcesso categoria: {current_category}")
                        
                        if i + 1 < len(sections):
                            next_lines = sections[i+1].strip().split('\n')
                            if next_lines and next_lines[0].strip().startswith('%'):
                                category_comment = next_lines[0].strip()[1:].strip()
                                print(f"Commento trovato per {current_category}: {category_comment}")
                        
                        cursor.execute('SELECT id FROM categories WHERE name = ?', (current_category,))
                        exists = cursor.fetchone()
                        
                        if exists:
                            cursor.execute('''
                                UPDATE categories 
                                SET comment = ?
                                WHERE name = ?
                            ''', (category_comment, current_category))
                        else:
                            cursor.execute('''
                                INSERT INTO categories (name, comment) 
                                VALUES (?, ?)
                            ''', (current_category, category_comment))
                        
                        category_comment = None
                        break
                
                if not lines[0].strip().startswith('% DEFINIZIONI'):
                    cursor.execute('SELECT id FROM categories WHERE name = ?', (current_category,))
                    category_id = cursor.fetchone()[0]
                    
                    pos = 0
                    while True:
                        pos = section.find('\\newglossaryentry', pos)
                        if pos == -1:
                            break
                        
                        entry = parse_glossary_entry(section, pos)
                        if entry:
                            try:
                                cursor.execute('''
                                    INSERT OR REPLACE INTO entries 
                                    (category_id, key, type, name, first, text, description, group_name, is_math)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ''', (
                                    category_id,
                                    entry['key'],
                                    entry['type'] or '\\acronymtype',
                                    entry['name'],
                                    entry['first'],
                                    entry['text'],
                                    entry['description'],
                                    entry.get('group', ''),
                                    entry['is_math']
                                ))
                                print(f"Entry {entry['key']} salvata con successo")
                            except Exception as e:
                                print(f"Errore nel salvare {entry['key']}: {e}")
                        pos += 1
                    
            conn.commit()
            print("Importazione completata")
            
    
    