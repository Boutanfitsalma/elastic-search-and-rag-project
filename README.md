# 🦊 Mozilla CI Log Analysis - Système RAG Sémantique

> Analyse intelligente de logs CI/CD avec pipeline temps réel (Kafka + Elasticsearch + RAG)

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Kafka](https://img.shields.io/badge/Kafka-3.7.0-black.svg)](https://kafka.apache.org/)
[![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.11.0-yellow.svg)](https://www.elastic.co/)
[![Mistral](https://img.shields.io/badge/LLM-Mistral_7B-purple.svg)](https://mistral.ai/)

---
## 📚 Documentation 

- [Rapport technique complet](elkk (1).pdf)
- [Slides de présentation](presentation.pdf)
- [Notebook d'exploration](Log_Analyzer_Colab.ipynb)

## 📋 Table des Matières

- [Vue d'ensemble](#-vue-densemble)
- [Architecture](#-architecture)
- [Prérequis](#-prérequis)
- [Installation](#-installation)
- [Utilisation](#-utilisation)
- [Structure du Projet](#-structure-du-projet)
- [Technologies](#-technologies)
- [Résultats](#-résultats)
- [Auteur](#-auteur)

---

## 🎯 Vue d'ensemble

Ce projet implémente un système complet d'analyse intelligente de logs CI/CD Mozilla combinant :

- **Pipeline temps réel** : Kafka pour l'ingestion streaming
- **Double indexation** : Elasticsearch pour visualisation (Kibana) et recherche sémantique (RAG)
- **Intelligence artificielle** : RAG avec embeddings (Sentence-BERT) + LLM local (Mistral 7B)
- **Interface conversationnelle** : Chatbot Streamlit en langage naturel

### Innovations

✅ **Recherche hybride** : Combine kNN (sémantique) + BM25 (mots-clés)  
✅ **Filtres automatiques** : Détection intelligente de plateforme/statut  
✅ **Agrégations ES** : Calculs globaux quand le RAG ne suffit pas  
✅ **Anti-hallucination** : Prompt engineering strict pour éviter les inventions  

---

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────┐     ┌───────────┐
│  Logs RAR   │────▶│  Parser  │────▶│   Kafka   │
│  (20 jours) │     │ (Python) │     │  (Topic)  │
└─────────────┘     └──────────┘     └─────┬─────┘
                                            │
                    ┌───────────────────────┴───────────────────┐
                    │                                           │
            ┌───────▼────────┐                      ┌──────────▼─────────┐
            │  Consumer 1    │                      │   Consumer 2       │
            │  (Standard)    │                      │   (Semantic)       │
            └───────┬────────┘                      └──────────┬─────────┘
                    │                                           │
            ┌───────▼────────┐                      ┌──────────▼─────────┐
            │ Elasticsearch  │                      │  Elasticsearch     │
            │ Index: kibana  │                      │ Index: semantic-v2 │
            └───────┬────────┘                      │ + Embeddings 384D  │
                    │                               └──────────┬─────────┘
            ┌───────▼────────┐                               │
            │    Kibana      │                      ┌────────▼──────────┐
            │  (Dashboards)  │                      │   RAG Engine      │
            └────────────────┘                      │ (Sentence-BERT +  │
                                                    │  Mistral LLM)     │
                                                    └────────┬──────────┘
                                                            │
                                                    ┌───────▼──────────┐
                                                    │  Streamlit UI    │
                                                    │   (Chatbot)      │
                                                    └──────────────────┘
```

### Flux de données

1. **Extraction** : Décompression de 20 fichiers RAR (~500k logs)
2. **Parsing** : Extraction 4 niveaux (métadonnées, erreurs, métriques, contexte)
3. **Streaming** : Envoi vers Kafka topic `mozilla-builds`
4. **Double consommation** :
   - Consumer 1 → Index Kibana (visualisation)
   - Consumer 2 → Index RAG (avec embeddings)
5. **Exploitation** :
   - Kibana : Dashboards interactifs
   - RAG : Interrogation en langage naturel

---

## 🔧 Prérequis

### Logiciels

- **Python** 3.8+
- **Docker** & Docker Compose
- **Ollama** (pour Mistral LLM)

### Matériel recommandé

- **RAM** : 8 GB minimum (16 GB recommandé)
- **Disque** : 10 GB d'espace libre
- **CPU** : 4 cœurs minimum (GPU optionnel pour accélération)

---

## 📦 Installation

### 1. Cloner le projet

```bash
git clone https://github.com/votre-username/mozilla-ci-log-analysis.git
cd mozilla-ci-log-analysis
```

### 2. Installer les dépendances Python

```bash
pip install -r requirements.txt
```

### 3. Lancer l'infrastructure (Kafka + Elasticsearch)

```bash
docker-compose up -d
```

Vérifier que tout est UP :
```bash
docker ps
# Devrait afficher : kafka, elasticsearch, kibana
```

### 4. Installer et démarrer Ollama + Mistral

```bash
# Installation Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Télécharger Mistral 7B
ollama pull mistral

# Vérifier
ollama list
```

---

## 🚀 Utilisation

### Pipeline complet (première fois)

#### Étape 1 : Extraction des logs RAR

```bash
python scripts/extract_rar.py
```

**Sortie** : `data/extracted/day_01/`, `day_02/`, ...

#### Étape 2 : Parsing des logs

```bash
python scripts/parse_all_logs.py
```

**Sortie** : `data/parsed/` (fichiers JSON structurés)

#### Étape 3 : Envoi vers Kafka

```bash
python src/streaming/producer.py
```

**Attendu** : ~25,000 messages envoyés

#### Étape 4 : Consommation et indexation

**Terminal 1** (Index Kibana) :
```bash
python src/streaming/consumer.py
```

**Terminal 2** (Index RAG avec embeddings) :
```bash
python src/streaming/consumer_semantic.py
```

**Attendu** : 25,450 documents indexés (débit : ~6 docs/s)

---

### Interface RAG (Chatbot)

#### Option 1 : Interface Streamlit (recommandé)

```bash
streamlit run app_chatbot.py
```

Ouvrir : http://localhost:8501

#### Option 2 : CLI Python

```bash
python src/ai/rag_engine_semantic.py
```

**Commandes** :
- `clear` : Effacer historique
- `stats` : Statistiques de session
- `quit` : Quitter

---

### Visualisation Kibana

Accéder à : http://localhost:5601

**Dashboards disponibles** :
- Vue d'ensemble (performances, durées, CPU/IO)
- Statistiques de succès (93.83% de taux de réussite)
- Analyse par builder et plateforme
- Analyse des erreurs

---

## 📁 Structure du Projet

```
mozilla-ci-log-analysis/
├── data/
│   ├── raw/                    # Fichiers .rar sources
│   ├── extracted/              # Logs .txt extraits
│   └── parsed/                 # JSON structurés
│
├── src/
│   ├── parser/
│   │   └── log_parser.py       # Parser multi-niveaux
│   ├── streaming/
│   │   ├── producer.py         # Kafka producer
│   │   ├── consumer.py         # Consumer standard
│   │   └── consumer_semantic.py # Consumer avec embeddings
│   └── ai/
│       └── rag_engine_semantic.py  # RAG Engine
│
├── scripts/
│   ├── extract_rar.py          # Extraction archives
│   └── parse_all_logs.py       # Parsing batch
│
├── app_chatbot.py              # Interface Streamlit
├── docker-compose.yml          # Kafka + ES + Kibana
├── requirements.txt            # Dépendances Python
└── README.md                   # Ce fichier
```

---

## 🛠️ Technologies

| Composant | Technologie | Version | Justification |
|-----------|-------------|---------|---------------|
| **Streaming** | Apache Kafka | 3.7.0 | Mode KRaft (sans Zookeeper), gestion messages 50MB |
| **Stockage** | Elasticsearch | 8.11.0 | Recherche full-text + kNN vectoriel natif |
| **Visualisation** | Kibana | 8.11.0 | Dashboards interactifs |
| **Embeddings** | Sentence-BERT | all-MiniLM-L6-v2 | 384 dims, léger, performant (80 MB) |
| **LLM** | Mistral | 7B (Ollama) | Open-source, local, aucune fuite de données |
| **Interface** | Streamlit | 1.29.0 | Prototypage rapide d'UI |
| **Parsing** | Python + Regex | 3.8+ | Flexibilité pour formats hétérogènes |

---




---



