# phonegluewc language packs

Word lists for the phonegluewc on-screen keyboard: suggestions, corrections, next word guesses and
long-press letters for 26 languages. The keyboard downloads a pack only when you add that language,
and checks each file against the sha256 in `index.tsv`. Nothing is sent back.

Languages: bs ca cs da de es et fr gl hr hu id is it lt lv nb nl pl pt ro sk sl sq sv tr

## Files

- `index.tsv`: code, file name, size, sha256 for each file
- `<code>/words.tsv`: plain letters typed, word, score, language tag
- `<code>/bigrams.tsv`: a word and the commonest words after it; `<s>` starts a sentence, `<*>` holds the commonest words overall
- `<code>/letters`: base key, letter, capital
- `tools/build.py`: builds all of the above

## Sources

Word frequencies come from [FrequencyWords](https://github.com/hermitdave/FrequencyWords) by Hermit Dave,
CC BY-SA 4.0. Words are kept only if the matching [LibreOffice dictionary](https://github.com/LibreOffice/dictionaries)
accepts them; the dictionaries are not included.

Next word counts come from the sentences of [Tatoeba](https://tatoeba.org/en/downloads) and its contributors,
CC BY 2.0 FR. Only counts of adjacent words are kept, up to ten next words for each word, and no sentence
is included. The counts are still derived from Tatoeba's sentences and are redistributed here under its terms.

Languages with few Tatoeba sentences have few next word guesses: bs, sq, sl, et, hr, gl and ca have
under 700 head words each, against about 4000 for de, es, fr, it and pt.

See `LICENSE`.

## Rebuild

    python3 -I tools/build.py SRC OUT [code ...]

SRC caches the downloads. Needs hunspell. Word list and dictionary downloads are pinned to a commit;
Tatoeba exports change weekly, so a rebuild can differ.
