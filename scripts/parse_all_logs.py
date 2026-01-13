"""
Parser tous les fichiers .txt et sauvegarder en JSON
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser.log_parser import MozillaCILogParser
import json

# Config
EXTRACTED_DIR = Path(__file__).parent.parent / "data" / "extracted"
PARSED_DIR = Path(__file__).parent.parent / "data" / "parsed"

print("🚀 PARSING EN MASSE")
print(f"Source: {EXTRACTED_DIR}")
print(f"Destination: {PARSED_DIR}")
print()

# Trouver tous les fichiers
all_files = list(EXTRACTED_DIR.rglob("*.txt"))
total = len(all_files)
print(f"📄 {total:,} fichiers à parser")
print()

# Parser
parser = MozillaCILogParser()
success = 0
failed = 0

for i, file_path in enumerate(all_files, 1):
    if i % 100 == 0:
        print(f"[{i}/{total}] {success} OK, {failed} KO")
    
    try:
        # Parser
        data = parser.parse_file(file_path)
        
        # Sauvegarder
        day_folder = file_path.parent.name  # day_01, day_02, etc
        output_dir = PARSED_DIR / day_folder
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / file_path.name.replace('.txt', '.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        
        success += 1
    except Exception as e:
        failed += 1

print()
print(f"✅ Terminé: {success} OK, {failed} KO")
print(f"📁 Fichiers dans: {PARSED_DIR}")