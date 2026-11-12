from pathlib import Path

source_path = Path("ios/Carbyne/Sources/CarbyneStore.swift")
source = source_path.read_text()

old_upload = """            _ = try await supabase.storage.from("avatars").upload(
                path: path,
                data: data,
                options: UploadOptions(contentType: "image/jpeg", cacheControl: .noCache, upsert: false)
            )"""
new_upload = """            _ = try await supabase.storage.from("avatars").upload(
                path,
                data: data,
                options: FileOptions(cacheControl: "3600", contentType: "image/jpeg", upsert: false)
            )"""

if old_upload not in source:
    raise SystemExit("Expected upload implementation was not found; refusing to patch an unexpected source file.")

source = source.replace(old_upload, new_upload, 1)
old_public_url = 'supabase.storage.from("avatars").publicURL(path: path)'
new_public_url = 'supabase.storage.from("avatars").getPublicURL(path: path)'
if old_public_url not in source:
    raise SystemExit("Expected public URL implementation was not found; refusing to patch an unexpected source file.")

source = source.replace(old_public_url, new_public_url, 1)
source_path.write_text(source)
print("Applied Supabase Swift 2.55.x Storage API compatibility patch.")
