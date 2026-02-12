"""
Check connected Android devices (laptop) and open TikTok.
Run from your laptop with the phone connected via USB or wireless ADB.
Scrolls feed, likes/comments ~10–20% of the time, tracks stats.
Comments are chosen randomly from comments.txt.
"""
import random
import subprocess
import uiautomator2 as u2
import time
import urllib.parse
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
COMMENTS_FILE = SCRIPT_DIR / "comments.txt"

# TikTok package name (official app from Play Store)
TIKTOK_PACKAGE = "com.zhiliaoapp.musically"

# Multiple selectors for Friends tab (bottom nav) — try in order to avoid errors if one changes
FRIENDS_SELECTORS = [
    ("text", "Friends"),
    ("resourceId", "com.zhiliaoapp.musically:id/men"),
    ("description", "Friends"),
    ("className_text", "android.widget.TextView", "Friends"),
]

# Multiple selectors for Inbox tab (bottom nav)
INBOX_SELECTORS = [
    ("description", "Inbox"),
    ("text", "Inbox"),
    ("resourceId", "com.zhiliaoapp.musically:id/mso"),
    ("className_text", "android.widget.TextView", "Inbox"),
]

# Multiple selectors for "New followers" item inside Inbox
NEW_FOLLOWERS_SELECTORS = [
    ("text", "New followers"),
    ("description", "New followers"),
    ("resourceId", "com.zhiliaoapp.musically:id/bur"),
    ("className_text", "android.widget.TextView", "New followers"),
]

# XPath for suggested friends rows on the suggested-friends page
SUGGESTED_FRIENDS_XPATH = '//*[@resource-id="com.zhiliaoapp.musically:id/hp9"]/android.widget.LinearLayout'
ZPJ_CONTAINER_RESOURCE_ID = "com.zhiliaoapp.musically:id/zpj"
CQB_CONTAINER_RESOURCE_ID = "com.zhiliaoapp.musically:id/cqb"

# Container on search results page whose children we want to dump (option 4)
LUP_CONTAINER_RESOURCE_ID = "com.zhiliaoapp.musically:id/lup"

# More button (search / grid view) — description "More", resourceId t3h, or text 更多
MORE_BUTTON_SELECTORS = [
    ("description", "More"),
    ("resourceId", "com.zhiliaoapp.musically:id/t3h"),
    ("text", "更多"),
    ("className_description", "android.widget.ImageView", "More"),
]

# Filter or Adjust button (search results) — description "Filters"/"Adjust", resourceIds dtb/j5t/ak7
FILTER_OR_ADJUST_SELECTORS = [
    ("description", "Filters"),
    ("description", "Adjust"),
    ("resourceId", "com.zhiliaoapp.musically:id/dtb"),
    ("resourceId", "com.zhiliaoapp.musically:id/j5t"),
    ("resourceId", "com.zhiliaoapp.musically:id/ak7"),
    ("text", "Filters"),
    ("className_description", "android.widget.Button", "Filters"),
    ("className_description", "android.widget.ImageView", "Adjust"),
]

# Latest filter button (search results sort) — text "Latest", resourceId aen
LATEST_BUTTON_SELECTORS = [
    ("description", "Latest"),
    ("text", "Latest"),
    ("resourceId", "com.zhiliaoapp.musically:id/aen"),
    ("className_text", "android.widget.Button", "Latest"),
]

# Apply button (Sort by modal) — confirms filter/sort selection
APPLY_BUTTON_SELECTORS = [
    ("description", "Apply"),
    ("text", "Apply"),
    ("className_text", "android.widget.Button", "Apply"),
]

# Recently uploaded filter (search results) — if visible, use instead of More → Filter/Adjust → Latest → Apply
RECENTLY_UPLOADED_SELECTORS = [
    ("description", "Recently uploaded"),
    ("text", "Recently uploaded"),
    ("className_text", "android.widget.Button", "Recently uploaded"),
]

# Multiple selectors for Like button (heart icon on video) — different resource-ids across versions/screens
LIKE_SELECTORS = [
    ("description", "Like"),
    ("resourceId", "com.zhiliaoapp.musically:id/f9g"),
    ("resourceId", "com.zhiliaoapp.musically:id/f9q"),
    ("resourceId", "com.zhiliaoapp.musically:id/d46"),
    ("className_description", "android.widget.ImageView", "Like"),
]

# Scroll / engagement settings
SCROLL_COUNT = 20
LIKE_CHANCE = 0.50           # Like 50% of posts
COMMENT_ON_LIKED_CHANCE = 0.30  # Of the posts we like, comment on 30% of those

# Multiple selectors for Comment button (speech bubble icon on video)
COMMENT_SELECTORS = [
    ("description", "Comment"),
    ("description", "Comments"),
    ("resourceId", "com.zhiliaoapp.musically:id/dxd"),  # Button "Read or add comments"
    ("resourceId", "com.zhiliaoapp.musically:id/dkc"),  # LinearLayout container (right-side icon)
    ("className_description", "android.widget.ImageView", "Comment"),
]


