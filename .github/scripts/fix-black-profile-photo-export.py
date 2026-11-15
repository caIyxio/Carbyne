from pathlib import Path

path = Path("ios/Carbyne/Sources/AccountSheets.swift")
source = path.read_text()
start = source.find("    private func renderCrop() throws -> UIImage {")
end = source.find("\n}\n\nextension UIImage {", start)
if start < 0 or end < 0:
    raise SystemExit("Could not locate the profile crop renderer; refusing to patch.")

replacement = r'''    private func renderCrop() throws -> UIImage {
        let normalized = previewImage
        guard normalized.cgImage != nil,
              normalized.size.width > 0,
              normalized.size.height > 0 else {
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

        // Match the live SwiftUI preview's aspect-fill sizing and drag offset,
        // but draw the original decoded UIImage directly. ImageRenderer can
        // produce a black snapshot for some PhotosPicker-backed image sources.
        let baseScale = max(viewport.width / normalized.size.width,
                            viewport.height / normalized.size.height)
        let drawWidth = normalized.size.width * baseScale * zoom
        let drawHeight = normalized.size.height * baseScale * zoom
        let outputSize = kind == .avatar
            ? CGSize(width: 1080, height: 1080)
            : CGSize(width: 1500, height: 500)
        let scaleX = outputSize.width / viewport.width
        let scaleY = outputSize.height / viewport.height
        let imageRect = CGRect(
            x: ((viewport.width - drawWidth) / 2 + offset.width) * scaleX,
            y: ((viewport.height - drawHeight) / 2 + offset.height) * scaleY,
            width: drawWidth * scaleX,
            height: drawHeight * scaleY
        )

        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        format.opaque = true
        let renderer = UIGraphicsImageRenderer(size: outputSize, format: format)
        let result = renderer.image { context in
            UIColor.black.setFill()
            context.fill(CGRect(origin: .zero, size: outputSize))
            context.cgContext.interpolationQuality = .high
            normalized.draw(in: imageRect)
        }

        guard let cg = result.cgImage,
              cg.width == Int(outputSize.width),
              cg.height == Int(outputSize.height) else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The edited image could not be exported. Please try again."])
        }
        return result
    }'''
source = source[:start] + replacement + source[end:]
path.write_text(source)
print("Replaced SwiftUI ImageRenderer crop export with direct UIKit image rendering.")
