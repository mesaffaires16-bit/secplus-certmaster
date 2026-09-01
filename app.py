import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List
import json
import time

# --- Configuration de la page ---
st.set_page_config(
    page_title="CompTIA Security+ SY0-701 Simulator",
    page_icon="🛡️",
    layout="wide"
)

# --- Initialisation du Client Gemini ---
api_key = st.secrets.get("GEMINI_API_KEY", None)
if not api_key:
    st.error("⚠️ Clé API introuvable. Ajoutez 'GEMINI_API_KEY' dans les Secrets de votre déploiement Streamlit.")
    st.stop()

client = genai.Client(api_key=api_key)

# --- Schéma Pydantic pour la génération structurée ---
class Option(BaseModel):
    id: str = Field(description="Lettre de l'option : A, B, C, ou D")
    text: str = Field(description="Texte de l'option de réponse")

class Explanation(BaseModel):
    why_correct: str = Field(description="Explication claire et détaillée de la bonne réponse")
    why_a_incorrect: str = Field(description="Pourquoi l'option A est incorrecte (ou vide si A est la bonne)")
    why_b_incorrect: str = Field(description="Pourquoi l'option B est incorrecte (ou vide si B est la bonne)")
    why_c_incorrect: str = Field(description="Pourquoi l'option C est incorrecte (ou vide si C est la bonne)")
    why_d_incorrect: str = Field(description="Pourquoi l'option D est incorrecte (ou vide si D est la bonne)")

class SecurityPlusQuestion(BaseModel):
    domain: str = Field(description="Domaine CompTIA Security+ SY0-701 (ex: 1.0, 2.0, 3.0, 4.0, 5.0)")
    sub_topic: str = Field(description="Sous-thématique précise du référentiel")
    difficulty: str = Field(description="Niveau de difficulté : Hard ou Exam-Level")
    scenario: str = Field(description="Mise en situation technique réaliste (logs, incident, infrastructure)")
    question: str = Field(description="La question technique précise posée au candidat")
    options: List[Option] = Field(description="Exactement 4 options : A, B, C, D")
    correct_answer: str = Field(description="La lettre de la réponse correcte (A, B, C ou D)")
    explanation: Explanation

# --- Gestion de l'état (Session State) ---
if "stats" not in st.session_state:
    st.session_state.stats = {
        "1.0 Concepts généraux de sécurité": {"total": 0, "correct": 0},
        "2.0 Menaces, vulnérabilités et atténuations": {"total": 0, "correct": 0},
        "3.0 Architecture de sécurité": {"total": 0, "correct": 0},
        "4.0 Opérations de sécurité": {"total": 0, "correct": 0},
        "5.0 Gestion des programmes de sécurité": {"total": 0, "correct": 0}
    }
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "user_answered" not in st.session_state:
    st.session_state.user_answered = False
if "selected_option" not in st.session_state:
    st.session_state.selected_option = None
if "tutor_chat" not in st.session_state:
    st.session_state.tutor_chat = []

# --- Fonction de génération de question ---
def generate_question(selected_domain: str):
    domain_instruction = (
        f"Génère une question stricte pour le domaine {selected_domain}."
        if selected_domain != "Aléatoire / Examen Complet"
        else "Choisis aléatoirement parmi les 5 domaines officiels du SY0-701."
    )

    prompt = f"""
    Tu es le concepteur en chef des examens officiels CompTIA Security+ (SY0-701).
    Génère une question de haut niveau technique basée sur des scénarios d'entreprise, des analyses de logs, 
    des configurations d'authentification, de pare-feu, de cryptographie ou de gestion des incidents.
    {domain_instruction}
    La question doit être en français, rigoureuse et ne laisser aucune ambiguïté.
    """

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SecurityPlusQuestion,
            temperature=0.7,
        ),
    )
    return json.loads(response.text)

# --- Barre latérale : Tableau de Bord & Paramètres ---
with st.sidebar:
    st.title("🛡️ Tableau de Bord")
    
    # Calcul des stats globales
    total_q = sum(v["total"] for v in st.session_state.stats.values())
    total_correct = sum(v["correct"] for v in st.session_state.stats.values())
    global_score = (total_correct / total_q * 100) if total_q > 0 else 0
    
    st.metric(label="Score Global", value=f"{global_score:.1f}%", delta=f"{total_correct}/{total_q} réussis")
    st.progress(global_score / 100)
    
    st.subheader("Performance par Domaine")
    for dom, data in st.session_state.stats.items():
        dom_total = data["total"]
        dom_correct = data["correct"]
        dom_pct = (dom_correct / dom_total * 100) if dom_total > 0 else 0
        st.write(f"**{dom[:3]}** : {dom_pct:.0f}% ({dom_correct}/{dom_total})")

    st.divider()
    mode_selection = st.selectbox(
        "Sélectionnez le Domaine d'entraînement :",
        [
            "Aléatoire / Examen Complet",
            "1.0 Concepts généraux de sécurité",
            "2.0 Menaces, vulnérabilités et atténuations",
            "3.0 Architecture de sécurité",
            "4.0 Opérations de sécurité",
            "5.0 Gestion des programmes de sécurité"
        ]
    )

