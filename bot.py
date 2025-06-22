from audiobox_aesthetics.infer import initialize_predictor
predictor = initialize_predictor()

import os
from openai import OpenAI          # SDK ≥ 1.0.0

client = OpenAI(                   # pulls your key from $OPENAI_API_KEY
 api_key="xxx"
)

def chat(input_text):
    response = client.chat.completions.create(
        model="gpt-4o-mini",           # any chat-capable model name
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": input_text}
        ],
        temperature=0.7,               # all the usual tuning knobs work
    )

    return response.choices[0].message.content

system_prompt = """
You are a genetic learning algorithm simulator.
You will help evolve a bytebeat string to create the best sounding music. 
Bytebeats will be given an aesthetic score (0.0 to 10.0):
You goal is to output a bytebeat string that maximizes this value.

Only the first 10 seconds of the bytebeat (from t=0 to t=16000) will be ranked.
I will give you the past history of bytebeats and their rankings. 
Your job is to cleverly learn from this history, to figure out how to create an even better scoring bytebeat.
Keep some ideas from high scores, and ignore ideas from low scores.
The bytebeat string has a maximum of 20 characters. 
Try adding in random strings.
Do not append ideas to the end of an existing bytebeat. 

Don't add extra words or syntax, just output the bytebeat string.

If there is no history, please produce the first bytebeat
"""

from bytebeat2wav import render
import torch

def render2(bytebeat):
    wav = render(bytebeat)
    wav = torch.from_numpy(wav).to(torch.float32) # → float32
    wav /= 32768.0        
    wav = wav.unsqueeze(0)
    scores = predictor.forward([{"path":wav, "sample_rate": 16_000}])[0]
    score = 0
    for k, v in scores.items():
        score += v
    score = round(score, 1)
    bytebeat.replace('"','')
    #score_string = 'Score: %s -> %s' % (, bytebeat)
    return score
    
    
    
def pick_history_subset(history, top_n: int = 3, rand_n: int = 3):
    """
    Return a shuffled list containing
      • up to `top_n` highest-scoring items
      • plus up to `rand_n` additional random items
    drawn from the remainder of `history`.
    Works even if history has < top_n items.
    """
    if not history:                     # empty history → nothing to do
        return []

    # ----- top N by score -----
    top = sorted(history, key=lambda h: h["score"], reverse=True)[:top_n]

    # ----- random N from the rest -----
    remaining = [h for h in history if h not in top]
    rand = random.sample(remaining, k=min(rand_n, len(remaining)))

    # ----- combine & shuffle -----
    chosen = top + rand
    random.shuffle(chosen)
    return chosen

def history_string(x):
    return f"{x['score']}: {x['bytebeat']}"

history = []
import wave
import subprocess, sys

    
def save(bytebeat, path):
    # ⇣  put the *exact* args in a list so the shell never sees them
    cmd = [
        sys.executable,          # or just "python"
        "bytebeat2wav.py",
        bytebeat,      # the byte-beat expression
        path
    ]

    subprocess.run(cmd, check=True)   # raises if the script exits non-zero


import random
high_score = 0

def go(bot_id, history):
    global high_score
    history_list =  pick_history_subset(history)
    #print(len(history_list))
    history_list = "\n".join(history_string(x) for x in history_list)
    
    n = random.randint(0, 10) 
    if n < 4:
        input_text = "No history, this is the first. Your Bytebeat:"
    else:
        input_text = f"History:\n{history_list}\n\nYour Bytebeat:"
    #print(input_text)
    bytebeat = chat(input_text)
    try:
        score = render2(bytebeat)
    except Exception as e:
        print("fail", e)
        return
    
    if score > high_score:
        high_score = score
        print(f"BOT {bot_id} NEW HIGH SCORE", score, bytebeat)
        save(bytebeat, f"bot{bot_id}_{score}.wav")
    else:
        #print(score, bytebeat)
        pass
        
    history.append({"score": score, "bytebeat": bytebeat})

    
    