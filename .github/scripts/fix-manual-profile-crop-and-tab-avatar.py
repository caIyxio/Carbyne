from pathlib import Path

account_path = Path("ios/Carbyne/Sources/AccountSheets.swift")
tab_path = Path("ios/Carbyne/Sources/CarbyneNativeTabController.swift")

account = account_path.read_text()
start = account.find("    private func renderCrop() throws -> UIImage {")
end = account.find("\n}\n\nextension UIImage", start)
if start < 0 or end < 0:
    raise SystemExit("Could not locate the current profile crop renderer; refusing unsafe edit.")

replacement = r'''    private func renderCrop() throws -> UIImage {
        let normalized = image.carbyneUpright()
        guard normalized.size.width > 0, normalized.size.height > 0 else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The selected photo could not be decoded. Please choose another image."])
        }

        let viewport = cropAreaSize == .zero
            ? CGSize(width: 320, height: 320 / aspect)
            : cropAreaSize
        guard viewport.width > 0, viewport.height > 0 else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The crop area is not ready yet. Please try again."])
        }

        // Render the same transformed image used by the SwiftUI preview, clipped to
        // the viewport. This avoids CGImage.cropping failures on scaled/offset rects.
        let previewScale = max(viewport.width / normalized.size.width,
                               viewport.height / normalized.size.height) * zoom
        let drawSize = CGSize(width: normalized.size.width * previewScale,
                              height: normalized.size.height * previewScale)
        let drawRect = CGRect(
            x: (viewport.width - drawSize.width) / 2 + offset.width,
            y: (viewport.height - drawSize.height) / 2 + offset.height,
            width: drawSize.width,
            height: drawSize.height
        )

        let target = kind == .avatar
            ? CGSize(width: 1080, height: 1080)
            : CGSize(width: 1500, height: 500)
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        format.opaque = true
        let renderer = UIGraphicsImageRenderer(size: target, format: format)
        let result = renderer.image { context in
            let canvas = CGRect(origin: .zero, size: target)
            UIColor.black.setFill()
            context.fill(canvas)
            context.cgContext.saveGState()
            context.cgContext.scaleBy(x: target.width / viewport.width,
                                      y: target.height / viewport.height)
            context.cgContext.clip(to: CGRect(origin: .zero, size: viewport))
            normalized.draw(in: drawRect)
            context.cgContext.restoreGState()
        }
        guard let output = result.cgImage, output.width > 0, output.height > 0 else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The edited image could not be exported. Please try again."])
        }
        return result
    }'''
account = account[:start] + replacement + account[end:]
account_path.write_text(account)

tab = tab_path.read_text()
old_size = "let size = CGSize(width: 28, height: 28)"
if old_size not in tab:
    raise SystemExit("Could not locate the tab avatar size; refusing unsafe edit.")
tab = tab.replace(old_size, "let size = CGSize(width: 34, height: 34)", 1)
tab_path.write_text(tab)
print("Replaced crop export with source-pixel cropping that mirrors preview zoom/drag, and increased the Profile tab avatar to 34pt.")
