from pathlib import Path
import re

source = Path("ios/Carbyne/Sources/CarbyneNativeTabController.swift")
if not source.is_file():
    raise SystemExit(f"Swift tab controller not found: {source}")

text = source.read_text()

# Replace SF Symbol names with custom vector artwork. These are not symbol
# substitutions: each tab gets hand-drawn paths using Instagram-like geometry.
# Carbyne's own tab order, color tint, destinations, and avatar stay unchanged.
start = text.find("    private static let unselectedSymbols = [")
if start < 0:
    raise SystemExit("Could not find the current tab symbol arrays.")
end_marker = "    )"
config_start = text.find("    private static let tabSymbolConfiguration =", start)
if config_start < 0:
    raise SystemExit("Could not find tab symbol configuration.")
config_end = text.find(end_marker, config_start)
if config_end < 0:
    raise SystemExit("Could not find end of tab symbol configuration.")
config_end = text.find("\n", config_end) + 1

text = text[:start] + text[config_end:]

old_images = """                image: UIImage(
                    systemName: Self.unselectedSymbols[index],
                    withConfiguration: Self.tabSymbolConfiguration
                ),
                selectedImage: UIImage(
                    systemName: Self.selectedSymbols[index],
                    withConfiguration: Self.tabSymbolConfiguration
                )"""
new_images = """                image: CarbyneTabGlyph.image(for: index, selected: false),
                selectedImage: CarbyneTabGlyph.image(for: index, selected: true)"""
if old_images not in text:
    raise SystemExit("Expected SF Symbol image initializer was not found.")

text = text.replace(old_images, new_images, 1)

if "enum CarbyneTabGlyph" in text:
    raise SystemExit("Custom tab glyph renderer already exists; refusing to duplicate it.")

