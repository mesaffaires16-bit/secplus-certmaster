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
    st.error("⚠️ Clé API introuvable. Ajoutez 'GEMINI_API_KEY' dans les Secrets de Streamlit.")
    st.stop()

client = genai.Client(api_key=api_key)

# --- Schéma Pydantic strict et optimisé ---
class Option(BaseModel):
    id: str = Field(description="Lettre : A, B, C, ou D")
    text: str = Field(description="Contenu de la réponse")

class Explanation(BaseModel):
    why_correct: str = Field(description="Explication synthétique et technique de la bonne réponse")
    why_a_incorrect: str = Field(description="Raison pour l'option A (vide si A est correcte)")
    why_b_incorrect: str = Field(description="Raison pour l'option B (vide si B est correcte)")
    why_c_incorrect: str = Field(description="Raison pour l'option C (vide si C est correcte)")
    why_d_incorrect: str = Field(description="Raison pour l'option D (vide si D est correcte)")

class SecurityPlusQuestion(BaseModel):
    domain: str = Field(description="Ex: 1.0, 2.0, 3.0, 4.0, 5.0")
    sub_topic: str = Field(description="Sous-thématique précise du SY0-701")
    difficulty: str = Field(description="Hard ou Exam-Level")
    scenario: str = Field(description="Scénario d'entreprise ou extrait de logs")
    question: str = Field(description="Question posée")
    options: List[Option]
    correct_answer: str = Field(description="A, B, C ou D")
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

# --- Fonction de génération avec Retry Automatique ---
def generate_question(selected_domain: str, max_retries: int = 3):
    domain_instruction = (
        f"Génère une question stricte pour le domaine {selected_domain}."
        if selected_domain != "Aléatoire / Examen Complet"
        else "Choisis aléatoirement parmi les 5 domaines du SY0-701."
    )

    prompt = f"""
    Tu es concepteur d'examen CompTIA Security+ (SY0-701).
    Génère un cas pratique réaliste (infrastructure, logs, protocole, attaque ou gouvernance).
    {domain_instruction}
    Rédige en français avec rigueur technique.
    """

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=SecurityPlusQuestion,
                    temperature=0.6,
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            # En cas de 503 ou pic de charge, on attend 1.5s et on retente
            if attempt < max_retries - 1:
                time.sleep(1.5)
                continue
            else:
                raise e

# --- Barre latérale : Tableau de Bord & Paramètres ---
with st.sidebar:
    st.title("🛡️ Tableau de Bord")
    
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
        "Sélectionnez le Domaine :",
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
        with st.spinner("Génération du scénario en cours..."):
            try:
                st.session_state.current_question = generate_question(mode_selection)
                st.session_state.user_answered = False
                st.session_state.selected_option = None
                st.session_state.tutor_chat = []
                st.rerun()
            except Exception:
                st.error("Les serveurs sont très sollicités. Veuillez recliquer sur le bouton.")

q = st.session_state.current_question

if q:
    st.caption(f"🏷️ **Domaine :** {q.get('domain')} | **Sous-thème :** {q.get('sub_topic')} | **Difficulté :** {q.get('difficulty')}")
    st.info(f"**Mise en situation :**\n\n{q.get('scenario')}")
    st.markdown(f"### {q.get('question')}")

    options = {opt['id']: opt['text'] for opt in q.get('options', [])}
    
    if not st.session_state.user_answered:
        user_choice = st.radio(
            "Choisissez la réponse adéquate :",
            options=list(options.keys()),
            format_func=lambda x: f"**{x}** : {options[x]}",
            index=None
        )
        
        if st.button("Valider la Réponse", disabled=(user_choice is None)):
            st.session_state.selected_option = user_choice
            st.session_state.user_answered = True
            
            is_correct = (user_choice == q.get('correct_answer'))
            dom_key = next((k for k in st.session_state.stats.keys() if k.startswith(q.get('domain')[:3])), None)
            if dom_key:
                st.session_state.stats[dom_key]["total"] += 1
                if is_correct:
                    st.session_state.stats[dom_key]["correct"] += 1
            st.rerun()

    if st.session_state.user_answered:
        correct_ans = q.get('correct_answer')
        chosen_ans = st.session_state.selected_option
        
        if chosen_ans == correct_ans:
            st.success(f"🎯 **EXCELLENT ! Bonne réponse : {correct_ans}.**")
        else:
            st.error(f"❌ **INCORRECT. Votre choix : {chosen_ans} | Réponse attendue : {correct_ans}.**")
        
        st.subheader("💡 Explication & Décomposition")
        exp = q.get('explanation', {})
        st.markdown(f"**Pourquoi {correct_ans} est correct :**\n{exp.get('why_correct')}")
        
        st.markdown("**Analyse des autres options :**")
        for opt_id in ["A", "B", "C", "D"]:
            if opt_id != correct_ans:
                reason = exp.get(f"why_{opt_id.lower()}_incorrect", "N/A")
                st.markdown(f"- **Option {opt_id}** : {reason}")

        # Tuteur Interactif
        st.divider()
        st.subheader("🧑‍🏫 Tuteur IA")
        
        for message in st.session_state.tutor_chat:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
        user_query = st.chat_input("Une question sur ce concept ou un acronyme ?")
        if user_query:
            st.session_state.tutor_chat.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)
                
            tutor_prompt = f"""
            Tu es le tuteur CompTIA Security+. 
            Scénario : {q.get('scenario')}
            Question : {q.get('question')}
            Bonne réponse : {correct_ans} ({options.get(correct_ans)})
            
            Question de l'étudiant : "{user_query}"
            Réponds de façon synthétique et claire.
            """
            
            with st.chat_message("assistant"):
                tutor_response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=tutor_prompt
                )
                st.markdown(tutor_response.text)
                st.session_state.tutor_chat.append({"role": "assistant", "content": tutor_response.text})
else:
    st.info("👈 Cliquez sur **'🚀 Nouvelle Question'** pour vous entraîner.")
