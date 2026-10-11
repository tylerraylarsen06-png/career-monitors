# career-monitors

Scheduled GitHub Actions monitors for career pages. One YAML file in `config/` per monitor.

## When asked to watch a firm ("watch JPMorgan's careers page")

1. Find the firm's official student, early-career or programs page. Prefer the page that lists programs over a job-search results page, which reorders on every load.
2. Fetch it with plain HTTP (`curl -sL -A "Mozilla/5.0" <url>`). The monitor does not run JavaScript, so if the listings are missing from the raw HTML, say so and suggest a different page.
3. Pick a `selector` that wraps the listings: `main`, an id, or a stable class. Omit it only if nothing stable exists.
4. Set `min_content_length` well below the scoped text length (500 is typical) so a bot-check page fails instead of counting as a change.
5. Write a `goal` from `profile.md` (or `profile.example.md`): what should alert, what to ignore.
6. Save as `config/<firm>-<page>.yaml`, kebab-case, using an existing file as the template.
7. Check that the YAML parses and the offline tests pass before committing:

   ```
   python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" config/<file>.yaml
   python3 -m unittest discover tests
   ```

8. Commit only the new config file. The first scheduled run records a baseline and sends nothing.

## Rules

- Never put secrets, webhook URLs or the ntfy topic in the repo. They live in Actions secrets.
- Never commit `state/` by hand. The workflow owns it.
- Keep `profile.md` free of anything you would not publish if the repo is public.
