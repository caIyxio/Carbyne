from pathlib import Path

path = Path("ios/Carbyne/Sources/ContentView.swift")
s = path.read_text()

start = s.index("struct ProfileBannerView: View {")
end = s.index("\n}", start) + 2
banner = s[start:end]

# The previous patch changed only the outer aspect ratio. The image's
# GeometryReader still forced width / 3, so it kept the old tall height.
if "geometry.size.width / 3 + pullDistance" not in banner:
    raise SystemExit("Expected banner image height expression not found; refusing to guess.")
if ".aspectRatio(3.0, contentMode: .fit)" not in banner:
    raise SystemExit("Expected shared banner aspect ratio 3.0 not found.")
banner = banner.replace("geometry.size.width / 3 + pullDistance",
                        "geometry.size.width / 3.8 + pullDistance", 1)
banner = banner.replace(".aspectRatio(3.0, contentMode: .fit)",
                        ".aspectRatio(3.8, contentMode: .fit)", 1)
s = s[:start] + banner + s[end:]

# The three controls live in the own-profile banner overlay. Move that row
# upward from 54pt to 20pt; don't affect any other control padding.
own_start = s.index("struct ChannelScreen: View {")
own_end = s.index("\nstruct PublicChannelScreen: View {", own_start)
own = s[own_start:own_end]
overlay_start = own.index("ProfileBannerView(url: store.publicImageURL(path: profile.bannerPath))")
padding_index = own.index(".padding(.top, 54)", overlay_start)
own = own[:padding_index] + own[padding_index:].replace(".padding(.top, 54)", ".padding(.top, 20)", 1)
s = s[:own_start] + own + s[own_end:]

path.write_text(s)
print("Profile banner now uses 3.8:1 in both image sizing and container layout; banner controls move up 34pt.")