def prompt_user_settings():
    """Ask the user how to run the bot (mode, scroll/pages, like/comment percentages)."""
    banner = r"""
==================================================
                 T I K T O K   B O T
==================================================
"""
    print(banner)

    print("Choose how to start:")
    print("  1) Start from beginning (open TikTok and go to Friends)")
    print("  2) Continue from current feed (do NOT reopen TikTok)")
    print("  3) Start from Inbox tab (open TikTok and go to Inbox)")
    print("  4) Open TikTok search by keyword (latest)")
    mode = input("Mode [1/2/3/4] (default 1): ").strip()
    if mode not in {"1", "2", "3", "4"}:
        mode = "1"

    pages_to_process = 0
    search_keywords: list[str] = []

    # For Inbox-only mode (3), ask for number of suggested-friends pages
    if mode == "3":
        # How many suggested-friends pages to process
        default_pages = 1
        pages_raw = input(f"How many suggested-friends pages to process? (default {default_pages}): ").strip()
        pages_to_process = default_pages
        if pages_raw:
            try:
                v = int(pages_raw)
                if v > 0:
                    pages_to_process = v
            except ValueError:
                pass

        total_scrolls = 0  # not used in mode 3
    elif mode == "4":
        # Get one or more search keywords for TikTok deep-link search
        raw = input("Enter keyword(s) for TikTok search (comma-separated): ").strip()
        if raw:
            search_keywords = [k.strip() for k in raw.split(",") if k.strip()]
        # Number of scrolls after opening search and applying filters
        default_scrolls = SCROLL_COUNT
        scroll_raw = input(f"How many videos to scroll? (default {default_scrolls}): ").strip()
        total_scrolls = default_scrolls
        if scroll_raw:
            try:
                v = int(scroll_raw)
                if v > 0:
                    total_scrolls = v
            except ValueError:
                pass
    else:
        # Number of scrolls (feed modes only)
        default_scrolls = SCROLL_COUNT
        scroll_raw = input(f"How many videos to scroll? (default {default_scrolls}): ").strip()
        total_scrolls = default_scrolls
        if scroll_raw:
            try:
                v = int(scroll_raw)
                if v > 0:
                    total_scrolls = v
            except ValueError:
                pass

    # Like percentage (used in ALL modes)
    default_like_pct = int(LIKE_CHANCE * 100)
    like_raw = input(f"What percentage of posts/videos to LIKE? 0–100 (default {default_like_pct}%): ").strip()
    like_chance = LIKE_CHANCE
    if like_raw:
        try:
            v = int(like_raw)
            v = max(0, min(100, v))
            like_chance = v / 100.0
        except ValueError:
            pass

    # Comment percentage on liked posts (used in ALL modes)
    default_comment_pct = int(COMMENT_ON_LIKED_CHANCE * 100)
    comment_raw = input(
        f"What percentage of LIKED posts/videos to COMMENT on? 0–100 (default {default_comment_pct}%): "
    ).strip()
    comment_on_liked_chance = COMMENT_ON_LIKED_CHANCE
    if comment_raw:
        try:
            v = int(comment_raw)
            v = max(0, min(100, v))
            comment_on_liked_chance = v / 100.0
        except ValueError:
            pass

    print("\nSettings:")
    mode_label = {
        "1": "Start from beginning (Friends)",
        "2": "Continue from current feed",
        "3": "Start from Inbox tab",
        "4": "Open TikTok search by keyword",
    }.get(mode, "Start from beginning (Friends)")
    print(f"  Mode: {mode_label}")
    if mode == "3":
        print(f"  Suggested-friends pages: {pages_to_process}")
    elif mode in {"1", "2", "4"}:
        print(f"  Scrolls: {total_scrolls}")
    print(f"  Like chance: {like_chance:.0%} of posts/videos")
    print(f"  Comment chance: {comment_on_liked_chance:.0%} of liked posts/videos")
    print("--------------------------------------------------")

    # For modes 1 & 2, pages_to_process is unused and defaults to 0
    if mode != "3":
        pages_to_process = 0

    return mode, total_scrolls, like_chance, comment_on_liked_chance, pages_to_process, search_keywords


def load_comments_from_file(path=None):
    """Load comment lines from file (one per line). Skip empty and # lines. Returns list."""
    path = path or COMMENTS_FILE
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def get_random_comment(path=None):
    """Pick a random comment from comments.txt. Returns None if file missing or empty."""
    comments = load_comments_from_file(path)
    return random.choice(comments) if comments else None


def click_friends_tab(d, timeout=3.0):
    """Click the Friends tab using the first selector that finds the element."""
    for item in FRIENDS_SELECTORS:
        kind = item[0]
        try:
            if kind == "text":
                el = d(text=item[1])
            elif kind == "resourceId":
                el = d(resourceId=item[1])
            elif kind == "description":
                el = d(description=item[1])
            elif kind == "className_text" and len(item) == 3:
                el = d(className=item[1], text=item[2])
            else:
                continue
            if el.exists(timeout=timeout):
                el.click()
                return True
        except Exception:
            continue
    # XPath fallbacks (uiautomator2 xpath)
    for xpath in [
        '//*[@text="Friends"]',
        '//android.widget.TextView[@resource-id="com.zhiliaoapp.musically:id/men"]',
    ]:
        try:
            d.xpath(xpath).click()
            return True
        except Exception:
            continue
    return False


def click_more_button(d, timeout=3.0):
    """Click the More button (search/grid view) using description, resourceId, text, and parent XPaths."""
    for item in MORE_BUTTON_SELECTORS:
        kind = item[0]
        try:
            if kind == "description":
                el = d(description=item[1])
            elif kind == "resourceId":
                el = d(resourceId=item[1])
            elif kind == "text":
                el = d(text=item[1])
            elif kind == "className_description" and len(item) == 3:
                el = d(className=item[1], description=item[2])
            else:
                continue
            if el.exists(timeout=timeout):
                el.click()
                return True
        except Exception:
            continue
    # XPath fallbacks: by description, resourceId, text, and parent-based
    for xpath in [
        '//*[@description="More"]',
        '//*[@resource-id="com.zhiliaoapp.musically:id/t3h"]',
        '//android.widget.ImageView[@resource-id="com.zhiliaoapp.musically:id/t3h"]',
        '//android.widget.TextView[@text="更多"]',
        '//*[@resource-id="com.zhiliaoapp.musically:id/du"]//*[@description="More"]',
        '//*[@resource-id="com.zhiliaoapp.musically:id/t4"]//*[@text="更多"]',
    ]:
        try:
            d.xpath(xpath).click()
            return True
        except Exception:
            continue
    return False


