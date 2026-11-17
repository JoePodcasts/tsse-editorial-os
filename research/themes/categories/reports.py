"""Render the same proposed joins that editors and a future release builder consume."""
from collections import Counter
from itertools import combinations
from classify import read

SITE="https://tsse-editorial-os.vercel.app"
# An editorial reading route, in episode-number order within the comparison.
GUIDE={
 "cat-01": ([14,103,159],"Episode 14 focuses on explaining why the founder chose the problem. Episode 103 turns the meeting around and asks what the investor must demonstrate to the founder.","Check episode 158 in its surrounding turns. A host’s formulation of what founders seek is weaker than a founder describing a decision."),
 "cat-02": ([10,103,112,197],"A cutoff can reduce discretionary bias. A five-part rubric still leaves room for judgment about people. Diversified exposure through managers and concentrated ownership in a direct fund answer different portfolio questions.","Keep the investment decision in view. A guest’s title or the existence of an investment supplies little evidence about how the decision was made."),
 "cat-03": ([41,96,195],"Running a services business can reveal a narrow need. Technical lead time tests defensibility. Observing a design partner use the product tests utility. These are different forms of early evidence.","Check whether examples about a founder’s background explain how the product or market was understood."),
 "cat-04": ([37,60,88,100],"Recruiting constantly, managing limited cash and learning quickly put different demands on a founder. The retrospective in episode 100 qualifies success stories by describing the failures they leave out.","Check episode 100 for how much the short reflection adds to this collection. Separate the founder’s conviction from an investor’s conviction about portfolio weights."),
 "cat-05": ([23,85,150,171],"A user can bring in the next user. An enterprise seller may instead have to move closer to buyers. Episode 171 asks when inbound demand pulls a company away from the intended customer.","Look for overlooked sales and pricing examples described in customer language. Check the channel mechanism before treating a corporate relationship as distribution."),
 "cat-06": ([9,139,154,186],"Synthetic biology changes production economics. Computer vision and learning algorithms can change products or how a fund sources deals. A technology card will therefore include several distinct lines of inquiry.","Inspect secondary deep-tech examples for a described capability. A company name, a technology in a job history, or an isolated AI mention is insufficient."),
 "cat-07": ([27,86,89,138],"Claims, brokerage and underwriting produce different problems from those of decentralized financial protocols. An insurance investor’s own fundraising experience may belong on a different card.","Check episode 120 against the surrounding crypto discussion. Give reviewers a way to distinguish insurance infrastructure from banking and payments."),
 "cat-08": ([3,72,155,197],"Care delivery pairs technical capability with empathy. Construction and industrial software turn on adoption constraints, budgets and existing workflows. The second half of the category name does considerable work.","Review episode 142’s data-center example and episode 160’s legal software. Confirm that the source describes an industry workflow or structural change."),
 "cat-09": ([16,19,125,152],"An immigrant-focused fund, a Latin America mandate and introductions to cross-border buyers address different barriers. A mixer offers evidence about the specific work a network does.","Check location-only portfolio claims such as episode 41. Separate founders’ access to a network from where a guest happened to live.")
}

