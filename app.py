# app.py
import re
import random
from collections import Counter
import gradio as gr

# ---------------- 기본 설정 ----------------
STOPWORDS = {
    "a","an","the","and","or","but","if","then","so","because","as","of","in","on","at","to","for","from","by","with",
    "about","into","through","during","before","after","above","below","up","down","out","over","under","again","further",
    "here","there","when","where","why","how","all","any","both","each","few","more","most","other","some","such","no",
    "nor","not","only","own","same","so","than","too","very","can","will","just","should","now",
    "이","그","저","것","수","등","및","또는","그리고","그래서","또한","은","는","이","가","을","를","의","에","에서","으로","로","와","과","도","만"
}

WORD_PATTERN = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?|[0-9]+(?:\.[0-9]+)?|[가-힣]+")

# ---------------- 유틸리티 함수 ----------------
def split_sentences(text):
    if not text:
        return []
    text = re.sub(r'\s+', ' ', text).strip()
    parts = re.split(r'(?<=[\.\!\?\。\?!]|다)\s+', text)
    return [p.strip() for p in parts if len(p.strip()) >= 3]

def tokenize(text):
    return [m.group(0) for m in WORD_PATTERN.finditer(text)]

def score_tokens(text, sents):
    tokens = []
    for s in sents:
        tokens.extend(tokenize(s))
    freq = Counter([t for t in tokens if t.lower() not in STOPWORDS])
    scores = {}
    for t, f in freq.items():
        score = f + len(t)/4
        scores[t] = score
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)

# ---------------- 빈칸 문제 ----------------
def make_fill_in_blank(sent, scored_tokens):
    toks = tokenize(sent)
    candidates = [t for t in toks if len(t) >= 2 and t not in STOPWORDS]
    if not candidates and toks:
        candidates = [max(toks, key=len)]
    for target in candidates:
        pattern = re.compile(re.escape(target))
        if pattern.search(sent):
            question = pattern.sub("____", sent, count=1)
            return question, target
    return None, None

# ---------------- OX 문제 ----------------
def make_true_false(sent, scored_tokens, rnd=None):
    if rnd is None: rnd = random.Random()
    s = sent
    truth = True
    explanation = f"원문: '{sent}'"
    nums = re.findall(r'\d+', s)
    if nums and rnd.random() < 0.6:
        n = rnd.choice(nums)
        new_n = str(int(n)+rnd.randint(1,10))
        s = s.replace(n,new_n,1)
        truth = False
        explanation += f" -> 숫자 변경 {n}→{new_n}"
        return s, truth, explanation
    return s, truth, explanation

# ---------------- 퀴즈 생성 ----------------
def generate_quiz(text, num_tf=3, num_blank=3):
    sents = split_sentences(text)
    scored = score_tokens(text, sents)
    tf_list, blank_list = [], []
    rnd = random.Random()
    for s in sents:
        if len(tf_list) < num_tf:
            q, truth, expl = make_true_false(s, scored, rnd)
            tf_list.append({"statement":q, "answer":truth, "explanation":expl})
        if len(blank_list) < num_blank:
            q,a = make_fill_in_blank(s, scored)
            if q: blank_list.append({"question":q,"answer":a})
        if len(tf_list) >= num_tf and len(blank_list) >= num_blank:
            break
    return {"tf":tf_list,"blank":blank_list}

# ---------------- 토론 주제 ----------------
def generate_discussion_topics(text, num=3):
    sents = split_sentences(text)
    topics = []
    for s in sents[:num]:
        topics.append(f"'{s}'의 핵심 의미와 사회적/역사적 영향을 토론하시오.")
    return topics

# ---------------- 출력 포맷 ----------------
def format_output(discussions, quiz, show_discussion=True, show_tf=True, show_blank=True):
    out = ""
    if show_discussion and discussions:
        out += "### 토론 주제\n"
        for i,t in enumerate(discussions,1):
            out += f"{i}) {t}\n"
        out += "\n"
    if show_tf and quiz.get("tf"):
        out += "### OX 문제\n"
        for i,q in enumerate(quiz.get("tf",[]),1):
            out += f"{i}) {q['statement']}\n"
            out += f"   정답: {'O(참)' if q['answer'] else 'X(거짓)'}\n"
            out += f"   해설: {q['explanation']}\n"
        out += "\n"
    if show_blank and quiz.get("blank"):
        out += "### 빈칸 채우기\n"
        for i,q in enumerate(quiz.get("blank",[]),1):
            out += f"{i}) {q['question']}\n"
            out += f"   정답: {q['answer']}\n"
        out += "\n"
    return out

# ---------------- Gradio 인터페이스 ----------------
def generate_all(text, types, num_discussion=3, num_tf=3, num_blank=3):
    show_discussion = "토론 주제" in types
    show_tf = "OX 문제" in types
    show_blank = "빈칸 문제" in types
    discussions = generate_discussion_topics(text, num=num_discussion) if show_discussion else []
    quiz = generate_quiz(text, num_tf=num_tf, num_blank=num_blank)
    return format_output(discussions, quiz, show_discussion, show_tf, show_blank)

iface = gr.Interface(
    fn=generate_all,
    inputs=[
        gr.Textbox(lines=10, placeholder="학습 내용을 붙여넣으세요", label="학습 내용"),
        gr.CheckboxGroup(["토론 주제","OX 문제","빈칸 문제"], label="출력 유형 선택", value=["토론 주제","OX 문제","빈칸 문제"]),
        gr.Slider(1,10,3, step=1, label="토론 주제 개수"),
        gr.Slider(1,10,3, step=1, label="OX 문제 개수"),
        gr.Slider(1,10,3, step=1, label="빈칸 문제 개수")
    ],
    outputs="markdown",
    title="📚 토론 & 퀴즈 생성기",
    description="텍스트를 분석하여 의미 있는 빈칸과 OX 문제를 생성합니다."
)

if __name__ == "__main__":
    iface.launch(share=True)