def click_filter_or_adjust_button(d, timeout=3.0):
    """Click the Filter or Adjust button on search results using description, resourceId, text, and XPaths."""
    for item in FILTER_OR_ADJUST_SELECTORS:
        kind = item[0]
        try:
            if kind == "description":
                el = d(description=item[1])
            elif kind == "resourceId":
                el = d(resourceId=item[1])
            elif kind == "text":
                el = d(text=item[1])
            elif kind == "className_description" and len(item) == 3:
                el = d(className=item[1], description=item[2])
            else:
                continue
            if el.exists(timeout=timeout):
                el.click()
                return True
        except Exception:
            continue
    for xpath in [
        '//*[@description="Filters"]',
        '//*[@description="Adjust"]',
        '//*[@content-desc="Filters"]',
        '//*[@resource-id="com.zhiliaoapp.musically:id/dtb"]',
        '//*[@resource-id="com.zhiliaoapp.musically:id/j5t"]',
        '//*[@resource-id="com.zhiliaoapp.musically:id/ak7"]',
        '//*[@text="Filters"]',
        '//android.widget.Button[@resource-id="com.zhiliaoapp.musically:id/dtb"]',
        '//android.widget.ImageView[@resource-id="com.zhiliaoapp.musically:id/j5t"]',
        '//android.widget.TextView[@text="Filters"]',
    ]:
        try:
            d.xpath(xpath).click()
            return True
        except Exception:
            continue
    return False


def click_latest_button(d, timeout=3.0):
    """Click the Latest filter button on search results (text, resourceId, description, XPaths)."""
    for item in LATEST_BUTTON_SELECTORS:
        kind = item[0]
        try:
            if kind == "description":
                el = d(description=item[1])
            elif kind == "text":
                el = d(text=item[1])
            elif kind == "resourceId":
                el = d(resourceId=item[1])
            elif kind == "className_text" and len(item) == 3:
                el = d(className=item[1], text=item[2])
            else:
                continue
            if el.exists(timeout=timeout):
                el.click()
                return True
        except Exception:
            continue
    for xpath in [
        '//*[@text="Latest"]',
        '//*[@description="Latest"]',
        '//*[@resource-id="com.zhiliaoapp.musically:id/aen"]',
        '//android.widget.Button[@text="Latest"]',
        '//android.widget.Button[@resource-id="com.zhiliaoapp.musically:id/aen"]',
    ]:
        try:
            d.xpath(xpath).click()
            return True
        except Exception:
            continue
    return False


def click_apply_button(d, timeout=3.0):
    """Click the Apply button in the Sort by / filter modal (description, text, XPaths)."""
    for item in APPLY_BUTTON_SELECTORS:
        kind = item[0]
        try:
            if kind == "description":
                el = d(description=item[1])
            elif kind == "text":
                el = d(text=item[1])
            elif kind == "className_text" and len(item) == 3:
                el = d(className=item[1], text=item[2])
            else:
                continue
            if el.exists(timeout=timeout):
                el.click()
                return True
        except Exception:
            continue
    for xpath in [
        '//*[@text="Apply"]',
        '//*[@description="Apply"]',
        '//*[@content-desc="Apply"]',
        '//android.widget.Button[@text="Apply"]',
    ]:
        try:
            d.xpath(xpath).click()
            return True
        except Exception:
            continue
    return False


def click_recently_uploaded_button(d, timeout=3.0):
    """Click the 'Recently uploaded' filter button if visible (search results). Returns True if clicked."""
    for item in RECENTLY_UPLOADED_SELECTORS:
        kind = item[0]
        try:
            if kind == "description":
                el = d(description=item[1])
            elif kind == "text":
                el = d(text=item[1])
            elif kind == "className_text" and len(item) == 3:
                el = d(className=item[1], text=item[2])
            else:
                continue
            if el.exists(timeout=timeout):
                el.click()
                return True
        except Exception:
            continue
    for xpath in [
        '//*[@text="Recently uploaded"]',
        '//*[@description="Recently uploaded"]',
        '//android.widget.Button[@text="Recently uploaded"]',
    ]:
        try:
            d.xpath(xpath).click()
            return True
        except Exception:
            continue
    return False


def click_inbox_tab(d, timeout=3.0):
    """Click the Inbox tab using the first selector that finds the element."""
    for item in INBOX_SELECTORS:
        kind = item[0]
        try:
            if kind == "text":
                el = d(text=item[1])
            elif kind == "resourceId":
                el = d(resourceId=item[1])
            elif kind == "description":
                el = d(description=item[1])
            elif kind == "className_text" and len(item) == 3:
                el = d(className=item[1], text=item[2])
            else:
                continue
            if el.exists(timeout=timeout):
                el.click()
                return True
        except Exception:
            continue
    # XPath fallbacks for Inbox tab
    for xpath in [
        '//*[@content-desc="Inbox"]',
        '//*[@text="Inbox"]',
        '//android.widget.FrameLayout[@resource-id="com.zhiliaoapp.musically:id/mso"]',
    ]:
        try:
            d.xpath(xpath).click()
            return True
        except Exception:
            continue
    return False


def click_new_followers(d, timeout=3.0):
    """Click the 'New followers' row in Inbox using multiple selectors/XPaths."""
    for item in NEW_FOLLOWERS_SELECTORS:
        kind = item[0]
        try:
            if kind == "text":
                el = d(text=item[1])
            elif kind == "resourceId":
                el = d(resourceId=item[1])
            elif kind == "description":
                el = d(description=item[1])
            elif kind == "className_text" and len(item) == 3:
                el = d(className=item[1], text=item[2])
            else:
                continue
            if el.exists(timeout=timeout):
                el.click()
                return True
        except Exception:
            continue
    # XPath fallbacks for New followers
    for xpath in [
        '//*[@text="New followers"]',
        '//*[@content-desc="New followers"]',
        '//*[@resource-id="com.zhiliaoapp.musically:id/bur"]',
        '//android.widget.TextView[@text="New followers"]',
    ]:
        try:
            d.xpath(xpath).click()
            return True
        except Exception:
            continue
    return False


