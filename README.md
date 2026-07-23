# News Desk — Setup Guide

**You do not need to know how to code.** You will not write a single line. You are
copying some files to a website called GitHub, flipping three switches, and that's it.

Set aside about 20 minutes for the first time. After that it runs by itself forever.

---

## What you're building

A web page that collects crypto and finance news from about 20 news sites every 20
minutes, sorts it by topic, and groups together the different articles about the same
story. You open it on your phone three times a day, scan it, and pull out what you want
to post.

**It costs nothing. Ever.** No credit card, no free trial that expires.

---

## Words you'll see, in plain English

You'll bump into these on GitHub. Nothing here is complicated, it's just named oddly.

| What GitHub calls it | What it actually is |
|---|---|
| **Repository** (or "repo") | A folder. That's it. Your project lives in one. |
| **Commit** | Saving a change. Like pressing Save, but it asks you to describe what you changed. |
| **Actions** | A robot that runs your files on a timer. This is what fetches the news. |
| **Workflow** | The robot's instructions — when to run, and what to do. |
| **Pages** | Free website hosting. This is what turns your files into a real web page. |
| **Branch / main** | Ignore it. You only have one, it's called `main`, you'll never need another. |

---

# Part 1 — Unzip the files

1. Find the file I sent you, `narrative-news-desk.zip`, probably in your Downloads folder.
2. Double-click it. It becomes a normal folder.
3. Open the folder. You should see **five** files:

   ```
   build_feed.py     ← the part that goes and gets the news
   index.html        ← the page you'll actually look at
   sources.json      ← the list of news sites
   tags.json         ← the keywords behind each tag button
   README.md         ← this guide
   ```

That's all you need to see. There is a sixth file hidden inside a folder whose name
starts with a dot, which your computer deliberately hides from you. **Ignore it
completely** — Part 4 handles it a different way, and hunting for it will only frustrate
you.

Keep this folder open. You'll drag from it in Part 3.

---

# Part 2 — Make your account and your repository

### 2.1 — Sign up

1. Go to **github.com**
2. Click **Sign up**, top right.
3. Email, password, username. Your username becomes part of your web address later, so
   pick something you don't mind being public — `narrativelabs` rather than `bevan_xyz123`.
4. Verify your email. Choose the **Free** plan when it's offered.

### 2.2 — Create the repository

1. Once you're logged in, click the **+** in the top-right corner → **New repository**.
2. Fill in:
   - **Repository name:** `news-desk` — lowercase, no spaces. This goes in your web address.
   - **Description:** leave blank
   - **Public / Private:** choose **Public**. This one matters — see the box below.
   - **Add a README file:** leave this **unticked**
   - Everything else: leave alone
3. Click **Create repository** at the bottom.

You'll land on a mostly-empty page covered in instructions. Ignore all of them.

> **Why Public?**
> GitHub's robot is free without limits on public repositories. On private ones you get
> 2,000 minutes a month and this needs about 2,100 — you'd run out near the end of every
> month and the news would quietly stop arriving.
>
> "Public" means someone could read these files if they knew your exact address. There's
> nothing private in them — it's a list of news websites and some keywords. Your page
> won't show up in Google and nobody is going to stumble across it.

---

# Part 3 — Upload the files

1. On your new empty repository page, find the link **uploading an existing file** —
   it's in the middle of the page, inside a sentence of grey text. Click it.
2. You'll see a big dashed box: "Drag files here to add them to your repository."
3. Go to your unzipped folder. Select all five files — click the first, hold **Shift**,
   click the last.
4. **Drag them into the dashed box.** Wait a few seconds for the names to appear.
5. Scroll down. There's a text box and a green button below it.
6. Click the green **Commit changes** button.

You'll now see your five files listed. That's your folder, online.

---

# Part 4 — Add the timer file

This is the file your computer hides from you. Rather than hunting for it, you'll create
it directly on GitHub. It's just typing and pasting.

1. On your repository page, click **Add file** (button near the top right) →
   **Create new file**.
2. At the top there's a box for the filename. **Type this exactly**, including the dot
   and the slashes:

   ```
   .github/workflows/refresh.yml
   ```

   As you type each `/`, watch what happens — GitHub turns it into a folder by itself.
   That's the trick, and that's why we're doing it this way.

3. Click into the big empty area below.
4. **Copy everything** in the box below, and paste it in:

```yaml
name: Refresh news desk

on:
  schedule:
    - cron: "*/20 * * * *"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - run: pip install --quiet feedparser requests

      - name: Build feed.json
        run: python build_feed.py

      - name: Commit if changed
        run: |
          git config user.name  "news-desk-bot"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add feed.json
          git diff --staged --quiet || git commit -m "feed: $(date -u +'%Y-%m-%d %H:%M UTC')"
          git push
```

5. Scroll to the bottom, click the green **Commit changes...** button, then **Commit
   changes** again in the pop-up.

> **Be careful with spacing.** This kind of file cares about indentation. Copy and paste
> the whole block in one go — don't retype it, and don't add or remove spaces at the
> start of any line.

---

# Part 5 — Let the robot save its work

By default GitHub's robot is only allowed to *read* your files. It needs to *write* too,
so it can save the news it collects. One switch.

1. Click **Settings** — a tab along the top of your repository, with a gear icon.
2. In the left-hand menu, scroll down to **Actions**, click it, then click **General**.
3. Scroll right to the bottom, to a section headed **Workflow permissions**.
4. Select **Read and write permissions**.
5. Click **Save**.

If it was already set that way, nothing to do.

---

# Part 6 — Run it for the first time

