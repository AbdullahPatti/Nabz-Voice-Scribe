"""Lexicon biasing WITHOUT the chain guard, for the "no chain guard" rows of the biasing table (RUN_NOTES).

asr_bias.py as committed always applies the guard (no bonus for starting a new name right after a finished one).
The A4000 runs tagged hf_base_ur_bias<λ> (no "_cg") were made before the guard existed. This reproduces them
without editing asr_bias.py: the same TrieBias, with the root bonus paid at every step.

    python rerun_bias_noguard.py 2 4 6 8 10        # Hadi only, tags hf_base_ur_bias2 ... hf_base_ur_bias10
"""
import sys

from transformers import LogitsProcessorList

from asr_bias import TrieBias
from run_asr_hf import Transcriber, run, select_clips


class TrieBiasNoGuard(TrieBias):
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
                    scores[row] -= lam * d
                    scores[row, list(self.children[prefix])] += lam * d + lam
                else:
                    scores[row, list(self.children[prefix])] += lam
            scores[row, self.roots] += lam  # no chain guard: a new name may start at any step
        return scores


def main():
    clips = select_clips(["hadi"])
    for lam in [float(x) for x in sys.argv[1:]]:
        t = Transcriber("openai/whisper-base", "ur",
                        logits_processor_factory=lambda tok, lam=lam: LogitsProcessorList([TrieBiasNoGuard(tok, lam)]))
        run(t, f"hf_base_ur_bias{lam:g}", "openai/whisper-base", "ur", clips)


if __name__ == "__main__":
    main()
