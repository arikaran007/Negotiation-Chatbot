import os
import streamlit as st
import google.generativeai as genai
from textblob import TextBlob
import re
from dotenv import load_dotenv
load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")


api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-pro')

#sentimental analysis
def analyze_sentiment(text):
    analysis = TextBlob(text)
    return analysis.sentiment.polarity

def get_sentiment_label(score):
    if score > 0.05:
        return "positive"
    elif score < -0.05:
        return "negative"
    else:
        return "neutral"

def extract_offer(text):
   
    match = re.search(r'\$?(\d+)', text)
    if match:
        return float(match.group(1))
    return None

#greetings
def extract_name(text):
    name_match = re.search(r"(?:hi|hello|hey)\s*(i'm|my name is)\s*([a-zA-Z]+)", text, re.IGNORECASE)
    if name_match:
        return name_match.group(2)
    return "Customer"


#gratitude
def detect_gratitude(text):
    return any(phrase in text.lower() for phrase in ["thank you", "thanks", "appreciate it"])


#negotiation start
def detect_general_inquiry(text):
    return any(phrase in text.lower() for phrase in ["what's your best price", "interested in buying", "best price", "price for"])

def initial_negotiation_response():
    return "Hey there! Thanks for your interest in our smartphone. It’s a fantastic device! Our standard price is $100, but I'm here to negotiate. What are you thinking?"

def fix_spacing(response_text):
    return re.sub(r'([a-zA-Z])(?=[A-Z])', r'\1 ', response_text)

def negotiate(customer_offer, negotiation_history, customer_name):
    current_offer = 100  

    # Perform sentiment analysis
    sentiment_score = analyze_sentiment(negotiation_history)
    sentiment = get_sentiment_label(sentiment_score)

    # Prompt Template
    prompt = f"""
    You are a skilled negotiator representing a supplier in a price negotiation. 
    The product's cost price is $80, and the desired selling price is $100.
    Current offer: ${current_offer}
    Customer's counteroffer: ${customer_offer}
    Negotiation history: {negotiation_history}
    Customer's sentiment: {sentiment}

    Respond in a conversational, human-like tone addressing the customer as {customer_name}. Maintain a natural and clear formatting with appropriate spacing between words.
    """

    # Generate response 
    response = model.generate_content(prompt)
    response_text = fix_spacing(response.text)

    # Decision
    if "accept" in response_text.lower():
        decision = "accept"
        new_offer = customer_offer
    elif "reject" in response_text.lower():
        decision = "reject"
        new_offer = current_offer
    else:
        decision = "counteroffer"
        try:
            new_offer = float(response_text.split("$")[-1].split()[0])
        except:
            new_offer = current_offer  

    return {
        "decision": decision,
        "new_offer": new_offer,
        "response": response_text,
        "sentiment": sentiment
    }

# Streamlit User Interface
st.title("Negotiation Chatbot")
st.write("Negotiate the price of a product. The starting price is $100.")


if "messages" not in st.session_state:
    st.session_state.messages = []
if "customer_name" not in st.session_state:
    st.session_state.customer_name = "Customer"
if "ongoing_negotiation" not in st.session_state:
    st.session_state.ongoing_negotiation = False

# Display chat 
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


if prompt := st.chat_input("Let's negotiate!"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

  
    if st.session_state.customer_name == "Customer":
        st.session_state.customer_name = extract_name(prompt)

    # gratitude
    if detect_gratitude(prompt):
        response = f"You're welcome, {st.session_state.customer_name}! Let me know if you have any more questions."

    elif not st.session_state.ongoing_negotiation and detect_general_inquiry(prompt):
        response = initial_negotiation_response()
        st.session_state.ongoing_negotiation = True  

    else:
        customer_offer = extract_offer(prompt)
        if customer_offer is None:
            response = f"Hey {st.session_state.customer_name}, I didn't catch the offer. Could you please mention the price you're thinking of?"
        else:
            negotiation_history = "\n".join([m["content"] for m in st.session_state.messages])
            response_data = negotiate(customer_offer, negotiation_history, st.session_state.customer_name)
            response = f"Decision: {response_data['decision']}\nNew offer: ${response_data['new_offer']}\n\n{response_data['response']}"

    # Display assistant response 
    with st.chat_message("assistant"):
        st.markdown(response)
 
    st.session_state.messages.append({"role": "assistant", "content": response})


st.sidebar.title("Negotiation Summary")
if st.session_state.messages:
    initial_offer = 100
    last_offer = initial_offer
    for message in st.session_state.messages:
        if message["role"] == "assistant" and "New offer: $" in message["content"]:
            last_offer = float(message["content"].split("New offer: $")[1].split("\n")[0])
    
    st.sidebar.metric("Initial Offer", f"${initial_offer}")
    st.sidebar.metric("Current Offer", f"${last_offer}", f"{last_offer - initial_offer:+.2f}")

    progress = (initial_offer - last_offer) / (initial_offer - 80)  
    st.sidebar.progress(min(max(progress, 0), 1))
    st.sidebar.text(f"Negotiation Progress: {progress:.2%}")
