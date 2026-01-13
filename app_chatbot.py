"""
Interface Chatbot Moderne - Mozilla CI RAG Sémantique
"""
import streamlit as st
import sys
from pathlib import Path

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent))

from src.ai.rag_engine_semantic import (
    ask_question_optimized, 
    smart_search, 
    clear_history,
    conversation_history,
    show_stats
)

# ========================================
# CONFIGURATION PAGE
# ========================================
st.set_page_config(
    page_title="Mozilla CI Assistant",
    page_icon="🦊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================================
# STYLE CSS MODERNE ET ÉPURÉ
# ========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Fond général */
    .stApp {
        background: #f8f9fa;
    }
    
    /* Suppression des marges par défaut */
    .main > div {
        padding-top: 2rem;
    }
    
    /* Container principal */
    .main {
        max-width: 1200px;
        margin: 0 auto;
    }
    
    /* En-tête */
    .header-container {
        background: white;
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    
    .header-title {
        font-size: 28px;
        font-weight: 700;
        color: #1a1a1a;
        margin: 0;
        line-height: 1.3;
    }
    
    .header-subtitle {
        font-size: 16px;
        color: #6c757d;
        margin-top: 0.5rem;
        font-weight: 400;
    }
    
    /* Messages utilisateur */
    .user-message {
        background: #0060df;
        color: white;
        padding: 1.25rem 1.5rem;
        border-radius: 18px;
        margin: 1.5rem 0;
        margin-left: auto;
        max-width: 75%;
        font-size: 15px;
        line-height: 1.6;
        box-shadow: 0 2px 8px rgba(0, 96, 223, 0.15);
    }
    
    .user-label {
        font-weight: 600;
        font-size: 13px;
        opacity: 0.9;
        margin-bottom: 0.5rem;
    }
    
    /* Messages assistant */
    .assistant-message {
        background: white;
        color: #1a1a1a;
        padding: 1.25rem 1.5rem;
        border-radius: 18px;
        margin: 1.5rem 0;
        max-width: 75%;
        font-size: 15px;
        line-height: 1.6;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        border: 1px solid #e9ecef;
    }
    
    .assistant-label {
        font-weight: 600;
        font-size: 13px;
        color: #0060df;
        margin-bottom: 0.5rem;
    }
    
    /* Zone de saisie */
    .input-container {
        background: white;
        padding: 1.5rem;
        border-radius: 16px;
        margin-top: 2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border: 1px solid #e9ecef;
    }
    
    .stTextInput>div>div>input {
        border-radius: 12px;
        padding: 1rem 1.25rem;
        border: 2px solid #e9ecef;
        font-size: 15px;
        transition: border-color 0.2s;
    }
    
    .stTextInput>div>div>input:focus {
        border-color: #0060df;
        box-shadow: 0 0 0 3px rgba(0, 96, 223, 0.1);
    }
    
    /* Boutons principaux */
    .stButton>button {
        background: #0060df;
        color: white;
        border-radius: 12px;
        padding: 0.875rem 1.75rem;
        border: none;
        font-weight: 600;
        font-size: 15px;
        transition: all 0.2s;
        box-shadow: 0 2px 4px rgba(0, 96, 223, 0.2);
    }
    
    .stButton>button:hover {
        background: #0250bb;
        box-shadow: 0 4px 8px rgba(0, 96, 223, 0.3);
    }
    
    /* Boutons suggestions */
    div[data-testid="column"] .stButton>button {
        background: #f8f9fa;
        color: #495057;
        border: 1px solid #dee2e6;
        box-shadow: none;
        font-weight: 500;
        font-size: 14px;
    }
    
    div[data-testid="column"] .stButton>button:hover {
        background: #e9ecef;
        border-color: #0060df;
        color: #0060df;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: white;
        border-right: 1px solid #e9ecef;
    }
    
    section[data-testid="stSidebar"] h2 {
        font-size: 18px;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 1rem;
    }
    
    section[data-testid="stSidebar"] h3 {
        font-size: 15px;
        font-weight: 600;
        color: #1a1a1a;
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
    }
    
    /* Radio buttons */
    .stRadio > label {
        font-size: 14px;
        font-weight: 500;
        color: #495057;
    }
    
    .stRadio > div {
        font-size: 14px;
    }
    
    /* Metrics */
    div[data-testid="stMetric"] {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e9ecef;
    }
    
    div[data-testid="stMetric"] label {
        font-size: 13px;
        font-weight: 500;
        color: #6c757d;
    }
    
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 24px;
        font-weight: 700;
        color: #0060df;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        font-size: 14px;
        font-weight: 500;
        background: #f8f9fa;
        border-radius: 8px;
        padding: 0.75rem;
    }
    
    /* Suppression des séparateurs */
    hr {
        margin: 2rem 0;
        border: none;
        border-top: 1px solid #e9ecef;
    }
    
    /* Section suggestions */
    .suggestions-container {
        background: white;
        padding: 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    
    .suggestions-title {
        font-size: 16px;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 1.25rem;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        color: #6c757d;
        padding: 2rem 0;
        font-size: 14px;
        margin-top: 3rem;
    }
</style>
""", unsafe_allow_html=True)

# ========================================
# INITIALISATION SESSION STATE
# ========================================
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'search_mode' not in st.session_state:
    st.session_state.search_mode = "hybrid"

# ========================================
# SIDEBAR
# ========================================
with st.sidebar:
    st.image("https://www.mozilla.org/media/protocol/img/logos/mozilla/logo-word-hor.e20791bb4dd4.svg", 
             width=180)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("## Configuration")
    
    # Mode de recherche
    st.session_state.search_mode = st.radio(
        "Mode de recherche",
        ["hybrid", "semantic"],
        format_func=lambda x: "Hybride (Recommandé)" if x == "hybrid" else "Sémantique pur",
        help="Le mode hybride combine recherche sémantique et par mots-clés"
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Statistiques
    st.markdown("## Statistiques")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Questions", len(st.session_state.messages) // 2)
    with col2:
        st.metric("Historique", len(conversation_history))
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Actions
    if st.button("Effacer l'historique", use_container_width=True):
        st.session_state.messages = []
        clear_history()
        st.rerun()
    
    if st.button("Statistiques détaillées", use_container_width=True):
        show_stats()
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Info
    st.markdown("### Capacités")
    st.markdown("""
    **Recherche intelligente**  
    Comprend les synonymes et filtre par plateforme
    
    **Analyse avancée**  
    Performance, erreurs et comparaisons
    
    **Contexte conversationnel**  
    Se souvient de vos questions précédentes
    """)

# ========================================
# HEADER
# ========================================
st.markdown("""
<div class="header-container">
    <h1 class="header-title">Mozilla CI Assistant</h1>
    <p class="header-subtitle">Analysez vos logs CI/CD avec l'intelligence artificielle</p>
</div>
""", unsafe_allow_html=True)

# ========================================
# SUGGESTIONS
# ========================================
if len(st.session_state.messages) == 0:
    st.markdown("""
    <div class="suggestions-container">
        <p class="suggestions-title">Questions suggérées</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    suggestions = [
        "Builds les plus lents",
        "Erreurs sur Linux",
        "Compare Windows vs Linux",
        "Résumé des problèmes",
        "Builds avec CPU élevé",
        "Tests qui échouent"
    ]
    
    for i, suggestion in enumerate(suggestions):
        col = [col1, col2, col3][i % 3]
        with col:
            if st.button(suggestion, key=f"sugg_{i}", use_container_width=True):
                st.session_state.messages.append({
                    "role": "user",
                    "content": suggestion
                })
                st.rerun()

# ========================================
# AFFICHAGE DES MESSAGES
# ========================================
chat_container = st.container()

with chat_container:
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f"""
            <div class="user-message">
                <div class="user-label">Vous</div>
                {message["content"]}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="assistant-message">
                <div class="assistant-label">Assistant</div>
                {message["content"]}
            </div>
            """, unsafe_allow_html=True)
            
            # Afficher les détails si disponibles
            if "details" in message:
                with st.expander("Voir les logs sources"):
                    for i, detail in enumerate(message["details"], 1):
                        st.markdown(f"""
                        **{i}. {detail['builder']}**
                        - Status: `{detail['status']}`
                        - Durée: `{detail['duration']}s`
                        - Score: `{detail['score']:.2f}`
                        """)

# ========================================
# INPUT UTILISATEUR
# ========================================
st.markdown('<div class="input-container">', unsafe_allow_html=True)

col1, col2 = st.columns([5, 1])

with col1:
    user_input = st.text_input(
        "Message",
        placeholder="Posez votre question sur les logs CI/CD...",
        key="user_input",
        label_visibility="collapsed"
    )

with col2:
    send_button = st.button("Envoyer", use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

# ========================================
# TRAITEMENT DE LA QUESTION
# ========================================
if send_button and user_input:
    # Ajouter message utilisateur
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    # Afficher spinner
    with st.spinner("Recherche dans les logs..."):
        try:
            # Recherche
            results = smart_search(
                user_input, 
                limit=5, 
                use_hybrid=(st.session_state.search_mode == "hybrid")
            )
            
            if results['hits']['hits']:
                # Préparer les détails
                details = []
                for hit in results['hits']['hits']:
                    src = hit['_source']
                    details.append({
                        'builder': src.get('metadata', {}).get('builder', 'N/A'),
                        'status': src.get('metadata', {}).get('result_status', 'N/A'),
                        'duration': src.get('metrics', {}).get('duration_seconds', 0),
                        'score': hit.get('_score', 0)
                    })
                
                # Génerer réponse (sans affichage console)
                import io
                from contextlib import redirect_stdout
                
                f = io.StringIO()
                with redirect_stdout(f):
                    answer = ask_question_optimized(
                        user_input, 
                        search_mode=st.session_state.search_mode,
                        show_details=False
                    )
                
                # Ajouter message assistant
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer if answer else "Désolé, je n'ai pas pu analyser ces logs.",
                    "details": details
                })
            else:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Aucun log pertinent trouvé pour cette question."
                })
        
        except Exception as e:
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Erreur lors de l'analyse : {str(e)}"
            })
    
    # Recharger la page pour afficher les nouveaux messages
    st.rerun()

# ========================================
# FOOTER
# ========================================
st.markdown("""
<div class="footer">
    Propulsé par Elasticsearch, Sentence Transformers et Mistral<br>
    Recherche sémantique 100% locale
</div>
""", unsafe_allow_html=True)