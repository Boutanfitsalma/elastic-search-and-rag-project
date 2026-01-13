"""
==============================================================================
LOG PARSER - Mozilla CI Build Logs
==============================================================================
Parse les logs de builds Mozilla CI et extrait toutes les informations
(Niveau 1-4 : Métadonnées, Erreurs, Métriques, Contexte)
==============================================================================
"""

import re
import json
from datetime import datetime
from pathlib import Path


class MozillaCILogParser:
    """Parser pour les logs Mozilla CI"""
    
    def __init__(self):
        """Initialise le parser"""
        self.reset()
    
    def reset(self):
        """Réinitialise l'état du parser"""
        self.parsed_data = {
            'metadata': {},
            'errors': {
                'has_errors': False,
                'error_count': 0,
                'warning_count': 0,
                'errors_list': [],
                'warnings_list': []
            },
            'metrics': {
                'cpu': {},
                'io': {},
                'memory': {},
                'timing': {}
            },
            'context': {
                'sections': [],
                'test_type': None,
                'platform': None,
                'build_type': None
            },
            'raw': {
                'file_name': None,
                'file_size': 0,
                'line_count': 0
            }
        }
    
    def parse_file(self, file_path):
        """
        Parse un fichier de log complet
        
        Args:
            file_path: Chemin vers le fichier .txt
        
        Returns:
            dict: Données parsées (niveau 1-4)
        """
        self.reset()
        
        file_path = Path(file_path)
        
        # Métadonnées du fichier
        self.parsed_data['raw']['file_name'] = file_path.name
        self.parsed_data['raw']['file_size'] = file_path.stat().st_size
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            self.parsed_data['raw']['line_count'] = len(lines)
            
            # Parser le header (20 premières lignes)
            self._parse_header(lines[:20])
            
            # Parser le contenu complet
            self._parse_content(lines)
            
            # Calculer des métriques dérivées
            self._calculate_derived_metrics()
            
            return self.parsed_data
        
        except Exception as e:
            self.parsed_data['parse_error'] = str(e)
            return self.parsed_data
    
    def _parse_header(self, header_lines):
        """
        Parse le header du log (NIVEAU 1 - Métadonnées)
        
        Args:
            header_lines: Liste des premières lignes
        """
        for line in header_lines:
            if ':' not in line or line.startswith('='):
                continue
            
            parts = line.split(':', 1)
            if len(parts) != 2:
                continue
            
            key = parts[0].strip()
            value = parts[1].strip()
            
            # Champs métadonnées principaux
            if key == 'builder':
                self.parsed_data['metadata']['builder'] = value
                self._extract_context_from_builder(value)
            elif key == 'slave':
                self.parsed_data['metadata']['slave'] = value
            elif key == 'starttime':
                self.parsed_data['metadata']['starttime'] = value
                self.parsed_data['metadata']['starttime_iso'] = self._convert_unix_to_iso(value)
            elif key == 'results':
                self._parse_results(value)
            elif key == 'buildid':
                self.parsed_data['metadata']['buildid'] = value
            elif key == 'builduid':
                self.parsed_data['metadata']['builduid'] = value
            elif key == 'revision':
                self.parsed_data['metadata']['revision'] = value
    
    def _parse_results(self, results_str):
        """
        Parse le champ results (ex: "success (0)", "failure (2)")
        
        Args:
            results_str: String du résultat
        """
        self.parsed_data['metadata']['results_raw'] = results_str
        
        # Extraire le statut et le code
        match = re.match(r'(\w+)\s*\((\d+)\)', results_str)
        if match:
            self.parsed_data['metadata']['result_status'] = match.group(1)
            self.parsed_data['metadata']['result_code'] = int(match.group(2))
        else:
            self.parsed_data['metadata']['result_status'] = results_str
            self.parsed_data['metadata']['result_code'] = None
    
    def _extract_context_from_builder(self, builder_name):
        """
        Extrait des informations contextuelles du nom du builder
        (NIVEAU 4 - Contexte)
        
        Args:
            builder_name: Nom du builder (ex: mozilla-esr52_ubuntu64_vm_test_pgo-xpcshell)
        """
        # Platform
        if 'ubuntu' in builder_name or 'linux' in builder_name:
            self.parsed_data['context']['platform'] = 'linux'
        elif 'win' in builder_name or 'xp' in builder_name:
            self.parsed_data['context']['platform'] = 'windows'
        elif 'mac' in builder_name or 'yosemite' in builder_name:
            self.parsed_data['context']['platform'] = 'mac'
        
        # Architecture
        if 'x64' in builder_name or '64' in builder_name:
            self.parsed_data['context']['architecture'] = '64bit'
        elif '32' in builder_name:
            self.parsed_data['context']['architecture'] = '32bit'
        
        # Build type
        if 'debug' in builder_name:
            self.parsed_data['context']['build_type'] = 'debug'
        elif 'pgo' in builder_name:
            self.parsed_data['context']['build_type'] = 'pgo'
        
        # Test type
        test_types = ['xpcshell', 'mochitest', 'reftest', 'web-platform-tests', 
                      'crashtest', 'jsreftest', 'cppunit', 'gtest', 'marionette']
        for test_type in test_types:
            if test_type in builder_name:
                self.parsed_data['context']['test_type'] = test_type
                break
    
    def _parse_content(self, lines):
        """
        Parse le contenu complet du log
        (NIVEAU 2 - Erreurs, NIVEAU 3 - Métriques, NIVEAU 4 - Contexte)
        
        Args:
            lines: Toutes les lignes du fichier
        """
        current_section = None
        section_start_time = None
        
        for line in lines:
            # Détecter les sections (NIVEAU 4)
            if 'Started' in line and '=========' in line:
                section_match = re.search(r"Started\s+(.+?)\s+\(results", line)
                if section_match:
                    section_name = section_match.group(1).strip()
                    current_section = section_name
                    
                    # Extraire le timestamp de début
                    time_match = re.search(r'at\s+([\d-]+\s+[\d:]+)', line)
                    if time_match:
                        section_start_time = time_match.group(1)
            
            # Section terminée
            if 'Finished' in line and '=========' in line and current_section:
                # Extraire le temps écoulé
                elapsed_match = re.search(r'elapsed:\s+([\d\s\w,]+)', line)
                if elapsed_match:
                    elapsed = elapsed_match.group(1).strip()
                    
                    self.parsed_data['context']['sections'].append({
                        'name': current_section,
                        'start_time': section_start_time,
                        'elapsed': elapsed
                    })
                
                current_section = None
                section_start_time = None
            
            # Détecter les erreurs (NIVEAU 2)
            if re.search(r'\bERROR\b', line, re.IGNORECASE):
                self.parsed_data['errors']['has_errors'] = True
                self.parsed_data['errors']['error_count'] += 1
                
                # Extraire le message d'erreur
                error_info = {
                    'line': line.strip(),
                    'timestamp': self._extract_timestamp_from_line(line)
                }
                
                self.parsed_data['errors']['errors_list'].append(error_info)
            
            # Détecter les warnings (NIVEAU 2)
            if re.search(r'\bWARNING\b', line, re.IGNORECASE):
                self.parsed_data['errors']['warning_count'] += 1
                
                warning_info = {
                    'line': line.strip(),
                    'timestamp': self._extract_timestamp_from_line(line)
                }
                
                self.parsed_data['errors']['warnings_list'].append(warning_info)
            
            # Extraire les métriques CPU (NIVEAU 3)
            cpu_match = re.search(r'CPU\s+(idle|system|user)[<br/>]*(\d+\.?\d*)', line, re.IGNORECASE)
            if cpu_match:
                metric_name = cpu_match.group(1).lower()
                metric_value = float(cpu_match.group(2))
                self.parsed_data['metrics']['cpu'][f'{metric_name}'] = metric_value
            
            # Extraire les métriques I/O (NIVEAU 3)
            io_match = re.search(r'I/O\s+(read|write)\s+bytes.*?(\d+)', line, re.IGNORECASE)
            if io_match:
                operation = io_match.group(1).lower()
                value = int(io_match.group(2))
                self.parsed_data['metrics']['io'][f'{operation}_bytes'] = value
            
            # Extraire elapsed time
            elapsed_match = re.search(r'elapsedTime=([\d.]+)', line)
            if elapsed_match:
                elapsed_time = float(elapsed_match.group(1))
                if 'elapsed_times' not in self.parsed_data['metrics']['timing']:
                    self.parsed_data['metrics']['timing']['elapsed_times'] = []
                self.parsed_data['metrics']['timing']['elapsed_times'].append(elapsed_time)
    
    def _calculate_derived_metrics(self):
        """
        Calcule des métriques dérivées
        """
        # Durée totale du build
        if 'elapsed_times' in self.parsed_data['metrics']['timing']:
            elapsed_times = self.parsed_data['metrics']['timing']['elapsed_times']
            if elapsed_times:
                self.parsed_data['metrics']['timing']['total_duration'] = sum(elapsed_times)
                self.parsed_data['metrics']['timing']['max_step_duration'] = max(elapsed_times)
        
        # Taux d'erreur
        if self.parsed_data['raw']['line_count'] > 0:
            error_rate = (self.parsed_data['errors']['error_count'] / 
                         self.parsed_data['raw']['line_count']) * 100
            self.parsed_data['errors']['error_rate_percent'] = round(error_rate, 2)
    
    def _extract_timestamp_from_line(self, line):
        """
        Extrait un timestamp d'une ligne
        
        Args:
            line: Ligne de log
        
        Returns:
            str: Timestamp ou None
        """
        # Format complet
        match = re.search(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', line)
        if match:
            return match.group(0)
        
        # Format court
        match = re.search(r'\d{2}:\d{2}:\d{2}', line)
        if match:
            return match.group(0)
        
        return None
    
    def _convert_unix_to_iso(self, unix_timestamp_str):
        """
        Convertit un Unix timestamp en ISO 8601
        
        Args:
            unix_timestamp_str: String du timestamp Unix
        
        Returns:
            str: ISO timestamp ou None
        """
        try:
            unix_ts = float(unix_timestamp_str)
            dt = datetime.fromtimestamp(unix_ts)
            return dt.isoformat()
        except:
            return None
    
    def to_json(self, indent=2):
        """
        Convertit les données parsées en JSON
        
        Args:
            indent: Indentation JSON
        
        Returns:
            str: JSON string
        """
        return json.dumps(self.parsed_data, indent=indent, ensure_ascii=False)
    
    def save_to_file(self, output_path):
        """
        Sauvegarde les données parsées dans un fichier JSON
        
        Args:
            output_path: Chemin du fichier de sortie
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())


def parse_log_file(file_path):
    """
    Fonction helper pour parser un fichier rapidement
    
    Args:
        file_path: Chemin vers le fichier .txt
    
    Returns:
        dict: Données parsées
    """
    parser = MozillaCILogParser()
    return parser.parse_file(file_path)


# ============================================================================
# EXEMPLE D'UTILISATION
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python log_parser.py <fichier.txt>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    print(f"🔍 Parsing de: {file_path}")
    print()
    
    # Parser le fichier
    parser = MozillaCILogParser()
    data = parser.parse_file(file_path)
    
    # Afficher un résumé
    print("=" * 80)
    print("📊 RÉSUMÉ DU PARSING")
    print("=" * 80)
    print()
    
    print("📄 MÉTADONNÉES (Niveau 1)")
    print(f"  Builder: {data['metadata'].get('builder', 'N/A')}")
    print(f"  Result: {data['metadata'].get('result_status', 'N/A')}")
    print(f"  Start time: {data['metadata'].get('starttime_iso', 'N/A')}")
    print()
    
    print("❌ ERREURS (Niveau 2)")
    print(f"  Has errors: {data['errors']['has_errors']}")
    print(f"  Error count: {data['errors']['error_count']}")
    print(f"  Warning count: {data['errors']['warning_count']}")
    print()
    
    print("📊 MÉTRIQUES (Niveau 3)")
    if data['metrics']['cpu']:
        print(f"  CPU: {data['metrics']['cpu']}")
    if data['metrics']['io']:
        print(f"  I/O: {data['metrics']['io']}")
    if data['metrics']['timing']:
        print(f"  Timing: {data['metrics']['timing']}")
    print()
    
    print("🎯 CONTEXTE (Niveau 4)")
    print(f"  Platform: {data['context'].get('platform', 'N/A')}")
    print(f"  Test type: {data['context'].get('test_type', 'N/A')}")
    print(f"  Sections count: {len(data['context']['sections'])}")
    print()
    
    # Sauvegarder en JSON
    output_file = file_path.replace('.txt', '_parsed.json')
    parser.save_to_file(output_file)
    print(f"💾 Sauvegardé dans: {output_file}")