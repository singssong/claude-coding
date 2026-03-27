# TODOS

## 당신에게 재생성 버튼 (Profile Change Invalidation)
**What:** Settings page button to clear all `why_for_user` values when user updates their profile significantly.
**Why:** Editing `user_profile.json` changes how future articles are processed, but existing DB entries still have `why_for_user` generated from the old profile. No way to know a callout is stale.
**Pros:** Profile changes take full effect immediately. No stale personalization.
**Cons:** Requires a settings page UI change + a new DELETE endpoint. Minor scope expansion.
**Context:** Added during /plan-eng-review after outside voice flagged that there's no profile version tracking in the articles table. For now, workaround is: manually run crawl after a profile change (existing rows will be overwritten for top-5 at next crawl).
**Depends on:** None. Can be built independently.

## Extend Eager why_for_user Generation to Top-10
**What:** Run `_translate_top_articles_with_profile()` for top-10 articles instead of top-5 at crawl time.
**Why:** The compact 6-10 section shows no "당신에게" callout unless user clicks to expand. Inconsistent experience compared to top-5.
**Pros:** All visible articles have callouts on page load. Consistent UX.
**Cons:** +5 Gemini calls per crawl (~5-10s extra). Marginal for manual crawl.
**Context:** Added during /plan-eng-review. Current decision: top-5 only to minimize crawl time on first ship. Revisit after using the feature for a week.
**Depends on:** Narrative Morning Briefing feature must be shipped first.
