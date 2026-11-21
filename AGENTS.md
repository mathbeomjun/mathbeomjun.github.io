# Instructions for AI assistants (Claude Code, Cowork, others)

This repository (https://mathbeomjun.github.io) generates Beomjun Choi's academic homepage, public CV and a private full record.
Read README.md first; it has the full "what goes where" table. Key rules:

1. Edit content only in `data/papers.bib`, `data/cv.yml`, `private/private.yml`. Do not hard-code content in templates.
2. Each of those files starts with a comment header explaining every field, with templates. Follow it.
3. NEVER commit or push `private/private.yml` or `private_out/`. They are in `.gitignore`; before any commit,
   show the staged file list and confirm these are absent.
4. Do not add facts that the owner has not confirmed (talks, positions, awards, grant amounts).
   If something comes from an email or document and is uncertain, put it in `private/private.yml` with "(확인 필요)".
   If `private/NOTES_FOR_AI.md` exists (it is not in the public repository), read it too: it lists
   owner-specific corrections and decisions.
5. Add new items at the TOP of each list. Keep BibTeX citation keys unchanged (private.yml refers to them).
6. arXiv links must be abstract pages (`https://arxiv.org/abs/...`); the build does this from `eprint`.
7. After editing, run `python build.py --no-pdf` (and `python build.py --record` if LaTeX is available) and
   fix any error before committing.
8. Design choices are deliberate (light ivory background, Source Serif 4, MaruBuri for Korean, Japandi-minimal);
   do not restyle unless asked. Colors live in `:root` variables in `assets/style.css`.
9. Communicate with the owner in Korean.
