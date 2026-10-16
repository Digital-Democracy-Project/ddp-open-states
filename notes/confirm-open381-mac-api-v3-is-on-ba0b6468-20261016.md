# CONFIRM: the Mac's api-v3 is on the OPEN-381 build (`ba0b6468`) (Mac side, 2026-10-16)

Ramon reported the Mac's api-v3 is updated. I checked by behavior, read-only, through the Mac's api-v3: Arizona `HB 2014` now returns its versions in this order:

1. Introduced Version
2. HOUSE - Natural Resources, Energy & Water
3. HOUSE - Appropriations
4. **House Engrossed Version**
5. SENATE - Natural Resources

The House Engrossed Version now sits after the House committee documents and before the Senate ones, which is the new rule.

**This is not a GO.** It only satisfies the Mac-side condition for Part 3 of `request-open381-arizona-final-recompute-HOLD-until-ramon-says-go-20261016.md`. Part 1 (read-only) may proceed. Parts 2 and 3 still need a separate GO note from Ramon on this branch.
