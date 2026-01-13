"""
==============================================================================
SCRIPT D'EXTRACTION DES FICHIERS .RAR
==============================================================================
Extrait automatiquement tous les fichiers .rar du dossier data/raw/
et les place dans data/extracted/day_XX/

Auteur: Mozilla CI Log Analysis Project
Date: 2024
==============================================================================
"""
import shutil
import stat
import os
import rarfile
import sys
from pathlib import Path
import re


# ============================================================================
# CONFIGURATION
# ============================================================================

# Chemins
BASE_DIR = Path(__file__).parent.parent  # Racine du projet
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
EXTRACTED_DATA_DIR = BASE_DIR / "data" / "extracted"

print("=" * 80)
print("🔓 EXTRACTION DES FICHIERS .RAR")
print("=" * 80)
print()
print(f"📁 Dossier source: {RAW_DATA_DIR}")
print(f"📁 Dossier destination: {EXTRACTED_DATA_DIR}")
print()

# ============================================================================
# VÉRIFICATIONS
# ============================================================================

# Vérifier que le dossier raw existe
if not RAW_DATA_DIR.exists():
    print(f"❌ ERREUR: Le dossier {RAW_DATA_DIR} n'existe pas!")
    print("   Créez-le et placez-y vos fichiers .rar")
    sys.exit(1)

# Créer le dossier extracted s'il n'existe pas
EXTRACTED_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Trouver tous les fichiers .rar
rar_files = sorted(list(RAW_DATA_DIR.glob("*.rar")))

if not rar_files:
    print(f"❌ ERREUR: Aucun fichier .rar trouvé dans {RAW_DATA_DIR}")
    sys.exit(1)

print(f"✅ {len(rar_files)} fichier(s) .rar trouvé(s)")
print()

# ============================================================================
# FONCTION D'EXTRACTION
# ============================================================================

def extract_rar_file(rar_path):
    """
    Extrait un fichier .rar dans le dossier approprié
    
    Args:
        rar_path: Chemin vers le fichier .rar
    
    Returns:
        tuple: (success, day_number, file_count)
    """
    try:
        # Extraire le numéro du jour depuis le nom du fichier
        # Formats possibles: log-2018-06-01.rar, log-2018-06-19.rar
        filename = rar_path.name
        
        # Chercher la date dans le nom
        date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', filename)
        
        if date_match:
            day = int(date_match.group(3))  # Jour (01, 02, ..., 20)
        else:
            # Fallback: essayer d'extraire juste un nombre
            num_match = re.search(r'(\d+)', filename)
            if num_match:
                day = int(num_match.group(1))
            else:
                print(f"⚠️  Impossible d'extraire le jour de: {filename}")
                return False, None, 0
        
        # Créer le nom du dossier de destination
        day_folder = EXTRACTED_DATA_DIR / f"day_{day:02d}"
        
        # Créer le dossier s'il n'existe pas
        day_folder.mkdir(parents=True, exist_ok=True)
        
        print(f"📦 Extraction de: {filename}")
        print(f"   → Destination: {day_folder}")
        
        # Ouvrir et extraire le .rar
        with rarfile.RarFile(rar_path) as rf:
            # Lister tous les fichiers
            all_files = rf.namelist()
            txt_files = [f for f in all_files if f.endswith('.txt')]
            
            print(f"   📊 {len(txt_files)} fichiers .txt trouvés")
            
            # Extraire tous les fichiers dans un dossier temporaire
            temp_folder = day_folder / "temp"
            temp_folder.mkdir(exist_ok=True)
            rf.extractall(temp_folder)
            
            # Déplacer tous les fichiers .txt vers day_folder (sans la structure)
            import shutil
            for txt_file in temp_folder.rglob("*.txt"):
                shutil.move(str(txt_file), str(day_folder / txt_file.name))
            
            # Supprimer le dossier temporaire (gérer fichiers en lecture seule)
            def _on_rm_error(func, path, exc_info):
                try:
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                except Exception:
                    try:
                        if os.path.isdir(path):
                            for root, dirs, files in os.walk(path, topdown=False):
                                for name in files:
                                    fp = os.path.join(root, name)
                                    try:
                                        os.chmod(fp, stat.S_IWRITE)
                                        os.remove(fp)
                                    except Exception:
                                        pass
                                for name in dirs:
                                    dp = os.path.join(root, name)
                                    try:
                                        os.chmod(dp, stat.S_IWRITE)
                                        os.rmdir(dp)
                                    except Exception:
                                        pass
                            try:
                                os.rmdir(path)
                            except Exception:
                                pass
                        else:
                            try:
                                os.remove(path)
                            except Exception:
                                pass
                    except Exception:
                        pass

            shutil.rmtree(temp_folder, onerror=_on_rm_error)
            
            # Compter les fichiers extraits
            extracted_count = len(list(day_folder.glob("*.txt")))
            
            print(f"   ✅ {extracted_count} fichiers extraits")
            print()
            
            return True, day, extracted_count
    
    except rarfile.BadRarFile:
        print(f"   ❌ ERREUR: Fichier .rar corrompu")
        print()
        return False, None, 0
    
    except Exception as e:
        print(f"   ❌ ERREUR: {str(e)}")
        print()
        return False, None, 0

