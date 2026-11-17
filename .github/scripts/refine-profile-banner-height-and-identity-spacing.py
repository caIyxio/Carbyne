from pathlib import Path

path = Path("ios/Carbyne/Sources/ContentView.swift")
s = path.read_text()

# A wider banner aspect ratio makes the banner visibly shorter while retaining
# the user's uploaded image and full-width treatment.
old_ratio = ".aspectRatio(3.0, contentMode: .fit)"
if old_ratio not in s:
    raise SystemExit("Expected profile banner aspect ratio was not found.")
s = s.replace(old_ratio, ".aspectRatio(3.8, contentMode: .fit)", 1)

# Give the identity text a little breathing room below the banner, while
# keeping the avatar overlapping its lower edge. Apply to own and public views.
old_avatar = ".padding(.top, -48)"
if s.count(old_avatar) < 2:
    raise SystemExit(f"Expected both profile avatar offsets; found {s.count(old_avatar)}.")
s = s.replace(old_avatar, ".padding(.top, -40)", 2)

# The identity row's negative top padding pulled the username too close to the
# banner. Positive spacing separates the name/handle from the banner edge.
old_row = """.padding(.horizontal, 16)
                            .padding(.top, -2)"""
new_row = """.padding(.horizontal, 16)
                            .padding(.top, 10)"""
if old_row not in s:
    raise SystemExit("Own profile identity-row spacing not found.")
s = s.replace(old_row, new_row, 1)

old_public = """.padding(.horizontal, 16)
                    .padding(.top, -2)"""
new_public = """.padding(.horizontal, 16)
                    .padding(.top, 10)"""
if old_public not in s:
    raise SystemExit("Public profile identity-row spacing not found.")
s = s.replace(old_public, new_public, 1)

path.write_text(s)
print("Reduced profile banner height and added breathing room around the username while preserving avatar overlap.")