def print_suggested_friends(d, like_chance, comment_on_liked_chance, timeout=2.0):
    """Pretty-print suggested-friends rows and key child XPaths in a compact, readable way."""
    print("\n================ SUGGESTED FRIENDS ================")
    try:
        root = d.xpath(SUGGESTED_FRIENDS_XPATH)
        nodes = root.all()
    except Exception as e:
        print(f"[error] querying suggested friends xpath: {e}")
        return

    if not nodes:
        print(f"[info] No elements found for xpath:\n  {SUGGESTED_FRIENDS_XPATH}")
        print("===================================================\n")
        return

    print(f"[info] Base row xpath:\n  {SUGGESTED_FRIENDS_XPATH}")
    print(f"[info] Total rows: {len(nodes)}")
    for idx, node in enumerate(nodes, 1):
        # Construct an index-specific xpath like .../android.widget.LinearLayout[1]
        row_xpath = f"{SUGGESTED_FRIENDS_XPATH}[{idx}]"
        print("\n---------------------------------------------------")
        print(f"Row {idx}")
        print(f"  row xpath: {row_xpath}")
        try:
            # Query direct children via XPath rather than relying on .children()
            child_nodes = d.xpath(f"{row_xpath}/*").all()
        except Exception as e:
            print(f"  [warn] error getting direct children: {e}")
            continue

        if not child_nodes:
            print("  [info] no direct children")
        else:
            print(f"  [info] direct children: {len(child_nodes)}")
            for c in child_nodes:
                ci = {}
                try:
                    ci = c.info or {}
                except Exception:
                    pass
                c_class = ci.get("className") or ci.get("class")
                c_res = ci.get("resourceName") or ci.get("resource-id") or ci.get("resourceId")
                c_text = ci.get("text") or ""

                # Build child xpath under this row
                if c_res and c_class:
                    child_xpath = f'{row_xpath}/{c_class}[@resource-id="{c_res}"]'
                elif c_class:
                    child_xpath = f"{row_xpath}/{c_class}"
                else:
                    child_xpath = f"{row_xpath}/*"

                print(f"    - child: {child_xpath}")
                if c_text:
                    print(f"        text={c_text!r}")

        # Additionally, print XPaths of nodes inside the zpj container for this row
        try:
            zpj_base = f'{row_xpath}/*[@resource-id="{ZPJ_CONTAINER_RESOURCE_ID}"]'
            zpj_children = d.xpath(f"{zpj_base}/*").all()
        except Exception as e:
            print(f"  [warn] error getting zpj children: {e}")
            continue

        if not zpj_children:
            print(f"  [info] no children under zpj container ({ZPJ_CONTAINER_RESOURCE_ID})")
            continue

        print(f"  zpj children ({ZPJ_CONTAINER_RESOURCE_ID}):")
        for z in zpj_children:
            zi = {}
            try:
                zi = z.info or {}
            except Exception:
                pass
            z_class = zi.get("className") or zi.get("class")
            z_res = zi.get("resourceName") or zi.get("resource-id") or zi.get("resourceId")
            z_text = zi.get("text") or ""

            if z_res and z_class:
                z_xpath = f'{zpj_base}/{z_class}[@resource-id="{z_res}"]'
            elif z_class:
                z_xpath = f"{zpj_base}/{z_class}"
            else:
                z_xpath = f"{zpj_base}/*"

            print(f"    - {z_xpath}")
            if z_text:
                print(f"        text={z_text!r}")

        # Also print children under the cqb container (buttons etc.)
        try:
            # Search anywhere under this row for the cqb container, not only as a direct child of zpj
            cqb_base = f'{row_xpath}//*[@resource-id="{CQB_CONTAINER_RESOURCE_ID}"]'
            cqb_children = d.xpath(f"{cqb_base}/*").all()
        except Exception as e:
            print(f"  [warn] error getting cqb children: {e}")
            cqb_children = []

        if cqb_children:
            print(f"  cqb children ({CQB_CONTAINER_RESOURCE_ID}):")
            for btn in cqb_children:
                bi = {}
                try:
                    bi = btn.info or {}
                except Exception:
                    pass
                b_class = bi.get("className") or bi.get("class")
                b_res = bi.get("resourceName") or bi.get("resource-id") or bi.get("resourceId")
                b_text = bi.get("text") or ""
                if b_res and b_class:
                    b_xpath = f'{cqb_base}/{b_class}[@resource-id="{b_res}"]'
                elif b_class:
                    b_xpath = f"{cqb_base}/{b_class}"
                else:
                    b_xpath = f"{cqb_base}/*"
                print(f"    - {b_xpath}")
                if b_text:
                    print(f"        text={b_text!r}")
        # For each row:
        # 1) open EVERY video thumbnail under zpj (each android.view.ViewGroup child),
        #    run like/comment logic on that video, then go back to the suggested list
        # 2) then click the SECOND child under the cqb container (if present)
        vg_indices = []
        for pos, z in enumerate(zpj_children, start=1):
            try:
                zi = z.info or {}
            except Exception:
                continue
            z_class = zi.get("className") or zi.get("class")
            if z_class == "android.view.ViewGroup":
                vg_indices.append(pos)

        row_should_be_skipped = False
        if vg_indices:
            print(f"  [info] Found {len(vg_indices)} video(s) under zpj for this row.")
        for vid_num, child_pos in enumerate(vg_indices, start=1):
            video_xpath = f"{zpj_base}/android.view.ViewGroup[{child_pos}]"
            print(f"  [action] Opening video {vid_num} via {video_xpath} ...")
            try:
                d.xpath(video_xpath).click()
                time.sleep(1.5)

                # If ANY video for this suggested friend is already liked,
                # skip ALL actions for this friend (no like/comment/follow).
                if is_post_already_liked(d):
                    print(
                        f"[suggested row {idx} video {vid_num}] "
                        "already liked — skipping this suggested friend completely."
                    )
                    row_should_be_skipped = True
                    break

                like_and_comment_on_open_video(
                    d,
                    like_chance,
                    comment_on_liked_chance,
                    label_prefix=f"[suggested row {idx} video {vid_num}] ",
                )
            except Exception as e:
                print(f"  [warn] error opening/processing video {vid_num}: {e}")
            finally:
                try:
                    d.press("back")
                    time.sleep(0.5)
                except Exception:
                    pass

        # If any video was already liked, skip follow/button actions for this row
        if row_should_be_skipped:
            print("  [info] Suggested friend already interacted with — skipping follow/actions.")
            continue

        # After closing all videos, click the second child of cqb (e.g. follow button) if it exists
        if len(cqb_children) >= 2:
            print("  [action] Clicking second child under cqb for this row...")
            try:
                cqb_children[1].click()
                time.sleep(0.5)
            except Exception as e:
                print(f"  [warn] error clicking second cqb child: {e}")

    # After processing all rows, scroll a bit more on the suggested-friends list
    print("\n[action] Finished all suggested-friend rows on this page — scrolling suggested list...\n")
    try:
        swipe_up_suggested_page(d)
        time.sleep(0.8)
    except Exception as e:
        print(f"[warn] Error while scrolling suggested-friends page: {e}")

    print("================ END SUGGESTED FRIENDS ============\n")