# ============================================================================
# EXTRACTION EN MASSE
# ============================================================================

print("-" * 80)
print("🚀 DÉMARRAGE DE L'EXTRACTION")
print("-" * 80)
print()

# Statistiques
total_files_extracted = 0
successful_extractions = 0
failed_extractions = 0
days_extracted = []

# Extraire chaque fichier .rar
for i, rar_path in enumerate(rar_files, 1):
    print(f"[{i}/{len(rar_files)}] ", end="")
    
    success, day, count = extract_rar_file(rar_path)
    
    if success:
        successful_extractions += 1
        total_files_extracted += count
        if day:
            days_extracted.append(day)
    else:
        failed_extractions += 1

# ============================================================================
# RAPPORT FINAL
# ============================================================================

print("=" * 80)
print("📊 RAPPORT D'EXTRACTION")
print("=" * 80)
print()

print(f"✅ Extractions réussies: {successful_extractions}/{len(rar_files)}")
print(f"❌ Extractions échouées: {failed_extractions}/{len(rar_files)}")
print(f"📄 Total de fichiers .txt extraits: {total_files_extracted:,}")
print()

if days_extracted:
    days_extracted_sorted = sorted(days_extracted)
    print(f"📅 Jours extraits: {min(days_extracted_sorted)} → {max(days_extracted_sorted)}")
    print(f"   ({len(days_extracted_sorted)} jours)")
    print()

print("📁 Structure créée:")
print(f"   {EXTRACTED_DATA_DIR}/")
for day in sorted(days_extracted):
    day_folder = EXTRACTED_DATA_DIR / f"day_{day:02d}"
    txt_count = len(list(day_folder.rglob("*.txt")))
    print(f"   ├── day_{day:02d}/  ({txt_count:,} fichiers .txt)")
print()

print("=" * 80)
print("🎉 EXTRACTION TERMINÉE AVEC SUCCÈS!")
print("=" * 80)
print()

print("💡 Prochaine étape:")
print("   Vous pouvez maintenant lancer le parser sur ces fichiers")
print()

# ============================================================================
# VÉRIFICATION FINALE
# ============================================================================

# Compter le total de fichiers .txt
total_txt_files = len(list(EXTRACTED_DATA_DIR.rglob("*.txt")))
print(f"🔍 Vérification finale: {total_txt_files:,} fichiers .txt accessibles")
print()

if total_txt_files == 0:
    print("⚠️  ATTENTION: Aucun fichier .txt n'a été extrait!")
    print("   Vérifiez que vos fichiers .rar contiennent bien des fichiers .txt")
else:
    print("✅ Tout est prêt pour le parsing!")
