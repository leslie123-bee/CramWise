# Turning Student Planner into a real Android app

This folder has everything needed to: (1) put your backend online so it works
from any phone, anywhere, and (2) build a real, installable Android app
(a proper `.apk` file) out of the app screens you already have.

None of this costs anything at this stage. Do the steps in order - each one
depends on the one before it.

You'll do this once. After it's set up, coming back to make changes is much
quicker.

---

## Part 1 - Put this code on GitHub

GitHub is just a place to store the code online so the next two tools
(Render and GitHub Actions) can reach it and build from it.

1. Go to github.com and create a free account, if you don't already have one.
2. Download **GitHub Desktop** (desktop.github.com) and sign in with that
   account. It's a normal Windows app, no command line needed.
3. In GitHub Desktop: **File > Add local repository**, and point it at this
   `student-planner-monorepo` folder (the one this file is in).
   - If it says the folder isn't a repository yet, click **create a
     repository** - just accept the defaults.
4. Click **Publish repository** (top of the window). Name it something like
   `student-planner`. Leave "Keep this code private" checked if you'd rather
   nobody else see it - that's fine, everything below still works with a
   private repository.
5. Once it's published, you're done with this part. You now have a private
   home for this code on GitHub.

---

## Part 2 - Put the backend online (Render)

Right now your backend only runs when your laptop is on and someone's on the
same WiFi. This step puts it on a server that's on all the time, so the app
works from anywhere with internet.

1. Go to render.com and create a free account (you can sign up with your
   GitHub account - it'll ask permission to see your repositories, that's
   normal and needed for step 4).
2. Click **New > Web Service**.
3. Choose **Build and deploy from a Git repository**, then select the
   `student-planner` repository you just published.
4. Fill in these fields:
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python3 server.py`
   - **Instance Type**: Free
5. Before clicking create, scroll to **Environment Variables** and add these
   (click "Add Environment Variable" for each one):

   | Key | Value |
   |---|---|
   | `JWT_SECRET` | `b59b002dda23db447797a6e95b17e2c6a54e549bed7615ae290ddb3de57c3922` |
   | `REQUIRE_STRONG_SECRET` | `1` |
   | `JWT_EXPIRES_IN_DAYS` | `30` |
   | `DB_PATH` | `./data/planner.db` |

   (That `JWT_SECRET` value was randomly generated just for you - you don't
   need to change it, but don't share it publicly since it's what keeps
   people's login sessions secure.)

6. Click **Create Web Service**. Render will build and start it - takes a
   couple of minutes the first time. When it says "Live", copy the URL shown
   at the top of the page - it'll look like:

   `https://student-planner-xxxx.onrender.com`

   **Save that URL somewhere** - you'll paste it into the Android app in
   Part 4.

7. One thing worth knowing: on Render's free tier, the server "falls
   asleep" after 15 minutes of no traffic, and the *next* request after that
   takes 30-60 seconds to wake it back up. That's normal, not a bug - later
   on, if that becomes annoying, Render has a small paid tier that keeps it
   always awake.

   Also worth knowing: the free tier's storage isn't permanent - if the
   service ever gets redeployed or restarted by Render, the database
   (everyone's saved subjects/sessions) can reset. Fine for testing; before
   real people rely on this day to day, ask me about attaching a persistent
   disk (a small Render setting) so data survives restarts.

---

## Part 3 - Build the actual Android app

This part uses GitHub's own computers to build the app, so nothing needs to
be installed on your laptop or phone for this step.

1. On github.com, open your `student-planner` repository.
2. Click the **Actions** tab near the top.
3. You'll see a workflow called **Build Android APK**. Click it.
4. Click the **Run workflow** button (top right of the list), then the green
   **Run workflow** button that appears.
5. Wait - this takes about 5-8 minutes. You can refresh the page; a yellow
   dot means it's running, a green check means it's done.
6. Once it's green, click into that run, scroll to the bottom to
   **Artifacts**, and download **student-planner-apk**. It downloads as a
   `.zip` - unzip it to get `app-debug.apk`. That file is the actual app.

---

## Part 4 - Install it on your phone

1. Get `app-debug.apk` onto your Android phone - easiest way is emailing it
   to yourself, or uploading it to Google Drive and opening Drive on your
   phone, or a WhatsApp message to yourself.
2. Tap the file on your phone to install it. Android will warn you about
   installing from outside the Play Store ("unknown sources") - this is
   expected for an app that isn't published yet. Tap through to allow it
   just for this file.
3. Open the app. The very first screen will ask for your **server
   address** - paste the Render URL you saved in Part 2
   (`https://student-planner-xxxx.onrender.com`), then tap **Save & connect**.
4. From here it works exactly like the version you tested on your laptop -
   sign up, set up your study days, add subjects, generate a plan.

If it ever can't connect, Profile > Server shows the address it's using and
lets you change it - handy if you rename the Render service later.

---

## What's still ahead for the Play Store itself

What you have after Part 4 is a real, working Android app you (and anyone
you send the file to) can install directly. Actually **listing** it on the
Play Store is a separate, later step that needs:

- A one-time $25 Google Play developer account (tied to your own Google
  account).
- A few pieces of store listing material: an app icon, a couple of
  screenshots, a short description, and a privacy policy page (required even
  for a simple app like this).
- A **release** build instead of the **debug** one from Part 3 - signed with
  a private key only you hold. I can add that to the GitHub Actions workflow
  when you're ready.
- Google's review, which is usually a few days for a first submission.

None of that is needed to actually use the app yourself right now - it's
only needed if/when you want it downloadable by anyone searching the Play
Store. Tell me when you're ready for that part and we'll go through it.