def print_lup_children(d, timeout=2.0):
    """Print child XPaths under the 'lup' container on the search results page (option 4)."""
    base_xpath = f'//*[@resource-id="{LUP_CONTAINER_RESOURCE_ID}"]'
    try:
        nodes = d.xpath(base_xpath).all()
    except Exception as e:
        print(f"[warn] error querying lup container: {e}")
        return

    if not nodes:
        print(f"[info] No elements found for lup container xpath:\n  {base_xpath}")
        return

    print(f"[info] Found {len(nodes)} lup container(s) at xpath:\n  {base_xpath}")
    for idx, _node in enumerate(nodes, 1):
        container_xpath = f"{base_xpath}[{idx}]"
        print(f"  lup[{idx}] xpath: {container_xpath}")
        try:
            children = d.xpath(f"{container_xpath}/*").all()
        except Exception as e:
            print(f"    [warn] error getting direct children: {e}")
            continue

        if not children:
            print("    [info] no direct children")
            continue

        for c in children:
            info = {}
            try:
                info = c.info or {}
            except Exception:
                pass
            c_class = info.get("className") or info.get("class")
            c_res = info.get("resourceName") or info.get("resource-id") or info.get("resourceId")
            c_text = info.get("text") or ""

            if c_res and c_class:
                child_xpath = f'{container_xpath}/{c_class}[@resource-id="{c_res}"]'
            elif c_class:
                child_xpath = f"{container_xpath}/{c_class}"
            else:
                child_xpath = f"{container_xpath}/*"

            print(f"    - child: {child_xpath}")
            if c_text:
                print(f"        text={c_text!r}")


def click_first_lup_item_frame(d, timeout=3.0):
    """
    Click the first FrameLayout child under the lup container on the search results page.

    Based on the printed hierarchy, this corresponds to
    android.widget.FrameLayout with resource-id com.zhiliaoapp.musically:id/t4a.
    """
    base_xpath = f'//*[@resource-id="{LUP_CONTAINER_RESOURCE_ID}"][1]/android.widget.FrameLayout[@resource-id="com.zhiliaoapp.musically:id/t4a"]'
    try:
        nodes = d.xpath(base_xpath).all()
    except Exception as e:
        print(f"[warn] error querying first lup FrameLayout child: {e}")
        return False

    if not nodes:
        print(f"[info] No FrameLayout child found at xpath:\n  {base_xpath}")
        return False

    try:
        nodes[0].click()
        return True
    except Exception as e:
        print(f"[warn] error clicking first lup FrameLayout child: {e}")
        return False


def get_like_button(d, timeout=1.5):
    """Return the Like button element if found, else None. Does not click."""
    for item in LIKE_SELECTORS:
        kind = item[0]
        try:
            if kind == "description":
                el = d(description=item[1])
            elif kind == "resourceId":
                el = d(resourceId=item[1])
            elif kind == "className_description" and len(item) == 3:
                el = d(className=item[1], description=item[2])
            else:
                continue
            if el.exists(timeout=timeout):
                return el
        except Exception:
            continue
    try:
        for xpath in ['//*[@content-desc="Like"]', '//android.widget.ImageView[@resource-id="com.zhiliaoapp.musically:id/f9g"]']:
            x = d.xpath(xpath)
            if x.exists(timeout=0.5):
                return x
    except Exception:
        pass
    return None


def is_post_already_liked(d, timeout=1.5):
    """True if the current post is already liked (then we skip like and comment)."""
    el = get_like_button(d, timeout=timeout)
    if el is None:
        return False
    try:
        info = el.info
        if info is None:
            return False
        # When post is liked, the like button is often selected=True or checked=True
        if info.get("selected") or info.get("checked"):
            return True
        return False
    except Exception:
        return False


def click_like(d, timeout=2.0):
    """Click the Like (heart) button using the first selector that finds the element."""
    for item in LIKE_SELECTORS:
        kind = item[0]
        try:
            if kind == "description":
                el = d(description=item[1])
            elif kind == "resourceId":
                el = d(resourceId=item[1])
            elif kind == "className_description" and len(item) == 3:
                el = d(className=item[1], description=item[2])
            else:
                continue
            if el.exists(timeout=timeout):
                el.click()
                return True
        except Exception:
            continue
    # XPath fallbacks for Like button
    for xpath in [
        '//*[@content-desc="Like"]',
        '//android.widget.ImageView[@resource-id="com.zhiliaoapp.musically:id/f9g"]',
        '//android.widget.ImageView[@resource-id="com.zhiliaoapp.musically:id/f9q"]',
        '//*[@resource-id="com.zhiliaoapp.musically:id/d46"]',
        '//*[@resource-id="com.zhiliaoapp.musically:id/dk3s"]/android.widget.FrameLayout[2]',
    ]:
        try:
            d.xpath(xpath).click()
            return True
        except Exception:
            continue
    return False


def click_comment(d, timeout=2.0):
    """Click the Comment (speech bubble) button using the first selector that finds the element."""
    for item in COMMENT_SELECTORS:
        kind = item[0]
        try:
            if kind == "description":
                el = d(description=item[1])
            elif kind == "resourceId":
                el = d(resourceId=item[1])
            elif kind == "className_description" and len(item) == 3:
                el = d(className=item[1], description=item[2])
            else:
                continue
            if el.exists(timeout=timeout):
                el.click()
                return True
        except Exception:
            continue
    # XPath fallbacks for Comment button (contains() handles "Read or add comments. N comments")
    for xpath in [
        '//*[@content-desc="Comment"]',
        '//*[@content-desc="Comments"]',
        '//*[contains(@content-desc, "comment")]',
        '//*[@resource-id="com.zhiliaoapp.musically:id/dxd"]',
        '//android.widget.LinearLayout[@resource-id="com.zhiliaoapp.musically:id/dkc"]',
        '//android.widget.Button[@resource-id="com.zhiliaoapp.musically:id/dxd"]',
    ]:
        try:
            d.xpath(xpath).click()
            return True
        except Exception:
            continue
    return False


