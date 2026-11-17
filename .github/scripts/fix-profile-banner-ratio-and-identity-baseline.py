from pathlib import Path

path = Path("ios/Carbyne/Sources/ContentView.swift")
s = path.read_text()

# ProfileBannerView is shared by own and public profiles. Restore the 3:1
# banner ratio so both layouts use the same proportions as other profiles.
old_ratio = ".aspectRatio(3.8, contentMode: .fit)"
if s.count(old_ratio) != 1:
    raise SystemExit(f"Expected one shared 3.8 banner ratio, found {s.count(old_ratio)}.")
s = s.replace(old_ratio, ".aspectRatio(3.0, contentMode: .fit)", 1)

# Top-align the identity copy with the bottom of the banner. The avatar's
# negative top padding independently keeps it overlapping the banner.
own = """                            HStack(alignment: .center, spacing: 18) {
                                AvatarView(url: store.publicImageURL(path: profile.avatarPath), size: 88)"""
own_new = """                            HStack(alignment: .top, spacing: 18) {
                                AvatarView(url: store.publicImageURL(path: profile.avatarPath), size: 88)"""
if s.count(own) != 1:
    raise SystemExit(f"Expected one own-profile identity row, found {s.count(own)}.")
s = s.replace(own, own_new, 1)

public = """                    HStack(alignment: .center, spacing: 18) {
                        AvatarView(url: store.publicImageURL(path: profile.avatarPath), size: 88)"""
public_new = """                    HStack(alignment: .top, spacing: 18) {
                        AvatarView(url: store.publicImageURL(path: profile.avatarPath), size: 88)"""
if s.count(public) != 1:
    raise SystemExit(f"Expected one public-profile identity row, found {s.count(public)}.")
s = s.replace(public, public_new, 1)

# Keep the text a small distance below the banner; avatar overlap remains
# governed by its own -40 top padding.
path.write_text(s)
print("Restored the shared 3:1 profile banner and top-aligned name/username below it while preserving avatar overlap.")
