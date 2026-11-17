from pathlib import Path

path = Path("ios/Carbyne/Sources/AccountSheets.swift")
source = path.read_text()

# Make the preview and export consume one shared transform, derived from the
# exact viewport, zoom, and clamped drag offset currently shown on screen.
old_scale = """                    let baseScale = max(geometry.size.width / previewImage.size.width, geometry.size.height / previewImage.size.height)
                    ZStack {"""
new_scale = """                    let metrics = cropMetrics(in: geometry.size)
                    ZStack {"""
if old_scale not in source:
    raise SystemExit("Could not locate crop preview scale calculation.")
source = source.replace(old_scale, new_scale, 1)

old_frame = """                            .frame(width: previewImage.size.width * baseScale * zoom,
                                   height: previewImage.size.height * baseScale * zoom)
                            .offset(offset)"""
new_frame = """                            .frame(width: metrics.displayedSize.width,
                                   height: metrics.displayedSize.height)
                            .offset(metrics.offset)"""
if old_frame not in source:
    raise SystemExit("Could not locate crop preview image frame.")
source = source.replace(old_frame, new_frame, 1)

old_drag = """                                let drawWidth = previewImage.size.width * baseScale * zoom
                                let drawHeight = previewImage.size.height * baseScale * zoom"""
new_drag = """                                let drawWidth = metrics.displayedSize.width
                                let drawHeight = metrics.displayedSize.height"""
if old_drag not in source:
    raise SystemExit("Could not locate crop drag clamp calculation.")
source = source.replace(old_drag, new_drag, 1)

old_appear = """                    .onAppear { cropAreaSize = geometry.size }"""
new_appear = """                    .onAppear { updateCropAreaSize(geometry.size) }
                    .onChange(of: geometry.size) { _, newSize in
                        updateCropAreaSize(newSize)
                    }"""
if old_appear not in source:
    raise SystemExit("Could not locate crop viewport size tracking.")
source = source.replace(old_appear, new_appear, 1)

old_zoom = """                    Slider(value: $zoom, in: 1...4, step: 0.05)"""
new_zoom = """                    Slider(value: $zoom, in: 1...4, step: 0.05)
                        .onChange(of: zoom) { _, _ in
                            let clamped = clampedOffset(for: cropAreaSize)
                            offset = clamped
                            dragOrigin = clamped
                        }"""
if old_zoom not in source:
    raise SystemExit("Could not locate crop zoom slider.")
source = source.replace(old_zoom, new_zoom, 1)

start = source.find("    private func renderCrop() throws -> UIImage {")
marker = "\n    }\n}\n\nextension UIImage"
end = source.find(marker, start)
if start < 0 or end < 0:
    raise SystemExit("Could not locate crop export function boundary.")

replacement = r'''    private func cropMetrics(in viewport: CGSize) -> (
        baseScale: CGFloat,
        displayedSize: CGSize,
        offset: CGSize,
        imageOrigin: CGPoint
    ) {
        let baseScale = max(viewport.width / previewImage.size.width,
                            viewport.height / previewImage.size.height)
        let displayedSize = CGSize(
            width: previewImage.size.width * baseScale * zoom,
            height: previewImage.size.height * baseScale * zoom
        )
        let maxX = max((displayedSize.width - viewport.width) / 2, 0)
        let maxY = max((displayedSize.height - viewport.height) / 2, 0)
        let clamped = CGSize(
            width: min(max(offset.width, -maxX), maxX),
            height: min(max(offset.height, -maxY), maxY)
        )
        let imageOrigin = CGPoint(
            x: (viewport.width - displayedSize.width) / 2 + clamped.width,
            y: (viewport.height - displayedSize.height) / 2 + clamped.height
        )
        return (baseScale, displayedSize, clamped, imageOrigin)
    }

    private func clampedOffset(for viewport: CGSize) -> CGSize {
        guard viewport.width > 0, viewport.height > 0 else { return .zero }
        return cropMetrics(in: viewport).offset
    }

    private func updateCropAreaSize(_ size: CGSize) {
        guard size.width > 0, size.height > 0 else { return }
        cropAreaSize = size
        let clamped = clampedOffset(for: size)
        offset = clamped
        dragOrigin = clamped
    }

    private func renderCrop() throws -> UIImage {
        let upright = previewImage
        guard let sourceCG = upright.cgImage,
              upright.size.width > 0, upright.size.height > 0 else {
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

        // This is the exact same transform used by the live preview. Instead
        // of calculating a second source rectangle, transform the full source
        // image into the preview's viewport and let the output bounds crop it.
        let metrics = cropMetrics(in: viewport)
        let target = kind == .avatar
            ? CGSize(width: 1080, height: 1080)
            : CGSize(width: 1500, height: 500)
        let outputScaleX = target.width / viewport.width
        let outputScaleY = target.height / viewport.height
        let pixelsPerPointX = CGFloat(sourceCG.width) / upright.size.width
        let pixelsPerPointY = CGFloat(sourceCG.height) / upright.size.height
        let imageScaleX = metrics.baseScale * zoom * outputScaleX / pixelsPerPointX
        let imageScaleY = metrics.baseScale * zoom * outputScaleY / pixelsPerPointY
        let imageTranslationX = metrics.imageOrigin.x * outputScaleX
        // Core Image uses a bottom-left origin; convert the preview's top-left
        // image origin while preserving the exact same visible viewport.
        let imageTranslationY = (
            viewport.height - metrics.imageOrigin.y - metrics.displayedSize.height
        ) * outputScaleY

        let transform = CGAffineTransform(
            a: imageScaleX, b: 0,
            c: 0, d: imageScaleY,
            tx: imageTranslationX, ty: imageTranslationY
        )
        let transformed = CIImage(cgImage: sourceCG).transformed(by: transform)
        let outputRect = CGRect(origin: .zero, size: target)
        guard let outputCG = CIContext(options: nil).createCGImage(transformed, from: outputRect),
              outputCG.width == Int(target.width),
              outputCG.height == Int(target.height) else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The edited image could not be exported. Please try again."])
        }
        return UIImage(cgImage: outputCG, scale: 1, orientation: .up)
    }'''
source = source[:start] + replacement + source[end + len("\n    }"):]
path.write_text(source)
print("Crop preview and export now share one viewport transform; zoom and viewport changes clamp the same drag offset.")
