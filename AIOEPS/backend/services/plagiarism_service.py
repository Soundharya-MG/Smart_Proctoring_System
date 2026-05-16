"""
plagiarism_service.py — Automatic Hybrid Plagiarism Detection
AIOEPS v7
Auto-runs on student submission.
Compares: Reference answers + Other students' submissions (same question)
Score bands: 0-60 Normal | 61-90 Medium | 91-100 Suspicious
"""

import re
import math
import ast
import tokenize
import io
from difflib import SequenceMatcher
from collections import Counter

# Optional: SentenceTransformers
try:
    from sentence_transformers import SentenceTransformer, util
    _st_model = SentenceTransformer('all-MiniLM-L6-v2')
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False
    print("⚠️  SentenceTransformer not available — semantic similarity skipped")


def _clean(text: str) -> str:
    return re.sub(r'\s+', ' ', text.lower().strip())

def _tokenize(text: str) -> list:
    return re.findall(r'\b\w+\b', text.lower())

def _remove_comments(code: str) -> str:
    """Remove single-line and multi-line comments."""
    code = re.sub(r'//.*', '', code)
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r'#.*', '', code)
    return code

def _normalize_varnames(code: str) -> str:
    """Replace variable-like names with generic tokens (simplistic)."""
    code = re.sub(r'\b[a-z][a-z0-9_]{0,10}\b', 'VAR', code)
    return code

def _normalize_code(code: str) -> str:
    """Normalize code: remove comments, strip formatting differences."""
    code = _remove_comments(code)
    code = re.sub(r'\s+', ' ', code).strip().lower()
    return code

def _get_ast_tokens(code: str) -> list:
    """Extract AST-level token types for Python code (language-agnostic fallback: tokenize)."""
    try:
        tokens = []
        code_io = io.StringIO(code)
        for tok in tokenize.generate_tokens(code_io.readline):
            if tok.type not in (tokenize.COMMENT, tokenize.NEWLINE,
                                 tokenize.NL, tokenize.ENCODING):
                # Normalize NAME tokens (variable names) to 'VAR'
                if tok.type == tokenize.NAME:
                    tokens.append('NAME')
                else:
                    tokens.append(tok.string)
        return tokens
    except Exception:
        return _tokenize(code)

def _token_similarity(t1: str, t2: str) -> float:
    """Token-based similarity ignoring variable names and comments."""
    toks1 = _get_ast_tokens(t1)
    toks2 = _get_ast_tokens(t2)
    if not toks1 or not toks2:
        return 0.0
    return SequenceMatcher(None, toks1, toks2).ratio()

def _tfidf_similarity(t1: str, t2: str) -> float:
    tok1, tok2 = _tokenize(t1), _tokenize(t2)
    if not tok1 or not tok2:
        return 0.0
    vocab = set(tok1) | set(tok2)
    def tf(tokens):
        c = Counter(tokens)
        total = len(tokens)
        return {w: c[w]/total for w in vocab}
    v1, v2 = tf(tok1), tf(tok2)
    dot = sum(v1[w]*v2[w] for w in vocab)
    n1  = math.sqrt(sum(v**2 for v in v1.values()))
    n2  = math.sqrt(sum(v**2 for v in v2.values()))
    return dot / (n1 * n2) if n1 and n2 else 0.0

def _string_similarity(t1: str, t2: str) -> float:
    return SequenceMatcher(None, _normalize_code(t1), _normalize_code(t2)).ratio()

def _semantic_similarity(t1: str, t2: str) -> float:
    if not SEMANTIC_AVAILABLE:
        return 0.0
    try:
        emb1 = _st_model.encode(t1, convert_to_tensor=True)
        emb2 = _st_model.encode(t2, convert_to_tensor=True)
        return float(util.cos_sim(emb1, emb2)[0][0])
    except Exception:
        return 0.0

def _score_pair(answer: str, ref: str) -> dict:
    """Compute all similarity metrics between two code strings."""
    token  = _token_similarity(answer, ref)
    kw     = _tfidf_similarity(answer, ref)
    string = _string_similarity(answer, ref)
    sem    = _semantic_similarity(answer, ref)
    combined = (token * 0.35 + kw * 0.25 + string * 0.25 + sem * 0.15) * 100
    combined = min(100, max(0, combined))
    return {
        'token':    round(token * 100, 1),
        'keyword':  round(kw    * 100, 1),
        'string':   round(string* 100, 1),
        'semantic': round(sem   * 100, 1),
        'combined': round(combined, 1)
    }

