"""Look for LaTeX that leaked into the rendered page as literal text.

The paper shipped for some time reading "as Section efsec:discussion reports".
The source said `Section~\\ref{sec:discussion}`; an editing pass turned the
backslash-r into a carriage return, which a later write normalised into a line
break, leaving the bare characters "ef{sec:discussion}" in the body text.

Nothing caught it. pdflatex did not warn, because "ef{sec:discussion}" is not a
malformed command - it is not a command at all, just words. The undefined
reference count stayed at zero for the same reason: no reference was made.

So the check has to run against the rendered output rather than the source. If
a brace, a backslash or a known command name survives into the text a reader
sees, something did not compile as intended.

    python check_paper_render.py [.texbuild/aimirror_ieee_paper.pdf]

Exits non-zero when residue is found.
"""
import glob
import re
import sys

# Command names that, stripped of their leading escape, still read as English
# fragments and so pass unnoticed: \ref -> "ef", \textbf -> "extbf",
# \begin -> "egin", \frac -> "rac", \newline -> "ewline".
REMNANTS = [
    "ef{", "efeq", "efsec", "eftable", "effig",
    "extbf", "extit", "exttt", "emph{", "egin{", "nd{",
    "rac{", "ewline", "ewcommand", "item{", "aption{", "abel{",
]


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None
    if not target:
        found = glob.glob(".texbuild/*.pdf") or glob.glob("*.pdf")
        if not found:
            print("no PDF found; build first")
            return 1
        target = found[0]

    try:
        from pypdf import PdfReader
    except ImportError:
        print("  render check skipped: pypdf not installed")
        return 0

    text = " ".join((p.extract_text() or "") for p in PdfReader(target).pages)
    flat = re.sub(r"\s+", " ", text)

    problems = []

    for token in REMNANTS:
        for m in re.finditer(re.escape(token), flat):
            problems.append((token, flat[max(0, m.start() - 60):m.start() + 40]))

    # Braces and backslashes have no business in rendered body text. Math and
    # code can legitimately carry them, so this is reported separately rather
    # than treated as the same certainty.
    stray = len(re.findall(r"[{}\\]", flat))

    if problems:
        print("  LATEX RESIDUE IN RENDERED TEXT:")
        for token, ctx in problems[:10]:
            print("    %-10s ...%s..." % (token, ctx.strip()))
    if stray:
        print("  note: %d brace/backslash characters in rendered text "
              "(check they are all intentional)" % stray)

    if not problems:
        print("  render check: clean")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
