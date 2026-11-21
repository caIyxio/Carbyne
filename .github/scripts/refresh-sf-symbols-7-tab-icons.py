from pathlib import Path
import re

source = Path("ios/Carbyne/Sources/CarbyneNativeTabController.swift")
if not source.is_file():
    raise SystemExit(f"Swift tab controller not found: {source}")

text = source.read_text()

# Preserve Carbyne's five destinations and their order. Only the glyph
# treatment changes: regular outline when inactive, filled when selected.
symbols = """    private static let unselectedSymbols = [
        "house",
        "movieclapper",
        "plus.square",
        "paperplane",
        "person.crop.circle.fill"
    ]
    private static let selectedSymbols = [
        "house.fill",
        "movieclapper.fill",
        "plus.square.fill",
        "paperplane.fill",
        "person.crop.circle.fill"
    ]
    private static let tabSymbolConfiguration = UIImage.SymbolConfiguration(
        pointSize: 25, weight: .regular, scale: .medium
    )"""

pattern = re.compile(
    r'    private static let symbols = \[.*?\]\n',
    re.S
)
if pattern.search(text):
    text = pattern.sub(symbols + "\n", text, count=1)
else:
    pair_pattern = re.compile(
        r'    private static let unselectedSymbols = \[.*?\]\n'
        r'    private static let selectedSymbols = \[.*?\]\n'
        r'(?:    private static let tabSymbolConfiguration = .*?\n(?:        .*?\n)*?)?',
        re.S
    )
    if pair_pattern.search(text):
        text = pair_pattern.sub(symbols + "\n", text, count=1)
    else:
        raise SystemExit("Could not locate the existing tab symbol definitions.")

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
elif "Self.unselectedSymbols[index]" not in text:
    raise SystemExit("Could not locate the tab item image initializer.")

if "controller.tabBar.tintColor = .label" not in text:
    needle = "        controller.tabBar.isTranslucent = true"
    if needle not in text:
        raise SystemExit("Could not locate native tab bar setup.")
    text = text.replace(
        needle,
        needle + "\n"
        + "        // Instagram-like monochrome navigation, without changing layout.\n"
        + "        controller.tabBar.tintColor = .label\n"
        + "        controller.tabBar.unselectedItemTintColor = .label",
        1
    )

expected = [
    '"house"', '"movieclapper"', '"plus.square"', '"paperplane"',
    '"house.fill"', '"movieclapper.fill"', '"plus.square.fill"', '"paperplane.fill"'
]
for symbol in expected:
    if symbol not in text:
        raise SystemExit(f"Missing expected Carbyne tab symbol: {symbol}")

if "updateAvatar(" not in text:
    raise SystemExit("Profile avatar updater is missing; refusing to alter the fifth tab.")

source.write_text(text)
print("Applied Instagram-like monochrome icon styling: consistent regular-weight outline glyphs, filled selected glyphs, black tint. Preserved Home, Spotlights, Upload, DMs, and live Profile avatar in their existing positions.")
