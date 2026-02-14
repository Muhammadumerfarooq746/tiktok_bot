# TikTok Bot — Mode Details

Detailed description of each mode and what the bot does in each one.

---

## How to run

- **On computer:** Connect the phone via USB (with USB debugging on) or via wireless ADB. Open a terminal in the project folder and run:  
  `python mian.py`  
  Then pick a mode and answer the questions (scroll count, like %, comment %, etc.).
- **On phone (Termux):** Install Python and dependencies in Termux, copy the project to the phone, then connect Termux to the same device using wireless debugging (see below). In Termux run:  
  `python mian.py`

### IP address and pair port (Termux / wireless ADB)

To run the bot from **Termux on the phone**, the phone must be connected to itself via wireless debugging so that `adb` (and uiautomator2) can talk to the device.

1. On the phone open **Settings → Developer options**.
2. Turn on **Wireless debugging**.
3. **Pairing (one-time):** Tap **“Pair device with pairing code”**.  
   - You will see **IP address : pair port** (e.g. `192.168.1.15:33089`) and a **6-digit pairing code**.  
   - In Termux run:  
     `adb pair 192.168.1.15:33089`  
     (use the IP and port shown; replace with your values.)  
   - When prompted, enter the 6-digit code.  
   - That pairing is saved; you don’t need to pair again unless you revoke it.
4. **Connect:** On the same **Wireless debugging** screen (not the pairing dialog), note the **“Device IP:port”** line — that is the **connection** port (often different from the pair port, e.g. `192.168.1.15:5555`).  
   In Termux run:  
   `adb connect 192.168.1.15:5555`  
   (again, use your phone’s IP and the connection port shown.)
5. Check: `adb devices` should list your device. Then run `python mian.py` in the project folder.

**Where to get the values:**  
- **IP address:** Shown on the Wireless debugging screen (and in the pairing dialog). It’s your phone’s Wi‑Fi IP (e.g. 192.168.1.15).  
- **Pair port:** Only in the “Pair device with pairing code” dialog (e.g. 33089). Use it only for `adb pair`.  
- **Connection port:** On the main Wireless debugging screen under “Device IP:port” (e.g. 5555). Use it for `adb connect` after pairing.

---

## Mode 1 — Start from beginning

**What it does:** Starts TikTok from scratch and runs the main feed like/comment/scroll loop.

**Steps:**

1. The bot **opens the TikTok app** on your phone (if it was closed).
2. It **clicks the Friends tab** so you are on the main “For You” / Friends feed.
3. It does **one initial scroll** to load the first video properly.
4. It then runs the **main loop** for the number of scrolls you chose:
   - On each video it checks if it’s already liked; if yes, it only scrolls.
   - Otherwise it may like (according to your like %) and, if it liked, may comment (according to your comment %).
   - Then it scrolls to the next video.
5. It stops after the set number of scrolls, or earlier if it hits the “Follow your friends to watch their videos” screen.

**When to use:** When you want the bot to take over from a cold start and work through the main feed.

---

## Mode 2 — Continue from current feed

**What it does:** Uses whatever is already on screen (no app restart) and runs the same like/comment/scroll loop.

**Steps:**

1. The bot **does not open or restart TikTok**. It assumes you already have the app open on a video (e.g. you left it on the feed).
2. It checks that it can see the feed (like/comment buttons). If not, it tries a couple of scrolls to find a video.
3. If the feed is still not detected, it tells you to open a video manually and run again.
4. Once on a video, it runs the **same main loop** as Mode 1: like/comment/scroll for the number of scrolls you set.
5. It stops after that many scrolls or when it sees the “Follow your friends” page.

**When to use:** When TikTok is already open on the feed and you want to continue from there without the bot reopening the app or touching the Friends tab.

---

## Mode 3 — Inbox (suggested friends)

**What it does:** Opens Inbox → “New followers”, then goes through suggested friends: opens each person’s videos, likes and comments on them, then follows the person. No main feed scroll.

**Steps:**

1. The bot **opens TikTok** and **clicks the Inbox tab**.
2. It **clicks “New followers”** to open the screen where TikTok suggests people to follow.
3. You choose **how many “pages”** of this suggested-friends list to process (e.g. 1, 2, 5).
4. For **each page**:
   - It finds every **suggested-friend row** on the page.
   - For each row it **opens every video** shown for that person (the small thumbnails).
   - On each opened video it runs the same **like/comment logic** (using your like % and comment %). If the video is already liked, it skips like and comment.
   - If **any** video for that suggested friend was already liked, the bot **skips the rest of that person** (no more videos, no follow).
   - After finishing all videos for a person, it **clicks the follow button** (second button in that row).
   - When the page is done, it **scrolls down** the suggested-friends list to load the next page.
5. It repeats step 4 for the number of pages you chose, then stops.

**When to use:** When you want to grow by engaging with “New followers” suggested accounts: watch their videos, like/comment, and follow them.

---

## Mode 4 — Keyword search

**What it does:** Opens TikTok search for your keyword(s), applies a time filter (Recently uploaded / Latest / Past 24 hours), opens the first search result, then runs the normal like/comment/scroll loop on that search feed.

**Steps:**

1. You enter **one or more search keywords** (comma-separated). The bot opens TikTok **search** for each keyword (via a deep link).
2. For each keyword it **waits for the search results** to load.
3. **Filter choice:**
   - If the **“Recently uploaded”** button is visible on the results screen, the bot **clicks it** and skips the rest of the filter menu.
   - Otherwise it **opens the filter/sort menu** (More → Filters/Adjust).
   - In the filter menu it tries to click **“Latest”** first. If “Latest” is not found, it tries **“Past 24 hours”**. If **neither** is found, it **closes the filter** (Back) and does not click Apply.
   - If it did click Latest or Past 24 hours, it then **clicks Apply** to confirm.
4. It **prints the list of child elements** under the search results container (for debugging/info).
5. It **clicks the first result** (first FrameLayout item in the results grid) to open that video.
6. From there it runs the **same main loop** as Modes 1 and 2: like/comment/scroll for the number of scrolls you set. So you get a “search feed” sorted by latest (or past 24h), and the bot scrolls through that feed liking and commenting.
7. You can enter **multiple keywords**; the bot runs the above (steps 2–6) for each keyword. After the last keyword it continues into the scroll loop from the last opened video.

**When to use:** When you want to target a specific topic (e.g. “car”, “cats”), see the latest or recent results, and have the bot like/comment/scroll on that search feed.

---

## Summary table

| Mode | Starts from | Main action |
|------|-------------|------------|
| **1** | App open → Friends tab → first scroll | Like/comment/scroll on main feed for N scrolls |
| **2** | Current screen (no restart) | Same like/comment/scroll on current feed for N scrolls |
| **3** | App open → Inbox → New followers | Suggested friends: open each person’s videos, like/comment, follow; repeat for N pages |
| **4** | Search by keyword(s) | Filter (Recently uploaded / Latest / Past 24h) → first result → like/comment/scroll for N scrolls |

In all modes, the bot uses your **like %** and **comment %** (and in mode 3/4 your other choices) and reads comments from **`comments.txt`** when it posts a comment.
