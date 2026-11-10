"""Lexicon contextual biasing for Whisper decoding (shallow fusion over a token trie, with failure cancellation).

Each drug name in lexicon.txt is tokenized (" Panadol", " panadol", ...) into a trie. At each decoding step, for each
beam hypothesis:
  * tokens that start a drug name get +lam (the decoder may switch to the Latin drug name inside Urdu text);
  * if the hypothesis ends in a partial drug name of d tokens, tokens that continue it get +lam, and every token that
    abandons it gets -lam*d, which takes back the bonus already paid, so half-names are not rewarded
    (Zhao et al. 2019, "Shallow-fusion end-to-end contextual biasing").
Only drug-name tokens are touched; no prompt is used, because a prompt halved negation recall (RUN_NOTES, 9 Nov).

whisper.cpp exposes the same hook (whisper_full_params.logits_filter_callback), so this ports to the phone build.

    python run_asr_hf.py --model openai/whisper-base --lang ur --bias 2.0
"""
from transformers import LogitsProcessor

from nabzlib import ROOT


def lexicon_names(path=ROOT / "lexicon.txt"):
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]


def build_trie(tokenizer, names):
    seqs = set()
    for n in names:
        for v in {n, n.lower(), n.capitalize()}:
            for s in (" " + v, v):
                ids = tuple(tokenizer.encode(s, add_special_tokens=False))
                if ids:
                    seqs.add(ids)
    children, complete = {}, set(seqs)
    for s in seqs:
        for d in range(len(s)):
            children.setdefault(s[:d], set()).add(s[d])
    return children, complete, max(len(s) for s in seqs)


class TrieBias(LogitsProcessor):
    def __init__(self, tokenizer, lam=2.0, names=None):
        self.children, self.complete, self.depth = build_trie(tokenizer, names or lexicon_names())
        self.lam = lam
        self.roots = sorted(self.children[()])
        # Whisper's special tokens (timestamps, <|endoftext|>) sit at the top of the vocabulary
        self.first_special = tokenizer.convert_tokens_to_ids("<|endoftext|>")

    def __call__(self, input_ids, scores):
        lam = self.lam
        for row in range(input_ids.shape[0]):
            hist = input_ids[row].tolist()
            hist = [t for t in hist if t < self.first_special][-self.depth:]
            prefix = ()
            for d in range(min(len(hist), self.depth - 1), 0, -1):
                p = tuple(hist[-d:])
                if p in self.children:
                    prefix = p
                    break
            if prefix:
                d = len(prefix)
                if prefix not in self.complete:
                    scores[row] -= lam * d  # abandoning the partial name costs back what it was paid
                    nxt = list(self.children[prefix])
                    scores[row, nxt] += lam * d + lam
                else:
                    nxt = list(self.children[prefix])
                    scores[row, nxt] += lam
            scores[row, self.roots] += lam
        return scores


def factory(lam):
    from transformers import LogitsProcessorList
    return lambda tok: LogitsProcessorList([TrieBias(tok, lam)])
