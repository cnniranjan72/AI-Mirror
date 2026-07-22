"""Expand the intent dataset from 110 to 500+ queries."""
import random
import hashlib

random.seed(42)

templates = {
    'identity_question': [
        'What kind of {t} am I?',
        'Describe my {t}',
        'Tell me about my {t}',
        'What are my {t}?',
        'Who am I as a {t}?',
        'What defines my {t}?',
        'How would you describe my {t}?',
        'Can you tell me about my {t}?',
        'What type of {t} am I?',
        'Analyze my {t}',
    ],
    'behavioral_question': [
        'What {t} do I have?',
        'How often do I {t}?',
        'What are my {t}?',
        'Describe my {t}',
        'Tell me about my {t}',
        'What {t} influence me?',
        'How much time do I spend on {t}?',
        'What are my strongest {t}?',
        'Show me my {t}',
        'What {t} patterns do I have?',
    ],
    'explanation': [
        'Why did I {t}?',
        'Why have my {t} changed?',
        'What caused my {t}?',
        'Explain why I {t}',
        'Why do I keep {t}?',
        'What led to my {t}?',
        'How come I {t}?',
        'Why is my {t} changing?',
        'What factors led to my {t}?',
        'Explain my {t}',
    ],
    'reflection': [
        'How has my {t} evolved?',
        'What have I been {t}?',
        'How have my {t} changed?',
        'What have I been learning about {t}?',
        'How did my {t} evolve?',
        'What progress have I made in {t}?',
        'Reflect on my {t}',
        'What changed in my {t}?',
        'How has my {t} grown?',
        'What have I noticed about my {t}?',
    ],
    'comparison': [
        'Compare my {t}',
        'What is the difference between {t} and {t2}?',
        'How do my {t} compare?',
        'Which is better for {t}?',
        'Compare {t} with {t2}',
        'How does my {t} differ from before?',
        'What are similarities between {t} and {t2}?',
        'How do my {t} contrast with my {t2}?',
        'Compare my current and past {t}',
        'Which {t} do I prefer more?',
    ],
    'prediction': [
        'Will I continue {t}?',
        'What will my {t} be like?',
        'Predict my {t}',
        'What is the likelihood I will {t}?',
        'Forecast my {t}',
        'Will I keep {t}?',
        'What is next for my {t}?',
        'How long will I {t}?',
        'What are the trends in my {t}?',
        'What will I be interested in next?',
    ],
    'coaching': [
        'How can I improve my {t}?',
        'Help me improve my {t}',
        'What strategy should I use for {t}?',
        'Give me advice on {t}',
        'How can I get better at {t}?',
        'What tips do you have for {t}?',
        'Should I focus on {t}?',
        'How can I achieve my {t}?',
        'Suggest a plan for {t}',
        'What can I do to improve my {t}?',
    ],
    'recommendation': [
        'Recommend some {t}',
        'What {t} should I explore?',
        'Suggest {t} for me',
        'What are good {t} resources?',
        'What else should I explore?',
        'Any good {t} recommendations?',
        'What similar {t} would I enjoy?',
        'Recommend a {t}',
        'Can you suggest {t}?',
        'What should I {t} next?',
    ],
    'memory_question': [
        'What did I {t} last week?',
        'Do you remember what I {t}?',
        'What was I {t} earlier?',
        'What did I {t} last month?',
        'Did I {t} previously?',
        'Recall what I {t}',
        'What happened during my last {t}?',
        'What did I do in my last {t}?',
        'What was I learning about {t}?',
        'What {t} did I engage with?',
    ],
    'information': [
        'What is {t}?',
        'Tell me about {t}',
        'Define {t}',
        'How does {t} work?',
        'What are the benefits of {t}?',
        'What does {t} mean?',
        'Explain {t} to me',
        'Describe {t}',
        'What do you know about {t}?',
        'What is the definition of {t}?',
    ],
    'unknown': [
        'Hello', 'Hi', 'Hey', 'Good morning', 'Good evening',
        'Thanks', 'Thank you', 'Okay', 'Ok', 'Sure',
        'I see', 'Nice', 'Cool', 'Awesome', 'Great',
        'Yes', 'No', 'Maybe', 'Hello there', 'Hi again',
        'Bye', 'Goodbye', 'See you', 'Later', 'Alright',
        'Hmm', 'Interesting', 'Wow', 'Alright then', 'Got it',
        'Understood', 'Fine', 'Whatever', 'Nope', 'Yep',
        'Hello!', 'Hi!', 'Hey there', 'Hello world', 'Just testing',
    ]
}

topics = [
    'learning', 'reading', 'watching', 'coding', 'exercising',
    'cooking', 'gaming', 'studying', 'writing', 'drawing',
    'photography', 'music', 'dancing', 'singing', 'meditating',
    'habits', 'interests', 'preferences', 'behaviors', 'patterns',
    'skills', 'knowledge', 'abilities', 'talents', 'strengths',
    'goals', 'aspirations', 'motivations', 'values',
    'learning style', 'content consumption', 'viewing habits',
    'study habits', 'work habits', 'daily routine',
    'personality', 'character', 'traits', 'qualities',
    'focus', 'attention', 'concentration', 'discipline',
    'Python', 'JavaScript', 'machine learning', 'data science',
    'web development', 'mobile apps', 'databases', 'algorithms',
    'video editing', 'graphic design', 'animation',
    'fitness', 'nutrition', 'health', 'wellness', 'yoga',
    'baking', 'gardening', 'DIY', 'crafting',
    'chess', 'puzzles', 'strategy', 'simulation',
]

seen = set()
lines = []
# 45 per intent = 495 total
for intent, tmpls in templates.items():
    count = 0
    attempts = 0
    while count < 45 and attempts < 500:
        t = random.choice(topics)
        t2 = random.choice(topics)
        tmpl = random.choice(tmpls)
        q = tmpl.replace('{t}', t).replace('{t2}', t2)
        key = hashlib.md5(q.encode()).hexdigest()
        if key in seen:
            attempts += 1
            continue
        seen.add(key)
        lines.append((q, intent))
        count += 1
        attempts += 1

print(f"Generated {len(lines)} queries")
from collections import Counter
for intent, cnt in sorted(Counter(l[1] for l in lines).items()):
    print(f"  {intent}: {cnt}")