def compute_plagiarism(answer: str, reference_answers: list) -> dict:
    """Compare answer against reference corpus."""
    if not answer or not answer.strip():
        return {'score': 0, 'level': 'Normal', 'details': 'No answer provided', 'matched_with': None}
    if not reference_answers:
        return {'score': 0, 'level': 'Normal', 'details': 'No reference data', 'matched_with': None}

    max_score   = 0.0
    best_detail = {}

    for ref in reference_answers:
        if not ref or not ref.strip():
            continue
        scores = _score_pair(answer, ref)
        if scores['combined'] > max_score:
            max_score = scores['combined']
            best_detail = scores

    score = round(max_score, 1)
    if score <= 60:
        level = 'Normal'
    elif score <= 90:
        level = 'Medium'
    else:
        level = 'Suspicious'

    return {'score': score, 'level': level, 'details': best_detail, 'matched_with': 'reference'}


def compute_plagiarism_full(answer: str, question_id: int, student_id: int,
                             question_text: str = '', session_id: int = None) -> dict:
    """
    AUTOMATIC full plagiarism check:
    1. Compare with reference answers
    2. Compare with other students' submitted answers for same question
    Returns worst (highest) score and details.
    """
    if not answer or not answer.strip():
        return {'score': 0, 'level': 'Normal', 'details': 'No answer', 'matched_with': None}

    try:
        from database.db import get_db_connection
        conn = get_db_connection()

        # --- Step 1: Reference check ---
        refs = get_references_for_question(question_text)
        ref_result = compute_plagiarism(answer, refs)

        # --- Step 2: Cross-student check ---
        # Fetch all OTHER students' answers for this question
        rows = conn.execute("""
            SELECT a.student_answer, es.student_id
            FROM answers a
            JOIN exam_sessions es ON a.session_id = es.id
            WHERE a.question_id = ?
              AND es.student_id != ?
              AND a.student_answer IS NOT NULL
              AND a.student_answer != ''
        """, (question_id, student_id)).fetchall()
        conn.close()

        max_cross_score = 0.0
        best_cross_detail = {}
        matched_student_id = None

        for row in rows:
            other_ans = row['student_answer']
            if not other_ans or not other_ans.strip():
                continue
            scores = _score_pair(answer, other_ans)
            if scores['combined'] > max_cross_score:
                max_cross_score = scores['combined']
                best_cross_detail = scores
                matched_student_id = row['student_id']

        # --- Pick worst case ---
        if max_cross_score > ref_result['score']:
            final_score = round(max_cross_score, 1)
            final_detail = best_cross_detail
            matched_with = f'student_id:{matched_student_id}'
        else:
            final_score = ref_result['score']
            final_detail = ref_result['details']
            matched_with = 'reference_answer'

        if final_score <= 60:
            level = 'Normal'
        elif final_score <= 90:
            level = 'Medium'
        else:
            level = 'Suspicious'

        return {
            'score': final_score,
            'level': level,
            'details': final_detail,
            'matched_with': matched_with,
            'ref_score': ref_result['score'],
            'cross_student_score': round(max_cross_score, 1),
            'total_compared': len(rows)
        }

    except Exception as e:
        # Fallback to reference-only check
        refs = get_references_for_question(question_text)
        return compute_plagiarism(answer, refs)


