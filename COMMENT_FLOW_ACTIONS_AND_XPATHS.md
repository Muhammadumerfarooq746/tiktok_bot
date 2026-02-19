# Actions and XPaths After Clicking the Comment Button

This document lists **all actions** the bot performs and **all selectors/XPaths** used **after** the comment button is clicked (i.e. once the comment sheet is open).

---

## 1. Wait

- **Action:** `time.sleep(1.0)`  
- **Purpose:** Let the comment sheet open.

---

## 2. Check if comments are turned off

**Function:** `is_comments_turned_off(d, timeout=1.5)`

**Action:** Check whether the comment sheet shows “comments disabled”. If **True**, the bot skips typing and goes back to feed.

**Selectors used (in order):**

| # | Selector type | Value |
|---|----------------|--------|
| 1 | text | `"This creator turned off comments"` |
| 2 | text | `"The creator limited content access"` |
| 3 | textContains | `"creator limited content access"` |
| 4 | text | `"The creator limited comment access"` |
| 5 | textContains | `"creator limited comment access"` |
| 6 | resourceId | `com.zhiliaoapp.musically:id/det` |
| 7 | resourceId | `com.zhiliaoapp.musically:id/message_tv` |

**No XPaths** are used here; only the above uiautomator2 selectors.

---

## 3. Type comment and wait for you to tap Send

**Function:** `post_random_comment(d, timeout=2.0, comment_text=ai_comment)`

### 3.1 Comment input (EditText)

**Action:** Find the comment input, click it, then set the comment text.

**Selector:**

- **className:** `android.widget.EditText`  
  - Used as: `d(className="android.widget.EditText")`  
  - `.exists(timeout=2.0)`, `.click()`, `.set_text(comment)`  

**No XPath** is used for the EditText; only `className="android.widget.EditText"`.

If that fails, the bot falls back to: `d.send_keys(comment)` (no element selector).

---

### 3.2 Wait loop (check every 40 seconds, up to 2 minutes)

**Action:** Every **40 seconds**, read the **current text** of the comment input to see if you’ve sent (text gone) or not.

**Selector (same as above):**

- **className:** `android.widget.EditText`  
  - Used in: `_get_comment_edittext_text(d)`  
  - `.exists(timeout=0.5)` then `.get_text()` or `info["text"]`  

**No XPath** for this check.

**Logic:**

- If current text is **empty** or **no longer contains** the typed comment → treat as “Send detected” and return (caller will press Back once).
- If after **2 minutes** the comment is still in the EditText → bot presses **Back twice** and returns.

---

### 3.3 Send button (not clicked by the bot)

The bot **does not** tap the Send button; you tap it. The code does **not** use any Send button XPath or selector for clicking.

*(If you re-enable auto Send later, the Send selectors/XPaths would be: resourceId `cex`, `cg1`, description "Send"/"Post"/"@2131588253", and XPaths like `//*[@resource-id="com.zhiliaoapp.musically:id/cex"]`, etc.)*

---

## 4. Back to feed (caller)

**Action:** After `post_random_comment()` returns, the **caller** runs:

- `d.press("back")`  
- `time.sleep(0.4)`

So after the comment flow, the bot uses **one Back** (from the caller). If “2 min elapsed, Send not detected”, the bot has already pressed Back **twice** inside `post_random_comment`, so the caller’s Back is a third press in that case.

---

## Summary table (after comment button click)

| Step | Action | Selector / XPath |
|------|--------|-------------------|
| 1 | Sleep 1.0 s | — |
| 2 | Check comments off? | text, textContains, resourceId `det`, `message_tv` (no XPath) |
| 3a | Find & click comment input, set text | `className="android.widget.EditText"` (no XPath) |
| 3b | Every 40 s: read EditText text | `className="android.widget.EditText"` (no XPath) |
| 3c | (Optional) 2 min timeout: Back twice | — |
| 4 | Caller: Back once | — |

---

## Related: “Comment sheet” detection elsewhere

**Function:** `is_in_comment_sheet(d)` (used e.g. in `ensure_on_feed`)

Uses:

- `d(className="android.widget.EditText")`
- `d(resourceId="com.zhiliaoapp.musically:id/cex")` (Send button)
- `d(resourceId="com.zhiliaoapp.musically:id/message_tv")`

No XPaths; only these selectors.
