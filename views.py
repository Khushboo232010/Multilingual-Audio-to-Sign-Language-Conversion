from googletrans import Translator  # type: ignore
import re
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import nltk
from django.contrib.staticfiles import finders
from django.contrib.auth.decorators import login_required
import time

# Download NLTK resources 
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('omw-1.4')

# Manual translation mapping for Hindi and English
manual_translations = {
    # Hindi to English for ISL gestures
    "mai": "Me",
    "main": "Me",
    "mein": "Me",
    "jata": "Go",
    "jati": "Go",
    "jaa": "Go",
    "hu": "",
    "college": "College",
    "school": "School",
    "kal": "Tomorrow",
    "aaj": "Today",
    "tum": "You",
    "aap": "You",
    "kaise": "How",
    "ho": "Are",
    "sukriya": "Thank you",
    "dhanyawad": "Thank you",
    "aawaz":"sound",
    "hello":"Hello",

    # English corrections
    "i": "Me",
    "am": "",
    "going": "Go",
    "go": "Go",
    "bye-bye": "Bye",
    "thankyou": "Thank you",
    "thanks": "Thank you",
    "job": "work",
    "watch": "see",
    "house":"home",
    "voice":"sound",
}

def home_view(request):
    return render(request, 'home.html')

def about_view(request):
    return render(request, 'about.html')

def contact_view(request):
    return render(request, 'contact.html')

@login_required(login_url="login")
def animation_view(request):
    if request.method == 'POST':
        text = request.POST.get('sen')
        lang_selected = request.POST.get('language', 'en')

        if not text:
            return render(request, 'animation.html', {'error': "Please enter some text."})

        translator = Translator()
        tries = 3
        while tries:
            try:
                detected_lang = translator.detect(text).lang

                if lang_selected == 'hi' or detected_lang == 'hi':
                    display_text = translator.translate(text, src='hi', dest='hi').text
                    translated_text = translator.translate(text, src='hi', dest='en').text
                    print("Translated Text:", translated_text)

                else:
                    display_text = text
                    translated_text = translator.translate(text, src='en', dest='en').text
                    print("Translated Text:", translated_text)
                    

                # Expand common contractions (like I'm → I am)
                translated_text = re.sub(r"\bI'm\b", "I am", translated_text, flags=re.IGNORECASE)
                translated_text = re.sub(r"\bI've\b", "I have", translated_text, flags=re.IGNORECASE)
                translated_text = re.sub(r"\bI'll\b", "I will", translated_text, flags=re.IGNORECASE)
                translated_text = re.sub(r"\bcan't\b", "cannot", translated_text, flags=re.IGNORECASE)
                translated_text = re.sub(r"\bwon't\b", "will not", translated_text, flags=re.IGNORECASE)

                translated_text = translated_text.replace(" r ", " are ").replace(" u ", " you ")
                break
            except Exception as e:
                print(f"Translation error: {e}")
                time.sleep(1)
                tries -= 1
        else:
            return render(request, 'animation.html', {'error': "Translation failed. Try again."})

        processed_text = translated_text.lower()
        words = re.split(r"[\s\-]+", processed_text)
        tagged = nltk.pos_tag(words)

        # Tense Detection
        tense = {
            "future": len([w for w in tagged if w[1] == "MD"]),
            "present": len([w for w in tagged if w[1] in ["VBP", "VBZ", "VBG"]]),
            "past": len([w for w in tagged if w[1] in ["VBD", "VBN"]]),
            "present_continuous": len([w for w in tagged if w[1] == "VBG"]),
        }

        stop_words = set(stopwords.words('english'))
        preserve_words = {'how',  'you', 'again', 'please', 'hello', 'hi', 'thanks', 'thank', 'i', 
                          'am','now','me', 'will', 'go', 'before','what','do','not','up','where','this','that','then','your',
                          'very',}

        lr = WordNetLemmatizer()
        filtered_text = []

        for w, p in zip(words, tagged):
            if w.lower() in preserve_words or w.lower() not in stop_words:
                if p[1] in ['VBG', 'VBD', 'VBZ', 'VBN', 'NN']:
                    filtered_text.append(lr.lemmatize(w, pos='v'))
                elif p[1] in ['JJ', 'JJR', 'JJS', 'RBR', 'RBS']:
                    filtered_text.append(lr.lemmatize(w, pos='a'))
                else:
                    filtered_text.append(lr.lemmatize(w))

        # Replace 'i' with 'Me'
        words = [manual_translations.get(w.lower(), w) for w in filtered_text]

        probable_tense = max(tense, key=tense.get)
        if probable_tense == "past" and tense["past"] >= 1:
            words.insert(0, "Before")
        elif probable_tense == "future" and tense["future"] >= 1 and "Will" not in words:
            words.insert(0, "Will")
        elif probable_tense == "present" and tense["present_continuous"] >= 1:
            words.insert(0, "Now")

        final_videos = []

        for w in words:
            matched = False
            clean_word = w.strip()

            # Try different capitalizations to match the filename
            possible_names = [
                clean_word.capitalize(),  # Bye
                clean_word.lower(),       # bye
                clean_word.upper(),       # BYE
            ]

            for name in possible_names:
                if finders.find(f"assets/{name}.mp4"):
                    final_videos.append(name)
                    matched = True
                    break

            if not matched:
                # If full word animation not found, fallback to spelling it
                for ch in clean_word.upper():
                    if ch.isalpha() and finders.find(f"assets/{ch}.mp4"):
                        final_videos.append(ch)
                    else:
                        print(f"No animation for alphabet: {ch}")

        return render(request, 'animation.html', {
            'words': final_videos,
            'display_text': display_text,
            'lang': lang_selected,
            'input_cleared': True
        })

    return render(request, 'animation.html')

def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('animation')
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect(request.POST.get('next') or 'animation')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect("home")