# ─── Reference Corpus ────────────────────────────────────────────────────────
REFERENCE_CORPUS = {
    'factorial': [
        """#include<iostream>
using namespace std;
int factorial(int n){
    if(n==0 || n==1) return 1;
    return n * factorial(n-1);
}
int main(){
    int n=5;
    cout<<factorial(n);
    return 0;
}""",
        """#include<iostream>
using namespace std;
int main(){
    int n=5, fact=1;
    for(int i=1;i<=n;i++) fact*=i;
    cout<<fact;
    return 0;
}""",
        """import java.util.*;
public class Main{
    static int factorial(int n){
        if(n==0||n==1) return 1;
        return n*factorial(n-1);
    }
    public static void main(String[] args){
        System.out.println(factorial(5));
    }
}""",
        """def factorial(n):
    if n==0 or n==1:
        return 1
    return n*factorial(n-1)
print(factorial(5))""",
        "factorial recursion base case n-1 multiply return 1",
    ],
    'prime': [
        """#include<iostream>
using namespace std;
int main(){
    int n=7;
    bool prime=true;
    if(n<2) prime=false;
    for(int i=2;i*i<=n;i++){
        if(n%i==0){ prime=false; break; }
    }
    if(prime) cout<<"Prime number";
    else cout<<"Not a prime number";
    return 0;
}""",
        """#include<iostream>
using namespace std;
bool isPrime(int n){
    if(n<2) return false;
    for(int i=2;i<=n/2;i++)
        if(n%i==0) return false;
    return true;
}
int main(){
    int n=7;
    cout<<(isPrime(n)?"Prime number":"Not a prime number");
    return 0;
}""",
        """import java.util.*;
public class Main{
    public static void main(String[] args){
        int n=7;
        boolean prime=true;
        for(int i=2;i*i<=n;i++){
            if(n%i==0){ prime=false; break; }
        }
        System.out.println(prime?"Prime number":"Not a prime number");
    }
}""",
        """n=7
prime=True
for i in range(2,int(n**0.5)+1):
    if n%i==0:
        prime=False
        break
print("Prime number" if prime else "Not a prime number")""",
        "prime divisible modulo sqrt loop break isPrime not prime number",
    ],
    'fibonacci': [
        """#include<iostream>
using namespace std;
int main(){
    int n=6,a=0,b=1;
    for(int i=0;i<n;i++){
        cout<<a<<" ";
        int c=a+b; a=b; b=c;
    }
    return 0;
}""",
        """import java.util.*;
public class Main{
    public static void main(String[] args){
        int n=6,a=0,b=1;
        for(int i=0;i<n;i++){
            System.out.print(a+" ");
            int c=a+b; a=b; b=c;
        }
    }
}""",
        """a,b=0,1
for i in range(6):
    print(a,end=' ')
    a,b=b,a+b""",
        "fibonacci series fib a b swap terms loop print 0 1 1 2 3 5",
    ],
    'oops': [
        "class object method constructor inheritance polymorphism encapsulation abstraction",
        "public static void main String args System out println",
        "int n return void class Main public",
    ],
    'data_structures': [
        "A stack is a linear data structure that follows the LIFO principle.",
        "Queue follows FIFO — first in first out data structure.",
        "Binary tree is a hierarchical structure where each node has at most two children.",
        "Linked list is a sequential structure where elements are connected via pointers.",
    ],
    'algorithms': [
        "Binary search works on sorted arrays by dividing the search space in half.",
        "Bubble sort repeatedly swaps adjacent elements if they are in wrong order.",
        "Merge sort uses divide and conquer to sort arrays in O(n log n) time.",
    ],
    'python': [
        "A list in Python is mutable and ordered collection of elements.",
        "Dictionary stores key value pairs and provides O(1) average lookup time.",
    ],
}


def get_reference_answers(subject: str = None) -> list:
    if subject and subject.lower() in REFERENCE_CORPUS:
        return REFERENCE_CORPUS[subject.lower()]
    all_refs = []
    for refs in REFERENCE_CORPUS.values():
        all_refs.extend(refs)
    return all_refs


def get_references_for_question(question_text: str) -> list:
    qt = question_text.lower()
    refs = []
    if 'factorial' in qt:
        refs.extend(REFERENCE_CORPUS['factorial'])
    if 'prime' in qt:
        refs.extend(REFERENCE_CORPUS['prime'])
    if 'fibonacci' in qt or 'fib' in qt:
        refs.extend(REFERENCE_CORPUS['fibonacci'])
    refs.extend(REFERENCE_CORPUS['oops'])
    if not refs:
        return get_reference_answers()
    return refs


def is_coding_question(question_type: str) -> bool:
    return (question_type or '').upper() in ('CODING', 'CODE')
