"""Phonetic drug-name hints: cross-script sound-alike candidates from the lexicon, for the note writer.

Whisper writes drug names as garbled Urdu script ("پر اندال" for Panadol). A consonant-skeleton match against the
lexicon recovers most of them, but snapping the transcript to the match inserts false drugs (see RUN_NOTES, drug
lexicon experiments). Here the transcript is left unchanged: the candidates go to the LLM as hints, and the LLM keeps
only those used as a treatment in context. drug_check.py and negation_guard.py still run on its output.

The matcher is nabzlib's find_term logic with its existing tolerances, unchanged, so nothing is tuned on the test clips.
It uses only lexicon.txt, never the answer key.

    python drug_hints.py                          # candidate quality on every ASR source
    python drug_hints.py --source avx2_base-q8_ur_t4 --show 5
"""
import argparse
from pathlib import Path

from nabzlib import RESULTS, ROOT, STOP, _allowed, find_term, levenshtein, load_key, read_manifest, skeleton, tokens

MIN_SKELETON = 4  # skeletons of 3 letters or fewer match too many ordinary words


def load_names(path=ROOT / "lexicon.txt"):
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        n = line.strip()
        if n and not n.startswith("#"):
            sk = "".join(skeleton(w) for w in tokens(n))
            if len(sk) >= MIN_SKELETON:
                out.setdefault(sk, n)
    return out  # skeleton -> display name


def candidates(text, names, max_ngram=3, top=10):
    """[(heard span, lexicon name, edit distance)], best first, one entry per lexicon name.
    A span may get several names ("پروفین" is within tolerance of both Brufen and Ibuprofen): the LLM chooses."""
    toks = [t for t in tokens(text) if not t.isdigit()]
    sk = [skeleton(t) for t in toks]
    best = {}
    for n in range(1, max_ngram + 1):
        for i in range(len(sk) - n + 1):
            if toks[i] in STOP or toks[i + n - 1] in STOP:
                continue
            w = "".join(sk[i:i + n])
            if len(w) < MIN_SKELETON:
                continue
            for vs, name in names.items():
                tol = _allowed(len(vs))
                if abs(len(w) - len(vs)) > tol:
                    continue
                d = levenshtein(w, vs)
                if d <= tol:
                    key = name
                    cand = (d / max(len(vs), 1), i, " ".join(toks[i:i + n]), name, d)
                    if key not in best or cand < best[key]:
                        best[key] = cand
    return [(span, name, d) for _, _, span, name, d in sorted(best.values())[:top]]


def hint_block(text, names):
    c = candidates(text, names)
    if not c:
        return ""
    lines = [f'- "{span}" may be {name}' for span, name, _ in c]
    return ("\n\nSound-alike matches from the drug list (automatic, often wrong; most are ordinary words):\n"
            + "\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", nargs="+")
    ap.add_argument("--show", type=int, default=0)
    args = ap.parse_args()
    key, names = load_key(), load_names()
    sources = args.source or sorted(p.name for p in (RESULTS / "asr").iterdir() if p.is_dir())
    clips = [c for c in read_manifest() if not c["clip"].startswith("conv_")]
    print(f"{'source':45} clips  key_drugs  in_hints  hints  hints_not_key")
    for src in sources:
        n = kd = hit = nh = fp = 0
        for c in clips:
            p = RESULTS / "asr" / src / c["speaker"] / f"{c['clip']}.txt"
            k = key["clips"].get(c["clip"])
            if not p.is_file() or not k:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            cands = candidates(text, names)
            got = [name for _, name, _ in cands]
            truth = [m["name"] for m in k["meds"]] + k["avoid"]
            n += 1
            kd += len(truth)
            hit += sum(1 for t in truth if any(find_term(g, key["drugs"].get(t, [t])) for g in got))
            nh += len(got)
            fp += sum(1 for g in got if not any(find_term(g, key["drugs"].get(t, [t])) for t in truth))
            if args.show and n <= args.show:
                print("   ", c["speaker"], c["clip"], truth, "->", [(s, nm) for s, nm, _ in cands])
        if n:
            print(f"{src:45} {n:5}  {kd:9}  {hit/kd:7.0%}  {nh:5}  {fp:13}")


if __name__ == "__main__":
    main()