def render(data):
    cats=read("taxonomy.json")
    links=read("theme-links.json")
    themes={t["id"]:t["name"] for t in read("../catalogue.json")}
    inv=data["inventory"]
    eps={r["episode_id"]:r for r in inv}
    ev=data["evidence"]
    rows=data["associations"]
    counts=Counter((r["category_id"],r["strength"]) for r in rows)
    overlap=Counter(pair for r in inv for pair in combinations(r["categories"],2))
    names={c["id"]:c["name"] for c in cats}
    missing=[r for r in inv if not r["categories"]]
    multi=sum(len(r["categories"])>1 for r in inv)
    total=len(inv)-len(missing)
    top_pair,top_n=overlap.most_common(1)[0]
    cov=["# Category coverage and quality","",
         f"The November 10 snapshot contains {len(inv)} published episodes. {total} have at least one proposed association, {multi} have several and {len(missing)} await classification. Across {len(rows)} associations, {sum(r['strength']=='strong' for r in rows)} are strong and {sum(r['strength']=='secondary' for r in rows)} secondary. Every membership is pending editorial review.","",
         f"The most frequent overlap is **{names[top_pair[0]]}** with **{names[top_pair[1]]}** ({top_n} episodes). Counts include both strengths. These are counts of proposed readings, not the frequency with which a word or subject occurs.","",
         "|Category|Strong|Secondary|Unique episodes|","|---|---:|---:|---:|"]
    review=["# Nine categories for exploring TSSE","",
            "The editor approved the nine category definitions. This review concerns which episodes belong under them and where the nine existing editorial themes fit. All assignments and theme links are proposed.","",
            f"Of {len(inv)} conversations examined, {total} have supporting evidence and {multi} have more than one proposed category. The widest overlap is {names[top_pair[0]]} with {names[top_pair[1]]} ({top_n} episodes). See [coverage and exceptions](coverage.md).","",
            "For each category, compare the representative passages first. Each episode row opens its supporting passages in the transcript reader. The [classification inventory](inventory.json) also includes episodes awaiting classification. Exact transcript words appear as blockquotes. The surrounding explanations are interpretations. A speaker label is source-supplied and audio-unverified.",""]
    for c in cats:
        k=c["id"]
        group=[r for r in rows if r["category_id"]==k]
        st,sec=counts[k,"strong"],counts[k,"secondary"]
        cov.append(f"|{c['name']}|{st}|{sec}|{st+sec}|")
        reps,variation,action=GUIDE[k]
        review.extend([f"## {c['name']}","",c["description"],"",f"**{st} strong · {sec} secondary**","",variation,"",action,""])
        related=[f"{themes[l['theme_id']]} ({l['relationship']})" for l in links if l["category_id"]==k]
        review.extend(["**Proposed editorial themes** — "+(" · ".join(related) or "No Phase 1 theme has sufficient evidence for a link")+".",""])
        for num in reps:
            a=next(r for r in group if r["episode_number"]==num)
            ep=eps[a["episode_id"]]
            p=ev[a["evidence"][0]]
            review.extend([f"**Episode {num} · [{ep['title']}]({ep['source_url']}) · {a['strength']}**","",
                           "> "+p["excerpt"].replace("\n","\n> "),"",
                           f"Source label {p['speaker_label']}. [Open the transcript passage]({SITE}{p['internal_link']})",""])
        review.extend(["### All proposed episodes","",
                       "|Episode|Strength|Reason for inclusion|Evidence in context|","|---|---|---|---|"])
        for a in group:
            ep=eps[a["episode_id"]]
            refs=" · ".join(f"[Passage {i}]({SITE}{ev[ref]['internal_link']})" for i,ref in enumerate(a["evidence"],1))
            review.append(f"|{ep['episode_number']} · {ep['title'].replace('|','/')}|{a['strength']}|{a['rationale'].replace('|','/')}|{refs}|")
        review.append("")
    cov.extend(["","### Cross-category overlap","","Each entry counts unique episodes carrying both categories. The numbers in the header use the editor’s display order above.","",
                "|Category|"+"|".join(str(c["display_order"]) for c in cats)+"|","|---|"+"---:|"*len(cats)])
    for c in cats:
        k=c["id"]
        cov.append("|"+c["name"]+"|"+"|".join("—" if t["id"]==k else str(overlap[tuple(sorted((k,t["id"])))]) for t in cats)+"|")
    cov.extend(["","### Unclassified episodes",""])
    for r in missing:
        cov.append(f"- [{r['episode_number']} · {r['title']}]({r['source_url']})")
    cov.extend(["","Episode 1 introduces the podcast. Episode 162 centers on special education, school staffing and support for learners. The discussion warrants its own editorial attention. Classifying it as healthcare solely because it concerns children with special needs would misdescribe the source.","",
                "### Where the taxonomy stretches","",
                "The discipline cards describe what someone is trying to do. The sector cards describe where or with what technology that work takes place. Episode 155 supports both emerging technology and legacy-industry change. Episode 93 connects financial regulation with distribution through partners. Preserve both memberships wherever each has evidence.","",
                "Growth has relatively few proposed episodes. Chapter headings and transcripts use many terms for the same sales motion, including ACV and inbound. Healthcare shares a category with construction, chemical production and legal software. Test whether readers can predict those results from the card description. Climate, regulation, social impact and educational access merit future indexing experiments within the existing nine categories.","",
                "### Review queue","",
                f"All {len(rows)} assignments and {len(links)} theme links need a human decision. {sum(len(r['evidence'])==1 for r in rows)} assignments currently have one selected excerpt. {sum(p['speaker_label']=='unknown' for p in ev.values())} of {len(ev)} unique excerpts have no local speaker label. {sum(p['start_timestamp'] is not None for p in ev.values())} begin with a genuine transcript marker. Check the surrounding turns before attribution and listen to audio before publishing a named quotation.","",
                "Review single-excerpt and secondary associations first. The inventory and association files support filtering by category, strength, evidence count and episode. Text matching can miss paraphrases and can confuse investor biography with analysis. The source-context decisions record targeted additions, revisions and exclusions. Counts are specific to these rules and this archive snapshot.",""])
    return {"review.md":"\n".join(review),"coverage.md":"\n".join(cov)}
