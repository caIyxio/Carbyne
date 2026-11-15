from pathlib import Path

path = Path("ios/Carbyne/Sources/AccountSheets.swift")
source = path.read_text()
old = '''        // Reject a blank export instead of silently uploading it.
        let data = output.dataProvider?.data as Data?
        if let data, data.count >= 4 {
            let bytes = [UInt8](data.prefix(4))
            if bytes.allSatisfy({ $0 == 0 }) {
                throw NSError(domain: "CarbyneImage", code: 422,
                              userInfo: [NSLocalizedDescriptionKey: "The crop rendered blank. Please reposition the image and try again."])
            }
        }'''
new = '''        // A transparent top-left corner is normal when a user drags the crop.
        // Validate the entire pixel buffer, not just its first pixel.
        if let providerData = output.dataProvider?.data {
            let bytes = providerData as Data
            guard bytes.contains(where: { $0 != 0 }) else {
                throw NSError(domain: "CarbyneImage", code: 422,
                              userInfo: [NSLocalizedDescriptionKey: "The crop could not be rendered. Please try again."])
            }
        }'''
if old not in source:
    raise SystemExit("Could not locate the faulty first-pixel blank check; refusing unsafe edit.")
source = source.replace(old, new, 1)
path.write_text(source)
print("Fixed false blank detection: checks the full output buffer, not a potentially transparent corner.")
