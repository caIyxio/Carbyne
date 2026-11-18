from pathlib import Path

root = Path('ios/Carbyne/Sources')
content_path = root / 'ContentView.swift'
store_path = root / 'CarbyneStore.swift'
models_path = root / 'CarbyneModels.swift'

content = content_path.read_text()
old_own = '''                                    HStack(spacing: 0) {
                                        profileMetric("0", label: "posts")
                                        Spacer(minLength: 8)
                                        profileMetric("\\(store.subscriberCounts[profile.id] ?? 0)", label: "subscribers")
                                    }
                                    .padding(.top, 4)'''
new_own = '''                                    HStack(spacing: 0) {
                                        profileMetric("0", label: "posts")
                                        Spacer(minLength: 8)
                                        profileMetric("\\(store.likeCounts[profile.id] ?? 0)", label: "likes")
                                        Spacer(minLength: 8)
                                        profileMetric("\\(store.subscriberCounts[profile.id] ?? 0)", label: "subscribers")
                                    }
                                    .padding(.top, 4)'''
if old_own not in content:
    raise SystemExit('Could not find own-profile metrics row.')
content = content.replace(old_own, new_own, 1)

old_public = '''                            HStack(spacing: 0) {
                                VStack(spacing: 2) {
                                    Text("0").font(.system(size: 17, weight: .semibold))
                                    Text("posts").font(.system(size: 12)).foregroundStyle(.secondary)
                                }
                                Spacer(minLength: 8)
                                VStack(spacing: 2) {
                                    Text("\\(store.subscriberCounts[profile.id] ?? 0)").font(.system(size: 17, weight: .semibold))
                                    Text("subscribers").font(.system(size: 12)).foregroundStyle(.secondary)
                                }
                            }'''
new_public = '''                            HStack(spacing: 0) {
                                profileMetric("0", label: "posts")
                                Spacer(minLength: 8)
                                profileMetric("\\(store.likeCounts[profile.id] ?? 0)", label: "likes")
                                Spacer(minLength: 8)
                                profileMetric("\\(store.subscriberCounts[profile.id] ?? 0)", label: "subscribers")
                            }'''
if old_public not in content:
    raise SystemExit('Could not find public-profile metrics row.')
content = content.replace(old_public, new_public, 1)

old_task = '''            .toolbar(.hidden, for: .navigationBar)
        }
    }

    private func profileMetric'''
new_task = '''            .toolbar(.hidden, for: .navigationBar)
            .task(id: profile.id) {
                await store.refreshProfileLikes(for: profile)
            }
        }
    }

    private func profileMetric'''
if old_task not in content:
    raise SystemExit('Could not find own-profile task insertion point.')
content = content.replace(old_task, new_task, 1)

old_public_task = '''        .task {
            await store.viewChannel(profile)
            await store.refreshSubscription(for: profile)
        }'''
new_public_task = '''        .task {
            await store.viewChannel(profile)
            await store.refreshSubscription(for: profile)
            await store.refreshProfileLikes(for: profile)
        }'''
if old_public_task not in content:
    raise SystemExit('Could not find public-profile loading task.')
content = content.replace(old_public_task, new_public_task, 1)
public_start = content.index('struct PublicChannelScreen: View {')
public_end = content.index('struct ChannelDirectorySheet: View {', public_start)
public_block = content[public_start:public_end]
public_close = public_block.rfind('}')
if public_close < 0:
    raise SystemExit('Could not find PublicChannelScreen closing brace.')
public_block = public_block[:public_close] + '''    private func profileMetric(_ value: String, label: String) -> some View {
        VStack(spacing: 2) {
            Text(value).font(.system(size: 17, weight: .semibold))
            Text(label).font(.system(size: 12)).foregroundStyle(.secondary)
        }
        .frame(minWidth: 58)
    }
''' + public_block[public_close:]
content = content[:public_start] + public_block + content[public_end:]
content_path.write_text(content)

store = store_path.read_text()
old_published = '''    @Published private(set) var subscriberCounts: [UUID: Int] = [:]
    @Published private(set) var isSubscribed = false'''
new_published = '''    @Published private(set) var subscriberCounts: [UUID: Int] = [:]
    @Published private(set) var likeCounts: [UUID: Int] = [:]
    @Published private(set) var isSubscribed = false'''
if old_published not in store:
    raise SystemExit('Could not find store published profile-count properties.')
store = store.replace(old_published, new_published, 1)

api = '''

    // MARK: - Content and likes API

    func refreshProfileLikes(for profile: CarbyneProfile) async {
        await refreshProfileLikes(for: profile.id)
    }

    func refreshProfileLikes(for creatorID: UUID) async {
        do {
            let records: [ProfileLikeCountRecord] = try await supabase
                .from("profile_like_counts")
                .select("creator_id,likes_count")
                .eq("creator_id", value: creatorID.uuidString)
                .limit(1)
                .execute().value
            likeCounts[creatorID] = records.first?.likesCount ?? 0
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    /// Register a video or Spotlight in the shared content registry.
    /// The supplied ID should be the UUID of the future video/Spotlight row.
    func registerContent(id: UUID, type: CarbyneContentType) async throws {
        guard let userID = session?.user.id else {
            throw NSError(domain: "Carbyne", code: 401,
                          userInfo: [NSLocalizedDescriptionKey: "Sign in to publish content."])
        }
        let item = ContentItemInsert(id: id, creatorID: userID, contentType: type.rawValue)
        try await supabase.from("content_items").insert(item).execute()
    }

    /// Add one like. Duplicate likes are prevented by the database primary key.
    func likeContent(id: UUID, creatorID: UUID) async throws {
        guard let userID = session?.user.id else {
            throw NSError(domain: "Carbyne", code: 401,
                          userInfo: [NSLocalizedDescriptionKey: "Sign in to like content."])
        }
        let like = ContentLikeInsert(contentID: id, userID: userID)
        try await supabase.from("content_likes").insert(like).execute()
        await refreshProfileLikes(for: creatorID)
    }

    func unlikeContent(id: UUID, creatorID: UUID) async throws {
        guard let userID = session?.user.id else {
            throw NSError(domain: "Carbyne", code: 401,
                          userInfo: [NSLocalizedDescriptionKey: "Sign in to remove a like."])
        }
        try await supabase.from("content_likes").delete()
            .eq("content_id", value: id.uuidString)
            .eq("user_id", value: userID.uuidString)
            .execute()
        await refreshProfileLikes(for: creatorID)
    }
'''
store = store.rstrip()
if not store.endswith('}'):
    raise SystemExit('Unexpected CarbyneStore.swift ending.')
store = store[:-1] + api + '\n}\n'
store_path.write_text(store)

models = models_path.read_text()
models += '''

enum CarbyneContentType: String, Codable {
    case video
    case spotlight
}

struct ContentItemInsert: Encodable {
    let id: UUID
    let creatorID: UUID
    let contentType: String

    enum CodingKeys: String, CodingKey {
        case id
        case creatorID = "creator_id"
        case contentType = "content_type"
    }
}

struct ContentLikeInsert: Encodable {
    let contentID: UUID
    let userID: UUID

    enum CodingKeys: String, CodingKey {
        case contentID = "content_id"
        case userID = "user_id"
    }
}

struct ProfileLikeCountRecord: Decodable {
    let creatorID: UUID
    let likesCount: Int

    enum CodingKeys: String, CodingKey {
        case creatorID = "creator_id"
        case likesCount = "likes_count"
    }
}
'''
models_path.write_text(models)

print('Added the likes metric and shared video/Spotlight likes API.')
