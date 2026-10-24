import argparse
import re
import sys
from collections import Counter

# A "word" is a run of letters/digits, optionally joined by internal
# apostrophes or hyphens (e.g. "don't", "state-of-the-art").
WORD_PATTERN = re.compile(r"[A-Za-z0-9]+(?:['\u2019\-][A-Za-z0-9]+)*")

# Common abbreviations whose trailing period should not end a sentence.
ABBREVIATIONS = (
    "Mr", "Mrs", "Ms", "Dr", "Prof", "Sr", "Jr", "St", "vs", "etc",
    "Inc", "Ltd", "Co", "Corp", "Gen", "Gov", "Sen", "Rep", "Lt", "Col",
    "Sgt", "Capt", "Mt", "No", "U.S", "U.K", "e.g", "i.e", "a.m", "p.m",
)

# Small stop-word list, used only when the user asks to ignore filler words.
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "for",
    "from", "had", "has", "have", "he", "her", "his", "i", "in", "is", "it",
    "its", "of", "on", "or", "she", "that", "the", "their", "they", "this",
    "to", "was", "were", "will", "with", "would", "we", "you", "not", "after",
    "also", "than", "then", "there", "which", "who", "about", "into", "over",
}

SAMPLE_ARTICLE = """\
Kim Jong-un has visited China, inaugurating a bridge that connects the two 
countries and saying he hopes to expand cooperation with his neighbour.

The North Korean leader arrived in the Chinese border city of Dandong 
on Saturday after crossing the New Yalu River Bridge, according to South Korea’s 
unification ministry, which handles affairs related to North Korea, and 
China’s official Xinhua news agency.

He met Wang Huning, a member of the standing committee of China’s Communist 
party. The pair toured a car factory, and promised to strengthen the bilateral 
relationship.

Kim said his country “stands ready to work with China to carry forward their 
historical friendship and expand practical cooperation, thereby delivering 
tangible benefits to the peoples of both countries”, according to Xinhua.

Wang then accompanied Kim to the bridge to send him off, Xinhua said.
"""


# --------------------------------------------------------------------------
# Core analysis functions
# --------------------------------------------------------------------------
def tokenize(text: str) -> list[str]:
    """Return all words in the text, lowercased."""
    return [w.lower() for w in WORD_PATTERN.findall(text)]


def count_word_occurrences(text: str, target: str) -> int:
    """Count whole-word, case-insensitive occurrences of `target` in `text`."""
    target = target.strip().lower()
    if not target:
        raise ValueError("Target word must not be empty.")
    return tokenize(text).count(target)


def most_common_word(text: str, ignore_stop_words: bool = False):
    """
    Return (word, count) for the most frequent word, or None if no words.
    Ties are broken by whichever word appeared first in the text.
    """
    words = tokenize(text)
    if ignore_stop_words:
        words = [w for w in words if w not in STOP_WORDS]
    if not words:
        return None
    # Counter.most_common preserves first-seen order among equal counts.
    return Counter(words).most_common(1)[0]


def average_word_length(text: str) -> float:
    """Average number of characters per word (letters/digits only)."""
    words = WORD_PATTERN.findall(text)
    if not words:
        return 0.0
    total_chars = sum(len(re.sub(r"['\u2019\-]", "", w)) for w in words)
    return total_chars / len(words)


def count_paragraphs(text: str) -> int:
    """Paragraphs are blocks of text separated by one or more blank lines."""
    blocks = re.split(r"\n\s*\n", text.strip())
    return sum(1 for block in blocks if block.strip())


def count_sentences(text: str) -> int:
    """
    Count sentences by finding terminal punctuation (. ! ?) followed by
    whitespace/end of text, while ignoring abbreviations and decimals.
    """
    cleaned = text.strip()
    if not cleaned:
        return 0

    # Protect periods in abbreviations (e.g. "Dr.", "U.S.") and decimals.
    for abbr in ABBREVIATIONS:
        cleaned = re.sub(
            rf"\b{re.escape(abbr)}\.", abbr.replace(".", "<DOT>") + "<DOT>", cleaned
        )
    cleaned = re.sub(r"(?<=\d)\.(?=\d)", "<DOT>", cleaned)

    # A sentence ends at ., !, or ? (with optional closing quotes/brackets)
    # followed by whitespace or end of string.
    endings = re.findall(r"[.!?]+[\"'\u201d\u2019)\]]*(?=\s|$)", cleaned)
    count = len(endings)

    # Trailing text with no terminal punctuation still counts as a sentence.
    if not re.search(r"[.!?][\"'\u201d\u2019)\]]*\s*$", cleaned):
        count += 1
    return count


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------
def analyze(text: str, target_word: str | None = None,
            ignore_stop_words: bool = False) -> dict:
    """Run all analyses and return the results as a dictionary."""
    results = {
        "total_words": len(tokenize(text)),
        "most_common_word": most_common_word(text, ignore_stop_words),
        "average_word_length": average_word_length(text),
        "paragraph_count": count_paragraphs(text),
        "sentence_count": count_sentences(text),
    }
    if target_word:
        results["target_word"] = target_word
        results["target_count"] = count_word_occurrences(text, target_word)
    return results


def print_report(results: dict) -> None:
    line = "=" * 46
    print(f"\n{line}\n  NEWS ARTICLE ANALYSIS\n{line}")
    print(f"Total words           : {results['total_words']}")
    print(f"Paragraphs            : {results['paragraph_count']}")
    print(f"Sentences             : {results['sentence_count']}")
    print(f"Average word length   : {results['average_word_length']:.2f} characters")

    common = results["most_common_word"]
    if common:
        print(f"Most common word      : '{common[0]}' ({common[1]} times)")
    else:
        print("Most common word      : n/a (no words found)")

    if "target_word" in results:
        print(f"Occurrences of '{results['target_word']}' : {results['target_count']}")
    print(f"{line}\n")


# --------------------------------------------------------------------------
# Input handling / CLI
# --------------------------------------------------------------------------
def read_interactive() -> str:
    """Let the user paste text (end with a line containing only 'END')."""
    print("Paste your article below. Type END on its own line when finished.")
    print("(Leave it empty and type END to analyze a built-in sample article.)\n")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)
    text = "\n".join(lines).strip()
    if not text:
        print("\nNo text entered - using the sample article.")
        return SAMPLE_ARTICLE
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze the text of a news article.")
    parser.add_argument("-f", "--file", help="path to a text file containing the article")
    parser.add_argument("-w", "--word", help="specific word to count")
    parser.add_argument("--ignore-stop-words", action="store_true",
                        help="ignore common filler words (the, and, of...) "
                             "when finding the most common word")
    args = parser.parse_args()

    # Choose the input source: file -> piped stdin -> interactive prompt.
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            print(f"Error: could not read '{args.file}': {exc}", file=sys.stderr)
            return 1
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        text = read_interactive()

    if not text.strip():
        print("Error: the article is empty.", file=sys.stderr)
        return 1

    target = args.word
    if target is None and sys.stdin.isatty() and not args.file:
        target = input("Word to count (press Enter to skip): ").strip() or None

    print_report(analyze(text, target, args.ignore_stop_words))
    return 0


if __name__ == "__main__":
    sys.exit(main())