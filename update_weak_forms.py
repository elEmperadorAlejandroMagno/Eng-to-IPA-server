#!/usr/bin/env python3
"""
Script para actualizar la base de datos SQLite con formas weak/strong
para RP en el formato / [strong], [weak] /
"""
import sqlite3
import os

# Diccionario de palabras con formas weak/strong para RP
WEAK_STRONG_FORMS = {
    # ARTÍCULOS
    "a": "/ eɪ, ə /",
    "an": "/ æn, ən /",
    
    # AUXILIARES - BE
    "am": "/ æm, əm /",
    "is": "/ ɪz, s /",
    "are": "/ ɑː, ə /",
    "was": "/ wɒz, wəz /",
    "were": "/ wɜː, wə /",
    
    # AUXILIARES - HAVE
    "have": "/ hæv, əv /",
    "has": "/ hæz, əz /",
    "had": "/ hæd, əd /",
    
    # AUXILIARES - DO
    "do": "/ duː, də /",
    
    # PREPOSICIONES
    "of": "/ ɒv, əv /",
    "to": "/ tuː, tə /",
    "for": "/ fɔː, fə /",
    "from": "/ frɒm, frəm /",
    "at": "/ æt, ət /",
    
    # CONJUNCIONES
    "and": "/ ænd, ən /",
    
    # PRONOMBRES
    "you": "/ juː, jə /",
    "he": "/ hiː, hi /",
    "she": "/ ʃiː, ʃi /",
    "we": "/ wiː, wi /",
    "me": "/ miː, mi /",
    "him": "/ hɪm, ɪm /",
    "her": "/ hɜː, hə /",
    "us": "/ ʌs, əs /",
    "them": "/ ðem, ðəm /",
    
    # PALABRAS COMUNES
    "that": "/ ðæt, ðət /",
    "there": "/ ðeə, ðə /",
    
    # MODALES
    "will": "/ wɪl, əl /",
    "would": "/ wʊd, əd /",
    "can": "/ kæn, kən /",
    "must": "/ mʌst, məst /",
}

def main():
    # Path a la base de datos
    db_path = os.path.join(os.path.dirname(__file__), 'app', 'ipa_en.sqlite')
    
    if not os.path.exists(db_path):
        print(f"Base de datos no encontrada: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    print("Actualizando formas weak/strong para RP...")
    
    updated_count = 0
    for word, rp_form in WEAK_STRONG_FORMS.items():
        # Actualizar la columna 'gb' (British) con el formato weak/strong
        cur.execute("UPDATE ipa SET gb = ? WHERE word = ?", (rp_form, word))
        
        if cur.rowcount > 0:
            updated_count += 1
            print(f"Actualizado: {word} -> {rp_form}")
        else:
            # Si la palabra no existe, insertarla
            cur.execute("INSERT OR IGNORE INTO ipa(word, us, gb) VALUES (?, NULL, ?)", (word, rp_form))
            if cur.rowcount > 0:
                updated_count += 1
                print(f"Insertado: {word} -> {rp_form}")
    
    conn.commit()
    conn.close()
    
    print(f"\nActualización completada. {updated_count} palabras modificadas.")
    print("Las formas weak/strong están ahora disponibles en formato RP.")

if __name__ == '__main__':
    main()