glyph_renderer = r'''

/// Custom tab glyphs drawn as vector paths so their construction, proportions,
/// and rounded strokes match Instagram's restrained navigation style.
/// Images use template rendering, so Carbyne's existing selected/unselected
/// tint colors remain in control. The profile slot is still supplied by avatar.
private enum CarbyneTabGlyph {
    private static let canvas = CGSize(width: 28, height: 28)
    private static let lineWidth: CGFloat = 2.55

    static func image(for index: Int, selected: Bool) -> UIImage? {
        guard (0...3).contains(index) else {
            return UIImage(systemName: "person.crop.circle.fill")
        }

        let renderer = UIGraphicsImageRenderer(size: canvas)
        let image = renderer.image { _ in
            UIColor.black.setStroke()
            UIColor.black.setFill()

            switch index {
            case 0: drawHome(selected: selected)
            case 1: drawClapperboard()
            case 2: drawUpload()
            case 3: drawPaperPlane()
            default: break
            }
        }
        return image.withRenderingMode(.alwaysTemplate)
    }

    private static func stroke(_ path: UIBezierPath, width: CGFloat = lineWidth) {
        path.lineWidth = width
        path.lineCapStyle = .round
        path.lineJoinStyle = .round
        path.stroke()
    }

    private static func drawHome(selected: Bool) {
        if selected {
            let house = UIBezierPath()
            house.move(to: CGPoint(x: 3.2, y: 13.1))
            house.addLine(to: CGPoint(x: 14, y: 3.5))
            house.addLine(to: CGPoint(x: 24.8, y: 13.1))
            house.addLine(to: CGPoint(x: 22.1, y: 13.1))
            house.addLine(to: CGPoint(x: 22.1, y: 23.5))
            house.addQuadCurve(to: CGPoint(x: 20.1, y: 25.5), controlPoint: CGPoint(x: 22.1, y: 25.5))
            house.addLine(to: CGPoint(x: 7.9, y: 25.5))
            house.addQuadCurve(to: CGPoint(x: 5.9, y: 23.5), controlPoint: CGPoint(x: 5.9, y: 25.5))
            house.addLine(to: CGPoint(x: 5.9, y: 13.1))
            house.close()

            let door = UIBezierPath(roundedRect: CGRect(x: 11.1, y: 16.2, width: 5.8, height: 9.3),
                                    byRoundingCorners: [.topLeft, .topRight],
                                    cornerRadii: CGSize(width: 1.4, height: 1.4))
            house.append(door)
            house.usesEvenOddFillRule = true
            house.fill()
        } else {
            let roof = UIBezierPath()
            roof.move(to: CGPoint(x: 3.2, y: 13.1))
            roof.addLine(to: CGPoint(x: 14, y: 3.5))
            roof.addLine(to: CGPoint(x: 24.8, y: 13.1))
            stroke(roof)

            let body = UIBezierPath()
            body.move(to: CGPoint(x: 6.2, y: 11.2))
            body.addLine(to: CGPoint(x: 6.2, y: 23.3))
            body.addQuadCurve(to: CGPoint(x: 8.2, y: 25.3), controlPoint: CGPoint(x: 6.2, y: 25.3))
            body.addLine(to: CGPoint(x: 19.8, y: 25.3))
            body.addQuadCurve(to: CGPoint(x: 21.8, y: 23.3), controlPoint: CGPoint(x: 21.8, y: 25.3))
            body.addLine(to: CGPoint(x: 21.8, y: 11.2))
            stroke(body)

            let door = UIBezierPath(roundedRect: CGRect(x: 11.2, y: 17.1, width: 5.6, height: 8.2),
                                    byRoundingCorners: [.topLeft, .topRight],
                                    cornerRadii: CGSize(width: 1.4, height: 1.4))
            stroke(door, width: 2.2)
        }
    }

    private static func drawClapperboard() {
        let body = UIBezierPath(roundedRect: CGRect(x: 4.1, y: 10.5, width: 19.8, height: 14.1),
                                cornerRadius: 2.7)
        stroke(body)

        let lid = UIBezierPath()
        lid.move(to: CGPoint(x: 4.8, y: 9.2))
        lid.addLine(to: CGPoint(x: 6.0, y: 5.2))
        lid.addQuadCurve(to: CGPoint(x: 7.7, y: 3.9), controlPoint: CGPoint(x: 6.5, y: 3.9))
        lid.addLine(to: CGPoint(x: 22.1, y: 3.9))
        lid.addQuadCurve(to: CGPoint(x: 23.5, y: 5.6), controlPoint: CGPoint(x: 23.5, y: 4.3))
        lid.addLine(to: CGPoint(x: 22.3, y: 9.2))
        lid.close()
        stroke(lid)

        for x in [9.2, 15.2, 21.0] {
            let stripe = UIBezierPath()
            stripe.move(to: CGPoint(x: x + 2.0, y: 4.2))
            stripe.addLine(to: CGPoint(x: x - 0.7, y: 9.0))
            stroke(stripe, width: 2.1)
        }

        let lowerDetails = UIBezierPath()
        lowerDetails.move(to: CGPoint(x: 9.3, y: 11.0))
        lowerDetails.addLine(to: CGPoint(x: 5.4, y: 17.2))
        lowerDetails.move(to: CGPoint(x: 17.0, y: 11.0))
        lowerDetails.addLine(to: CGPoint(x: 13.1, y: 17.2))
        lowerDetails.move(to: CGPoint(x: 23.1, y: 11.8))
        lowerDetails.addLine(to: CGPoint(x: 19.4, y: 17.2))
        stroke(lowerDetails, width: 2.1)
    }

    private static func drawUpload() {
        let square = UIBezierPath(roundedRect: CGRect(x: 4.0, y: 4.0, width: 20.0, height: 20.0),
                                  cornerRadius: 5.2)
        stroke(square)
        let plus = UIBezierPath()
        plus.move(to: CGPoint(x: 14, y: 9.0))
        plus.addLine(to: CGPoint(x: 14, y: 19.0))
        plus.move(to: CGPoint(x: 9.0, y: 14))
        plus.addLine(to: CGPoint(x: 19.0, y: 14))
        stroke(plus, width: 2.45)
    }

    private static func drawPaperPlane() {
        let plane = UIBezierPath()
        plane.move(to: CGPoint(x: 3.2, y: 12.5))
        plane.addLine(to: CGPoint(x: 24.7, y: 4.1))
        plane.addLine(to: CGPoint(x: 17.3, y: 24.1))
        plane.addLine(to: CGPoint(x: 12.8, y: 15.6))
        plane.close()
        stroke(plane)

        let fold = UIBezierPath()
        fold.move(to: CGPoint(x: 12.8, y: 15.6))
        fold.addLine(to: CGPoint(x: 24.7, y: 4.1))
        stroke(fold, width: 2.25)
    }
}
'''
text = text.rstrip() + "\n" + glyph_renderer + "\n"

# Validate destination order and avatar updater are untouched.
if ".home, .moments, .upload, .messages, .channel" not in text:
    raise SystemExit("Carbyne tab destinations/order changed unexpectedly.")
if "updateAvatar(" not in text or 'item?.image = icon' not in text:
    raise SystemExit("Live profile avatar updater is missing.")
if "controller.tabBar.tintColor =" in text or "unselectedItemTintColor =" in text:
    raise SystemExit("A tab tint override was introduced; preserve Carbyne colors.")

source.write_text(text)
print("Replaced the four tab glyphs with custom Instagram-style vector artwork; retained Carbyne Home/Spotlights clapperboard/Upload/DMs/Profile order, existing colors, layout, actions, and live avatar.")
