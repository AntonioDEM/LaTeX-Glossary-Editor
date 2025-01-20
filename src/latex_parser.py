import re


def extract_balanced_content(text, start_pos, open_char='{', close_char='}'):
    """
    Estrae il contenuto tra parentesi graffe bilanciate partendo da una posizione data
    Args:
        text (str): Il testo da analizzare
        start_pos (int): La posizione da cui iniziare la ricerca
        open_char (str): Il carattere di apertura (default: '{')
        close_char (str): Il carattere di chiusura (default: '}')
    Returns:
        tuple: (contenuto estratto, posizione finale) o (None, -1) se non trovato
    """
    count = 0
    start = -1
    
    for i in range(start_pos, len(text)):
        if text[i] == open_char:
            if count == 0:
                start = i
            count += 1
        elif text[i] == close_char:
            count -= 1
            if count == 0 and start != -1:
                return text[start + 1:i], i
    
    return None, -1

def extract_field_content(content, field_name):
    """
    Estrae il contenuto di un campo LaTeX, gestendo graffe nidificate e diversi formati
    Args:
        content (str): Il contenuto LaTeX completo
        field_name (str): Il nome del campo da estrarre
    Returns:
        str: Il contenuto del campo o None se non trovato
    """
    # Cerca il campo nel contenuto
    field_pattern = fr'{field_name}\s*=\s*'
    field_start = content.find(field_name + '=')
    if field_start == -1:
        return None
    
    # Salta gli spazi dopo l'uguale
    pos = field_start + len(field_name)
    while pos < len(content) and content[pos] in ['=', ' ', '\t', '\n']:
        pos += 1
    
    if pos >= len(content):
        return None
    
    # Gestisci il caso speciale del type che non usa graffe
    if field_name == 'type':
        end_pos = content.find(',', pos)
        if end_pos == -1:
            end_pos = content.find('}', pos)
        if end_pos == -1:
            return None
        return content[pos:end_pos].strip()
    
    # Per tutti gli altri campi, estrai il contenuto tra graffe
    if content[pos] == '{':
        extracted, _ = extract_balanced_content(content, pos)
        return extracted
    
    return None

def parse_glossary_entry(content, start_pos):
    """
    Analizza una singola definizione del glossario
    Args:
        content (str): Il contenuto LaTeX completo
        start_pos (int): La posizione di inizio della definizione
    Returns:
        dict: Un dizionario con i campi estratti o None se il parsing fallisce
    """
    try:
        # Trova la chiave
        key_start = content.find('{', start_pos)
        if key_start == -1:
            return None
        
        key_content, key_end = extract_balanced_content(content, key_start)
        if not key_content:
            return None
        
        # Trova il contenuto principale
        content_start = content.find('{', key_end)
        if content_start == -1:
            return None
            
        main_content, _ = extract_balanced_content(content, content_start)
        if not main_content:
            return None
        
        # Estrai tutti i campi
        fields = {
            'key': key_content,
            'type': extract_field_content(main_content, 'type'),
            'name': extract_field_content(main_content, 'name'),
            'first': extract_field_content(main_content, 'first'),
            'text': extract_field_content(main_content, 'text'),
            'description': extract_field_content(main_content, 'description')
        }
        
        # Verifica se è in modalità matematica
        is_math = False
        if fields['name']:
            is_math = fields['name'].startswith('$') and fields['name'].endswith('$')
        
        fields['is_math'] = is_math
        return fields
        
    except Exception as e:
        print(f"Errore nel parsing della definizione: {str(e)}")
        return None