1. Click the **Actions** tab along the top of your repository.
   - If a page appears asking you to enable workflows, click the green button to confirm.
2. In the left sidebar, click **Refresh news desk**.
3. On the right, click the **Run workflow** dropdown, then the green **Run workflow** button.
4. Wait about 5 seconds and **refresh the page**. A new row appears with a yellow dot —
   that means it's working. After a minute or two it becomes a **green tick**.

### Seeing what it actually did

Click that row, then click **refresh** in the panel that opens. You'll get a list of
steps. Click **Build feed.json** to expand it. You'll see one line per news site:

```
  ok  CoinDesk            18 items
  ok  Cointelegraph       23 items
  FAIL Bankless            0 items   [HTTPError: 404 ...]
```

**Some sites failing is completely normal and expected.** News sites change their
addresses without telling anyone. As long as most of them say `ok`, you're fine. Send me
this list and I'll clear out the dead ones.

### If you got a red X instead of a green tick

Click the row and read the last red line. Two things cause almost all of these:

- **"Permission denied" or "403"** near the end → Part 5 didn't save. Go back and redo it.
- **"yaml" or "line 12"** in the error → the paste in Part 4 lost its spacing. Delete
  that file and redo Part 4, copying the whole block in one go.

---

# Part 7 — Turn on the web page

1. Go to **Settings** (top tabs) → **Pages** (left-hand menu).
2. Under **Source**, choose **Deploy from a branch**.
3. Two dropdowns appear underneath. Set them to **main** and **/ (root)**.
4. Click **Save**.
5. **Wait about two minutes**, then refresh the page. A green box appears at the top with
   your address:

   ```
   https://YOUR-USERNAME.github.io/news-desk/
   ```

6. Click **Visit site**.

**That's it. You're done.** That address is permanent — bookmark it.

### Put it on your phone

Open the address in your phone's browser.

- **iPhone:** Share button → Add to Home Screen
- **Android:** three-dot menu → Add to Home screen

Now it sits on your phone like any other app.

---

# Part 8 — Using it every day

The page refreshes itself. Just open it.

**The five little bars** to the left of each story are the important part. They show how
many different news sites are running that same story. Five bars means everyone is
covering it — that's your signal it matters, and probably what to post about. One bar
means one outlet noticed. That's the whole point of this thing.

- **Tap a tag** at the top to show only that topic. Tap again to unselect. Tap several to
  combine them.
- **4H / 12H / 24H / 72H** — how far back to look. 4H for a morning check, 24H if you've
  been away.
- **Tap any story** to open it up. You'll see how each outlet worded the same event,
  which helps when you're deciding your own angle instead of repeating theirs.
- **Open** — reads the full article.
- **Copy headline + link** and **Copy all angles** — puts it on your clipboard, ready to
  paste wherever you write.
- **Mark used** — greys a story out so you don't post it twice. This is remembered on
  that device only, so your phone and your laptop won't agree with each other.

Top right shows when it last updated. If that goes past 90 minutes it turns yellow —
something's stuck. See Part 10.

---

# Part 9 — Changing the tags

The tag buttons come from `tags.json`, and you can edit it right in your browser.

1. On your repository page, click **tags.json**.
2. Click the **pencil icon**, top right of the file.
3. Edit. The format is a tag name, then the words that trigger it:

   ```
   "LIQUIDATION": ["liquidation", "liquidated", "long squeeze", "margin call"],
   ```

   Four rules that will save you pain:
   - Every word needs `"quote marks"` around it, with commas between them
   - The **last** item in a list gets **no** comma after it
   - To add a tag, copy an existing line and change it
   - To delete a tag, delete its whole line — the button disappears on the next run

   Matching is exact, so `etf` will not catch `etfs`. Put both in.

4. Click **Commit changes...** → **Commit changes**.
5. Go to **Actions** → **Refresh news desk** → **Run workflow** to see it straight away,
   or just wait 20 minutes.

> **If you break the file,** the robot turns red and the page keeps showing the last good
> news rather than breaking. Click the **History** button on the file (clock icon), find
> the version from before your edit, and restore it. Nothing is ever really lost.

Adding news sites works the same way, in `sources.json`. Send me a site you want and I'll
give you the exact line to paste.

---

# Part 10 — When something goes wrong

**The page says "No feed yet"**
The robot hasn't run successfully yet. Do Part 6.

**The page is blank, or says 404**
Pages hasn't finished setting up. Wait 5 minutes and try again. If it's still broken,
recheck Part 7 — the two dropdowns must say **main** and **/ (root)**.

**The clock in the corner turned yellow**
The news has gone stale. Go to **Actions** and look at the most recent run. A red X means
it failed, so open it and read the last red line. A green tick means it worked, and the
news sites themselves are unreachable — that usually fixes itself within the hour.

**It just stopped working after a couple of months**
GitHub switches off timers on repositories nobody has touched for 60 days. Go to
**Actions** and click the button to re-enable it if a banner is offering that.

**A tag stopped showing anything**
Nothing matched it in the last 72 hours. Switch the window to 72H to check. If it's still
empty, the keywords need broadening — Part 9.

**Everything is on fire**
Send me a screenshot of the red text in the Actions log. That log always says exactly
what went wrong, and I can read it even when it looks like nonsense.

---

## The one thing to be realistic about

RSS feeds run 20 to 60 minutes behind X/Twitter. Traders watching the timeline will have
a story before this board does.

That's a fine trade for what you're doing. This isn't built to beat anyone to a headline.
It's built so that three times a day you can see everything that happened, sorted, with a
clear signal of which stories the whole industry is covering. That's a different job, and
it's the one that actually makes content.