def get_comment_button(d, timeout=1.5):
    """Return the Comment button element if found, else None. Does not click."""
    for item in COMMENT_SELECTORS:
        kind = item[0]
        try:
            if kind == "description":
                el = d(description=item[1])
            elif kind == "resourceId":
                el = d(resourceId=item[1])
            elif kind == "className_description" and len(item) == 3:
                el = d(className=item[1], description=item[2])
            else:
                continue
            if el.exists(timeout=timeout):
                return el
        except Exception:
            continue
    try:
        for xpath in [
            '//*[@content-desc="Comment"]',
            '//*[@content-desc="Comments"]',
            '//*[@resource-id="com.zhiliaoapp.musically:id/dxd"]',
            '//android.widget.LinearLayout[@resource-id="com.zhiliaoapp.musically:id/dkc"]',
        ]:
            x = d.xpath(xpath)
            if x.exists(timeout=0.5):
                return x
    except Exception:
        pass
    return None


def has_zero_comments(d, timeout=1.5):
    """Return True if the visible comment button indicates '0 comments' (then we skip commenting)."""
    el = get_comment_button(d, timeout=timeout)
    if el is None:
        return False
    try:
        info = el.info or {}
    except Exception:
        return False
    desc = (
        info.get("contentDescription")
        or info.get("content-desc")
        or info.get("description")
        or ""
    )
    text = info.get("text") or ""
    combined = f"{desc} {text}".lower()
    # Examples: "Add and view comments. 0 comments"
    return "0 comments" in combined


def is_comments_turned_off(d, timeout=1.5):
    """True if the comment sheet shows comments disabled — then we should skip commenting and go back to feed."""
    for sel in [
        d(text="This creator turned off comments"),
        d(text="The creator limited content access"),
        d(textContains="creator limited content access"),
        d(text="The creator limited comment access"),
        d(textContains="creator limited comment access"),
        d(resourceId="com.zhiliaoapp.musically:id/det"),   # "The creator limited comment access" message
        d(resourceId="com.zhiliaoapp.musically:id/message_tv"),
    ]:
        try:
            if sel.exists(timeout=timeout):
                return True
        except Exception:
            continue
    return False


def is_in_comment_sheet(d, timeout=0.8):
    """True if the bot is currently in the comment sheet (not on the main feed)."""
    for sel in [
        d(className="android.widget.EditText"),
        d(resourceId="com.zhiliaoapp.musically:id/cex"),   # red Send button (comment sheet)
        d(resourceId="com.zhiliaoapp.musically:id/message_tv"),
    ]:
        if sel.exists(timeout=timeout):
            return True
    return False


def is_follow_friends_page(d, timeout=1.0):
    """True if the 'Follow your friends to watch their videos' page is shown — bot should stop scroll and process."""
    for sel in [
        d(text="Follow your friends to watch their videos"),
        d(description="Follow your friends to watch their videos"),
    ]:
        try:
            if sel.exists(timeout=timeout):
                return True
        except Exception:
            continue
    try:
        if d(textContains="Follow your friends").exists(timeout=timeout):
            return True
    except Exception:
        pass
    try:
        if d.xpath('//*[contains(@text, "Follow your friends")]').exists(timeout=timeout):
            return True
    except Exception:
        pass
    return False


def is_on_feed_page(d, timeout=1.5):
    """True if we appear to be on a TikTok video feed item.

    For safety we only require that EITHER Like OR Comment button exists (not necessarily both),
    and that we are not in the comment sheet, unless we explicitly detect a
    combination that clearly looks like a feed video.
    """
    like_el = get_like_button(d, timeout=timeout)
    comment_el = get_comment_button(d, timeout=timeout)
    # If we see Like/Comment AND an EditText, treat it as feed and skip the
    # comment-sheet check (requested behaviour).
    try:
        has_edit = d(className="android.widget.EditText").exists(timeout=timeout)
    except Exception:
        has_edit = False

    if has_edit and (like_el is not None or comment_el is not None):
        print("[info] Detected search/feed screen (EditText + Like/Comment) — treating as feed.")
        return True

    # Otherwise, if comment sheet is open, we're not on feed
    if is_in_comment_sheet(d, timeout=timeout):
        return False

    return like_el is not None or comment_el is not None


def ensure_on_feed(d, max_back=3):
    """If we're stuck in the comment sheet, press Back until we're on the feed. Avoids errors from scrolling/liking in comments."""
    for _ in range(max_back):
        try:
            # If we clearly see Like/Comment + EditText, treat as feed and stop.
            like_el = get_like_button(d, timeout=0.5)
            comment_el = get_comment_button(d, timeout=0.5)
            try:
                has_edit = d(className="android.widget.EditText").exists(timeout=0.5)
            except Exception:
                has_edit = False
            if has_edit and (like_el is not None or comment_el is not None):
                print("[info] ensure_on_feed: Search/feed screen detected (EditText + Like/Comment); no Back needed.")
                return

            if not is_in_comment_sheet(d):
                return
            d.press("back")
            time.sleep(0.4)
        except Exception:
            return


def post_random_comment(d, timeout=2.0):
    """
    After comment sheet is open: type a random comment from comments.txt and tap Send.
    Returns True if a comment was posted, False otherwise.
    """
    comment = get_random_comment()
    if not comment:
        return False
    try:
        # Focus/click comment input (EditText) then type
        inp = d(className="android.widget.EditText")
        if inp.exists(timeout=timeout):
            inp.click()
            time.sleep(0.3)
            inp.set_text(comment)
            time.sleep(0.4)
        else:
            d.send_keys(comment)
            time.sleep(0.4)
        # Tap red Send button after writing comment — from screenshot: id/cex (android.widget.Button)
        send_selectors = [
            d(resourceId="com.zhiliaoapp.musically:id/cex"),
        ]
        send_xpaths = [
            '//*[@resource-id="com.zhiliaoapp.musically:id/cex"]',
            '//android.widget.Button[@resource-id="com.zhiliaoapp.musically:id/cex"]',
        ]
        for _ in range(2):  # retry once
            for sel in send_selectors:
                if sel.exists(timeout=1.0):
                    sel.click()
                    time.sleep(0.3)
                    return True
            for xpath in send_xpaths:
                try:
                    d.xpath(xpath).click()
                    time.sleep(0.3)
                    return True
                except Exception:
                    continue
            time.sleep(0.3)
        return False
    except Exception:
        return False


