"""Replay the full-corpus lexical screen; write JSONL to stdout."""
import json
import re
from corpus import corpus, sentences

# Alternative formulations within a group, independent signals across groups.
QUERIES = {
    "portfolio-breadth": ["diversif|concentrat|power law", "portfolio|investments|funds", "return|risk|winner|outlier|lose|average"],
    "earning-trust": ["relationship|build trust|get to know|stay in touch", "investor|founder|entrepreneur|fundrais|raising", "time|before|months|years|early|update"],
    "customer-proof": ["customer|users", "talk|validat|feedback|listen|willing to pay|interview", "problem|product|build|need|pay|solution"],
    "financing-milestones": ["runway|burn rate|cash flow|milestone|dilution", "rais|capital|funding|money|cash", "next|months|enough|round|need|profitab"],
    "pitch-clarity": ["story|pitch|explain|communicat|presentation", "simple|clear|concise|understand|seconds|jargon|complex", "investor|business|company|problem|product|founder|entrepreneur"],
    "capital-geography": ["silicon valley|bay area|coasts", "outside|midwest|region|local|ecosystem|access|elsewhere|geograph", "capital|funding|invest|entrepreneur|founder|talent"],
    "talent-as-leverage": ["recruit|hiring|hire|attract talent", "team|people|talent|candidate", "founder|ceo|company|entrepreneur|startup|investor"],
    "founder-insight": ["insight|unique perspective|unfair advantage|domain expertise", "founder|entrepreneur|market|customer|problem", "experience|unique|understand|others|industry|different|deep"],
    "distribution-partners": ["distribution|channel|partnership", "partner|incumbent|carrier|broker|platform", "customer|sell|reach|market|product|access|scale"],
}
def candidates():
    episodes, docs = corpus()
    patterns = {key:[re.compile(p,re.I) for p in groups] for key,groups in QUERIES.items()}
    for pid, doc in docs.items():
        for line in sentences(doc):
            for theme, groups in patterns.items():
                if all(p.search(line) for p in groups[:2]):
                    score = sum(len(set(m.group().lower() for m in p.finditer(line))) for p in groups)
                    yield dict(theme=theme, passage=pid, episode=doc["episode_number"], excerpt=line,
                               rank=score, speaker=doc["speaker_label"])
if __name__ == "__main__":
    for row in candidates():
        print(json.dumps(row, ensure_ascii=False))
