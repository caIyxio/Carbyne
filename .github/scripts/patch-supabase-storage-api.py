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

if old_upload in source:
    source = source.replace(old_upload, new_upload, 1)
elif "options: FileOptions(cacheControl: \"3600\", contentType: \"image/jpeg\", upsert: false)" not in source:
    raise SystemExit("Expected upload implementation was not found; refusing to patch an unexpected source file.")

old_public_url = 'supabase.storage.from("avatars").publicURL(path: path)'
new_public_url = 'try? supabase.storage.from("avatars").getPublicURL(path: path)'
if old_public_url in source:
    source = source.replace(old_public_url, new_public_url, 1)
elif 'try? supabase.storage.from("avatars").getPublicURL(path: path)' not in source:
    raise SystemExit("Expected public URL implementation was not found; refusing to patch an unexpected source file.")

source_path.write_text(source)
print("Applied Supabase Swift 2.55.x Storage API compatibility patch.")