def swipe_up_one_page(d, duration=0.5):
    """Swipe up one page (e.g. next TikTok video). Uses screen height for distance."""
    w, h = d.window_size()
    x1, y1 = w // 2, int(h * 0.75)
    x2, y2 = w // 2, int(h * 0.25)
    d.swipe(x1, y1, x2, y2, duration=duration)


def swipe_up_suggested_page(d, duration=0.9):
    """Scroll more aggressively on the suggested-friends list (cover ~full screen)."""
    w, h = d.window_size()
    # Start very low and end very high so we move almost a full screen.
    x1, y1 = w // 2, int(h * 0.92)
    x2, y2 = w // 2, int(h * 0.08)
    d.swipe(x1, y1, x2, y2, duration=duration)


def like_and_comment_on_open_video(d, like_chance, comment_on_liked_chance, label_prefix=""):
    """Apply like/comment logic on the CURRENTLY open video (used from suggested-friends mode)."""
    # If already liked, we don't like or comment
    if is_post_already_liked(d):
        if label_prefix:
            print(f"{label_prefix}Already liked — skip like/comment on this video")
        return

    did_like = False
    try:
        if random.random() < like_chance:
            if click_like(d):
                did_like = True
                if label_prefix:
                    print(f"{label_prefix}Liked video from suggested-friends")
            time.sleep(0.3)
    except Exception as e:
        if label_prefix:
            print(f"{label_prefix}Like error: {e}")

    try:
        if did_like and random.random() < comment_on_liked_chance:
            # Skip if the visible comment button shows "0 comments"
            if has_zero_comments(d):
                if label_prefix:
                    print(f"{label_prefix}0 comments shown — skipping comment on this video")
                return
            if click_comment(d):
                time.sleep(1.0)
                if is_comments_turned_off(d):
                    if label_prefix:
                        print(f"{label_prefix}Comments off — no comment")
                else:
                    if post_random_comment(d) and label_prefix:
                        print(f"{label_prefix}Comment posted on suggested-friends video")
                # Back from comment sheet to video
                d.press("back")
                time.sleep(0.4)
    except Exception as e:
        if label_prefix:
            print(f"{label_prefix}Comment error: {e}")


