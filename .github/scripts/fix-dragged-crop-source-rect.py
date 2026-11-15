from pathlib import Path

path = Path("ios/Carbyne/Sources/AccountSheets.swift")
source = path.read_text()
start = source.find("    private func renderCrop() throws -> UIImage {")
end = source.find("\n}\n\nextension UIImage", start)
if start < 0 or end < 0:
    raise SystemExit("Could not locate crop renderer; refusing unsafe edit.")

replacement = r'''    private func renderCrop() throws -> UIImage {
        // Crop the source pixels using the same viewport/scale/offset as the preview.
        // Drawing a full image into a translated output rect can leave the entire
        // output transparent when the preview and export coordinate spaces diverge.
        let upright = image.carbyneUpright()
        let sourceCG: CGImage
        if let cg = upright.cgImage {
            sourceCG = cg
        } else if let ci = upright.ciImage,
                  let cg = CIContext(options: nil).createCGImage(ci, from: ci.extent) {
            sourceCG = cg
        } else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The selected photo could not be decoded. Please choose another image."])
        }

        let viewport = cropAreaSize == .zero
            ? CGSize(width: 320, height: 320 / aspect)
            : cropAreaSize
        guard viewport.width > 0, viewport.height > 0,
              image.size.width > 0, image.size.height > 0 else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The crop area is not ready yet. Please try again."])
        }

        // Match the preview's aspect-fill scale and constrain the drag exactly as
        // the gesture does, then convert the visible viewport back to source pixels.
        let baseScale = max(viewport.width / image.size.width,
                            viewport.height / image.size.height)
        let displayScale = baseScale * zoom
        let displayedWidth = image.size.width * displayScale
        let displayedHeight = image.size.height * displayScale
        let maxX = max((displayedWidth - viewport.width) / 2, 0)
        let maxY = max((displayedHeight - viewport.height) / 2, 0)
        let clampedX = min(max(offset.width, -maxX), maxX)
        let clampedY = min(max(offset.height, -maxY), maxY)

        let sourceOriginX = ((displayedWidth - viewport.width) / 2 - clampedX) / displayScale
        let sourceOriginY = ((displayedHeight - viewport.height) / 2 - clampedY) / displayScale
        let pixelsPerPointX = CGFloat(sourceCG.width) / image.size.width
        let pixelsPerPointY = CGFloat(sourceCG.height) / image.size.height

        let rawRect = CGRect(
            x: sourceOriginX * pixelsPerPointX,
            y: sourceOriginY * pixelsPerPointY,
            width: (viewport.width / displayScale) * pixelsPerPointX,
            height: (viewport.height / displayScale) * pixelsPerPointY
        )
        let imageBounds = CGRect(x: 0, y: 0, width: CGFloat(sourceCG.width), height: CGFloat(sourceCG.height))
        let cropRect = rawRect.integral.intersection(imageBounds)
        guard cropRect.width >= 1, cropRect.height >= 1,
              let croppedCG = sourceCG.cropping(to: cropRect) else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The selected crop is outside the image. Please reposition it and try again."])
        }

        let target = kind == .avatar
            ? CGSize(width: 1080, height: 1080)
            : CGSize(width: 1500, height: 500)
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        format.opaque = true
        let result = UIGraphicsImageRenderer(size: target, format: format).image { context in
            context.cgContext.interpolationQuality = .high
            context.cgContext.draw(croppedCG, in: CGRect(origin: .zero, size: target))
        }
        guard let output = result.cgImage,
              output.width == Int(target.width),
              output.height == Int(target.height) else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The edited image could not be exported. Please try again."])
        }
        return result
    }'''
source = source[:start] + replacement + source[end:]
path.write_text(source)
print("Replaced translated-canvas export with a source-pixel crop based on the preview drag offset.")