# --- Zone Principale ---
st.title("CompTIA Security+ (SY0-701) - Entraînement Adaptatif")

col_btn, _ = st.columns([1, 3])
with col_btn:
    if st.button("🚀 Nouvelle Question", type="primary", use_container_width=True):
        with st.spinner("Génération d'un scénario d'examen..."):
            st.session_state.current_question = generate_question(mode_selection)
            st.session_state.user_answered = False
            st.session_state.selected_option = None
            st.session_state.tutor_chat = []
            st.rerun()

q = st.session_state.current_question

if q:
    st.caption(f"🏷️ **Domaine :** {q.get('domain')} | **Sous-thème :** {q.get('sub_topic')} | **Difficulté :** {q.get('difficulty')}")
    
    # Boîte de scénario
    st.info(f"**Mise en situation :**\n\n{q.get('scenario')}")
    st.markdown(f"### {q.get('question')}")

    options = {opt['id']: opt['text'] for opt in q.get('options', [])}
    
    # Formulaire de réponse
    if not st.session_state.user_answered:
        user_choice = st.radio(
            "Choisissez la meilleure option :",
            options=list(options.keys()),
            format_func=lambda x: f"**{x}** : {options[x]}",
            index=None
        )
        
        if st.button("Valider la Réponse", disabled=(user_choice is None)):
            st.session_state.selected_option = user_choice
            st.session_state.user_answered = True
            
            # Enregistrement des statistiques
            is_correct = (user_choice == q.get('correct_answer'))
            dom_key = next((k for k in st.session_state.stats.keys() if k.startswith(q.get('domain')[:3])), None)
            if dom_key:
                st.session_state.stats[dom_key]["total"] += 1
                if is_correct:
                    st.session_state.stats[dom_key]["correct"] += 1
            st.rerun()

    # Affichage des résultats et de la rétroaction
    if st.session_state.user_answered:
        correct_ans = q.get('correct_answer')
        chosen_ans = st.session_state.selected_option
        
        if chosen_ans == correct_ans:
            st.success(f"🎯 **EXCELLENT ! La bonne réponse est bien {correct_ans}.**")
        else:
            st.error(f"❌ **INCORRECT. Vous avez choisi {chosen_ans}, mais la bonne réponse est {correct_ans}.**")
        
        # Explications détaillées
        st.subheader("💡 Analyse & Décomposition Pédagogique")
        exp = q.get('explanation', {})
        st.markdown(f"**Pourquoi {correct_ans} est la réponse exacte :**\n{exp.get('why_correct')}")
        
        st.markdown("**Pourquoi les autres options sont incorrectes dans ce contexte :**")
        for opt_id in ["A", "B", "C", "D"]:
            if opt_id != correct_ans:
                reason = exp.get(f"why_{opt_id.lower()}_incorrect", "N/A")
                st.markdown(f"- **Option {opt_id}** : {reason}")

        # Section Tuteur Interactif Socratique
        st.divider()
        st.subheader("🧑‍🏫 Tuteur IA Dédié")
        st.caption("Vous avez un doute sur un acronyme ou le raisonnement ? Posez directement votre question ci-dessous.")
        
        for message in st.session_state.tutor_chat:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
        user_query = st.chat_input("Ex: Peux-tu m'expliquer la différence entre cette solution et un SIEM ?")
        if user_query:
            st.session_state.tutor_chat.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)
                
            tutor_prompt = f"""
            Tu es le tuteur d'un candidat préparant l'examen CompTIA Security+.
            Contexte de la question actuelle :
            - Scénario : {q.get('scenario')}
            - Question : {q.get('question')}
            - Réponse correcte : {correct_ans} ({options.get(correct_ans)})
            
            L'utilisateur demande : "{user_query}"
            Réponds de manière concise, pédagogique et précise sans t'éparpiller.
            """
            
            with st.chat_message("assistant"):
                tutor_response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=tutor_prompt
                )
                st.markdown(tutor_response.text)
                st.session_state.tutor_chat.append({"role": "assistant", "content": tutor_response.text})
else:
    st.info("👈 Cliquez sur le bouton **'🚀 Nouvelle Question'** pour commencer votre session d'entraînement.")
