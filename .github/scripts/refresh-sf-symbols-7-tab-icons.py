from pathlib import Path
import re

source = Path("ios/Carbyne/Sources/CarbyneNativeTabController.swift")
if not source.is_file():
    raise SystemExit(f"Swift tab controller not found: {source}")

text = source.read_text()

# Keep Carbyne's original five destinations and order:
# Home, Spotlights, Upload, DMs, Profile.
# Use Apple's native SF Symbols with Instagram-like outline/solid states.
# Do not alter the tab bar tint, accent color, layout, or destination behavior.
symbol_block = """    private static let unselectedSymbols = [
        "house",
        "movieclapper",
        "plus.app",
        "paperplane",
        "person.crop.circle.fill"
    ]
    private static let selectedSymbols = [
        "house.fill",
        "movieclapper.fill",
        "plus.app.fill",
        "paperplane.fill",
        "person.crop.circle.fill"
    ]
    private static let tabSymbolConfiguration = UIImage.SymbolConfiguration(
        pointSize: 25, weight: .regular, scale: .medium
    )"""

# Replace whichever previous tab-symbol definition exists.
patterns = [
    re.compile(r'    private static let unselectedSymbols = \[.*?\]\n'
               r'    private static let selectedSymbols = \[.*?\]\n'
               r'    private static let tabSymbolConfiguration = UIImage\.SymbolConfiguration\(.*?\n    \)\n',
               re.S),
    re.compile(r'    private static let symbols = \[.*?\]\n', re.S),
]
replaced = False
for pattern in patterns:
    if pattern.search(text):
        text = pattern.sub(symbol_block + "\n", text, count=1)
        replaced = True
        break
if not replaced:
    raise SystemExit("Could not locate existing tab symbol definitions.")

# Apply outline/filled variants to the same four existing tabs.
old_images = """                image: UIImage(systemName: Self.symbols[index]),
                selectedImage: UIImage(systemName: Self.symbols[index])"""
new_images = """                image: UIImage(
                    systemName: Self.unselectedSymbols[index],
                    withConfiguration: Self.tabSymbolConfiguration
                ),
                selectedImage: UIImage(
                    systemName: Self.selectedSymbols[index],
                    withConfiguration: Self.tabSymbolConfiguration
                )"""
if old_images in text:
    text = text.replace(old_images, new_images, 1)
elif "Self.unselectedSymbols[index]" not in text or "Self.selectedSymbols[index]" not in text:
    raise SystemExit("Could not locate existing tab item image initializer.")

# Remove the prior mistaken tint override. Preserve Carbyne's own colors.
text = text.replace(
    "        // Instagram-like monochrome navigation, without changing layout.\n"
    "        controller.tabBar.tintColor = .label\n"
    "        controller.tabBar.unselectedItemTintColor = .label\n",
    ""
)

expected = [
    '"house"', '"movieclapper"', '"plus.app"', '"paperplane"',
    '"house.fill"', '"movieclapper.fill"', '"plus.app.fill"', '"paperplane.fill"'
]
for symbol in expected:
    if symbol not in text:
        raise SystemExit(f"Missing expected Carbyne SF Symbol: {symbol}")

if "Self.tabs = [" in text or ".home, .moments, .upload, .messages, .channel" not in text:
    raise SystemExit("The original Carbyne tab destinations/order appear to have changed.")
if "updateAvatar(" not in text:
    raise SystemExit("Profile avatar updater is missing; refusing to alter the fifth tab.")

source.write_text(text)
print("Applied native SF Symbol Instagram-style glyph treatment to existing Home, Spotlights clapperboard, Upload plus-square, and DMs paperplane tabs. Preserved Carbyne colors, layout, order, actions, and live profile avatar.")