def get_connected_devices():
    """List Android devices connected via ADB (USB or wireless)."""
    out = subprocess.run(
        ["adb", "devices"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if out.returncode != 0:
        print("Error running adb. Is ADB installed and in PATH?")
        return []
    lines = out.stdout.strip().split("\n")[1:]  # skip "List of devices attached"
    devices = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices


def main():
    devices = get_connected_devices()
    if not devices:
        print("No Android devices connected.")
        print("Connect your phone via USB (with USB debugging on) or run: adb connect <ip>:5555")
        return

    print(f"Connected device(s): {len(devices)}")
    for i, serial in enumerate(devices, 1):
        print(f"  {i}. {serial}")

    # Use first device
    serial = devices[0]
    if len(devices) > 1:
        print(f"\nUsing first device: {serial}")

    # Prompt user for how to run the bot
    mode, total_scrolls, like_chance, comment_on_liked_chance, pages_to_process, search_keywords = prompt_user_settings()

    print(f"\nConnecting to {serial}...")
    try:
        d = u2.connect(serial)
    except Exception as e:
        print(f"Failed to connect to device: {e}")
        return

    print("Device info:", d.info.get("productName", serial))
    print("Screen size:", d.window_size())

    if mode == "1":
        # Start from beginning: open TikTok and go to Friends tab
        print(f"\nOpening TikTok ({TIKTOK_PACKAGE})...")
        d.app_start(TIKTOK_PACKAGE)
        print("TikTok launched.")
        time.sleep(2)
        print("\nClicking Friends tab...")
        if click_friends_tab(d):
            print("Friends tab clicked.")
        else:
            print("Could not find Friends tab. Try opening TikTok manually and run again.")
        time.sleep(1.5)
        print("\nFirst scroll from Friends...")
        try:
            swipe_up_one_page(d)
            time.sleep(0.6)
        except Exception as e:
            print(f"First scroll failed: {e}")
    elif mode == "2":
        # Continue from current feed without restarting TikTok
        print("\nStarting from current feed (no app restart / Friends navigation).")
        ensure_on_feed(d)
        if not is_on_feed_page(d):
            print(
                "Feed UI not clearly detected (no like/comment buttons found). "
                "Trying to scroll to find a video in the feed..."
            )
            feed_found = False
            for attempt in range(1, 3):  # try up to 2 scrolls
                try:
                    swipe_up_one_page(d)
                    time.sleep(0.8)
                    ensure_on_feed(d)
                    if is_on_feed_page(d):
                        print(f"  [info] Feed detected after scroll {attempt}.")
                        feed_found = True
                        break
                except Exception as e:
                    print(f"  [warn] Error during feed-detection scroll {attempt}: {e}")
                    break
            if not feed_found:
                print(
                    "Feed UI still not detected after scrolling.\n"
                    "Please manually open a TikTok video in the feed and run the bot again."
                )
                return
    elif mode == "3":
        # Start from Inbox tab
        print(f"\nOpening TikTok ({TIKTOK_PACKAGE})...")
        d.app_start(TIKTOK_PACKAGE)
        print("TikTok launched.")
        time.sleep(2)
        print("\nClicking Inbox tab...")
        if click_inbox_tab(d):
            print("Inbox tab clicked.")
        else:
            print("Could not find Inbox tab. Try opening TikTok manually and run again.")
        time.sleep(1.5)
        print("\nClicking 'New followers' row...")
        if click_new_followers(d):
            print("'New followers' opened.")
            time.sleep(1.5)
            # Process suggested-friends rows on multiple pages
            if pages_to_process <= 0:
                pages_to_process = 1
            for page in range(1, pages_to_process + 1):
                print(f"\n=== Suggested-friends page {page}/{pages_to_process} ===")
                print_suggested_friends(d, like_chance, comment_on_liked_chance)
        else:
            print("Could not find 'New followers' item in Inbox.")
        # For now, Inbox mode does not run the feed scrolling / like / comment loop
        return
    elif mode == "4":
        # Open TikTok search using deep-link(s) with user-provided keyword(s)
        if not search_keywords:
            print("No search keywords provided. Exiting.")
            return
        print("\nOpening TikTok search for keywords:")
        for idx, kw in enumerate(search_keywords, 1):
            encoded_kw = urllib.parse.quote(kw)
            url = f"snssdk1233://search?keyword={encoded_kw}"
            print(f"  {idx}. {kw!r} -> {url}")
            try:
                subprocess.run(
                    [
                        "adb",
                        "-s",
                        serial,
                        "shell",
                        "am",
                        "start",
                        "-a",
                        "android.intent.action.VIEW",
                        "-d",
                        url,
                    ],
                    check=False,
                    text=True,
                    capture_output=True,
                    timeout=10,
                )
                time.sleep(1.5)
                # Wait for search UI — if "Recently uploaded" is visible, use it; else More → Filter/Adjust → Latest → Apply
                time.sleep(2.0)
                if click_recently_uploaded_button(d, timeout=5.0):
                    print(f"  [action] Clicked Recently uploaded for {kw!r} (skipped More flow)")
                else:
                    if click_more_button(d, timeout=5.0):
                        print(f"  [action] Clicked More for {kw!r}")
                    else:
                        print(f"  [warn] More button not found for {kw!r}")
                    time.sleep(1.0)
                    if click_filter_or_adjust_button(d, timeout=5.0):
                        print(f"  [action] Clicked Filter/Adjust for {kw!r}")
                    else:
                        print(f"  [warn] Filter/Adjust button not found for {kw!r}")
                    time.sleep(1.0)
                    if click_latest_button(d, timeout=5.0):
                        print(f"  [action] Clicked Latest for {kw!r}")
                    else:
                        print(f"  [warn] Latest button not found for {kw!r}")
                    time.sleep(1.0)
                    if click_apply_button(d, timeout=5.0):
                        print(f"  [action] Clicked Apply for {kw!r}")
                    else:
                        print(f"  [warn] Apply button not found for {kw!r}")
                # After filters are applied (or Recently uploaded clicked), print child xpaths under lup container
                print("  [info] Dumping children under lup container on search results...")
                print_lup_children(d)
                # Then click the first FrameLayout child under lup (first result block)
                time.sleep(0.8)
                if click_first_lup_item_frame(d, timeout=5.0):
                    print(f"  [action] Clicked first FrameLayout item under lup for {kw!r}")
                else:
                    print(f"  [warn] Could not click first FrameLayout item under lup for {kw!r}")
            except Exception as e:
                print(f"  [warn] Error opening search for {kw!r}: {e}")
        # After setting up search/feed in option 4, fall through to the normal
        # like/comment + scroll loop below, starting from the opened video.

    if not load_comments_from_file():
        print("Note: comments.txt missing or empty — commenting will be skipped.")

    # Scroll N times: skip if already liked; else like some % of posts; comment on some % of those we like
    # (values are controlled by user input via prompt_user_settings)
    likes_done = 0
    comments_done = 0
    print(
        f"\nScrolling {total_scrolls} times "
        f"(like {like_chance:.0%} of posts, comment on {comment_on_liked_chance:.0%} of liked)"
    )
    print("-" * 50)

    for i in range(total_scrolls):
        try:
            # Ensure we're on feed (not stuck in comment sheet) before like/comment/scroll
            ensure_on_feed(d)

            # If "Follow your friends" page appeared, stop scroll and process
            if is_follow_friends_page(d):
                print(f"\n  [{i+1}/{total_scrolls}] 'Follow your friends' page detected — stopping.")
                break

            # If post is already liked, skip like and comment — just scroll
            if is_post_already_liked(d):
                print(f"  [{i+1}/{total_scrolls}] Already liked — skip")
                swipe_up_one_page(d)
                time.sleep(0.6)
                continue

            # Like some % of posts (only if not already liked)
            did_like = False
            try:
                if random.random() < like_chance:
                    if click_like(d):
                        likes_done += 1
                        did_like = True
                        print(f"  [{i+1}/{total_scrolls}] Liked")
                    time.sleep(0.3)
            except Exception:
                print(f"  [{i+1}/{total_scrolls}] Like button not found / error — skip, will scroll")

            # Comment on only some % of the posts we just liked
            try:
                if did_like and random.random() < comment_on_liked_chance:
                    if click_comment(d):
                        time.sleep(1.0)
                        if is_comments_turned_off(d):
                            print(f"  [{i+1}/{total_scrolls}] Comments off — back to feed")
                        else:
                            if post_random_comment(d):
                                comments_done += 1
                                print(f"  [{i+1}/{total_scrolls}] Comment posted")
                            else:
                                print(f"  [{i+1}/{total_scrolls}] Comment opened (post skipped)")
                            time.sleep(0.5)
                        d.press("back")
                        time.sleep(0.4)
                    time.sleep(0.3)
            except Exception:
                print(f"  [{i+1}/{total_scrolls}] Comment button not found / error — skip, will scroll")
                try:
                    d.press("back")
                except Exception:
                    pass

            # Scroll to next video (always, even if like/comment failed or button didn't appear)
            swipe_up_one_page(d)
            time.sleep(0.6)
        except Exception as e:
            print(f"  [{i+1}/{total_scrolls}] Error: {e}")
            try:
                ensure_on_feed(d)
            except Exception:
                pass
            try:
                swipe_up_one_page(d)
                time.sleep(0.6)
            except Exception:
                pass
            time.sleep(0.5)

    # Summary
    print("-" * 50)
    print("Done. Tracked stats:")
    print(f"  Scrolls: {total_scrolls}")
    print(f"  Likes:   {likes_done}")
    print(f"  Comments posted: {comments_done}")


if __name__ == "__main__":
    main()
