import sqlite3
from .glossary_os_handler import GlossaryOSHandler

class DatabaseManager:
    _instance = None  # Corrected from _instancee

    def __new__(cls, db_path=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            if db_path is None:
                os_handler = GlossaryOSHandler()
                os_handler.ensure_directories_exist()
                db_path = os_handler.get_database_path()
            cls._instance.db_path = db_path
            cls._instance.conn = None
            cls._instance.cursor = None
        elif db_path is not None and cls._instance.db_path != db_path:
            # Se viene fornito un nuovo path diverso, aggiorna la connessione
            print(f"Aggiornamento path database da {cls._instance.db_path} a {db_path}")  # Debug
            if cls._instance.conn:
                cls._instance.conn.close()
            cls._instance.db_path = db_path
            cls._instance.conn = None
            cls._instance.cursor = None
        return cls._instance
    
    def connect(self):
        """Crea una connessione al database se non esiste già"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
    
    def execute(self, query, params=None):
        """Esegue una query SQL"""
        try:
            # Assicuriamoci di avere una connessione prima di eseguire la query
            self.connect()  # Aggiungiamo questa riga
            
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return self.cursor
        except sqlite3.Error as e:
            print(f"Errore nell'esecuzione della query: {str(e)}")
            raise
    
    def commit(self):
        """Esegue il commit delle modifiche"""
        if self.conn:
            self.conn.commit()
    
    def close(self):
        """Chiude la connessione al database"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
    
    def begin_transaction(self):
        """Inizia una transazione"""
        self.execute("BEGIN IMMEDIATE")
    
    def end_transaction(self):
        """Termina una transazione con commit"""
        self.commit()
            
    def rollback(self):
        """Esegue il rollback di una transazione"""
        if self.conn:
            self.conn.rollback()
    
    def delete_entry(self, category, key):
        """Elimina una definizione e tutte le sue opzioni di formattazione"""
        try:
            # Inizia la transazione
            self.execute("BEGIN IMMEDIATE")
            
            # Prima ottieni l'ID dell'entry
            cursor = self.execute('''
                SELECT e.id 
                FROM entries e
                JOIN categories c ON e.category_id = c.id
                WHERE c.name = ? AND e.key = ?
            ''', (category, key))
            
            result = cursor.fetchone()
            if not result:
                self.rollback()
                return False
                
            entry_id = result[0]
            
            # Elimina le opzioni di formattazione
            self.execute('''
                DELETE FROM formatting_options 
                WHERE entry_id = ?
            ''', (entry_id,))
            
            # Elimina l'entry
            self.execute('''
                DELETE FROM entries 
                WHERE id = ?
            ''', (entry_id,))
            
            # Commit della transazione
            self.commit()
            return True
            
        except sqlite3.Error as e:
            print(f"Errore durante l'eliminazione: {str(e)}")
            self.rollback()
            raise

    def get_category_comment(self, category_name):
        """Recupera il commento di una categoria"""
        try:
            cursor = self.execute(
                'SELECT comment FROM categories WHERE name = ?',
                (category_name,)
            )
            result = cursor.fetchone()
            if result:
                print(f"Debug - Commento recuperato per {category_name}: {result[0]}")
                return result[0]
            else:
                print(f"Debug - Nessun commento trovato per {category_name}")
                return ""
        except sqlite3.Error as e:
            print(f"Errore nel recupero del commento: {str(e)}")
            return ""

    def fetch_all_categories(self):
        """Recupera tutte le categorie dal database"""
        try:
            cursor = self.execute('SELECT name FROM categories')
            categories = cursor.fetchall()
            print(f"Debug - Categorie disponibili: {[category[0] for category in categories]}")
            return [category[0] for category in categories]
        except sqlite3.Error as e:
            print(f"Errore nel recupero delle categorie: {str(e)}")
            return []

    def save_category_comment(self, category_name, comment):
        """Salva il commento di una categoria"""
        try:
            self.execute(
                'UPDATE categories SET comment = ? WHERE name = ?',
                (comment, category_name)
            )
            self.commit()
            print(f"Debug - Commento salvato per {category_name}: {comment}")
            return True
        except sqlite3.Error as e:
            print(f"Errore nel salvataggio del commento: {str(e)}")
            return False

    def add_category(self, name, comment=None):
        """Aggiunge una nuova categoria con commento opzionale"""
        try:
            self.execute(
                'INSERT INTO categories (name, comment) VALUES (?, ?)', 
                (name, comment)
            )
            self.commit()
            return True
        except sqlite3.IntegrityError:
            print(f"Errore: la categoria {name} esiste già")
            return False
        except sqlite3.Error as e:
            print(f"Errore database: {e}")
            return False
            
    def __enter__(self):
        """Gestisce l'inizio di un blocco with"""
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Gestisce la fine di un blocco with"""
        if exc_type is None:
            self.commit()
        else:
            if self.conn:
                self.conn.rollback()
        # Non chiudiamo la connessione qui per mantenerla attiva