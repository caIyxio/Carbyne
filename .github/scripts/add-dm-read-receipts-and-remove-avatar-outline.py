from pathlib import Path

ROOT = Path("ios/Carbyne/Sources")

def replace(file, old, new, label):
    path = ROOT / file
    source = path.read_text()
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match in {file}, found {count}")
    path.write_text(source.replace(old, new, 1))

replace("CarbyneNativeTabController.swift", """                context.cgContext.setStrokeColor(UIColor.white.withAlphaComponent(0.9).cgColor)
                context.cgContext.setLineWidth(2)
                context.cgContext.strokeEllipse(in: rect.insetBy(dx: 1, dy: 1))
""", "", "Remove profile tab avatar outline")

replace("ContentView.swift", """                        NavigationLink {
                            ChatThreadScreen(profile: conversation.profile)
                        } label: {
                            HStack(spacing: 12) {
                                AvatarView(url: store.publicImageURL(path: conversation.profile.avatarPath), size: 52)
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(conversation.profile.title).font(.system(size: 15, weight: .semibold))
                                    Text(conversation.lastMessage.preview)
                                        .font(.system(size: 13))
                                        .foregroundStyle(.secondary)
                                        .lineLimit(1)
                                }
                                Spacer()
                                Text(conversation.lastMessage.createdAt, style: .time)
                                    .font(.system(size: 11))
                                    .foregroundStyle(.tertiary)
                            }
                            .padding(.vertical, 4)
                        }
""", """                        NavigationLink {
                            ChatThreadScreen(profile: conversation.profile)
                        } label: {
                            HStack(spacing: 12) {
                                AvatarView(url: store.publicImageURL(path: conversation.profile.avatarPath), size: 52)
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(conversation.profile.title).font(.system(size: 15, weight: .semibold))
                                    Text(conversation.lastMessage.preview)
                                        .font(.system(size: 13))
                                        .foregroundStyle(.secondary)
                                        .lineLimit(1)
                                }
                                Spacer()
                                Text(conversation.lastMessage.createdAt, style: .time)
                                    .font(.system(size: 11))
                                    .foregroundStyle(.tertiary)
                            }
                            .padding(.vertical, 4)
                        }
                        .listRowBackground(CarbynePalette.background)
                        .listRowSeparator(.hidden)
""", "Apply charcoal to DM conversation rows")

replace("CarbyneModels.swift", """    let attachmentSize: Int64?
    let createdAt: Date
""", """    let attachmentSize: Int64?
    let createdAt: Date
    let readAt: Date?
""", "Add message read timestamp")
replace("CarbyneModels.swift", """        case attachmentSize = "attachment_size"
        case createdAt = "created_at"
""", """        case attachmentSize = "attachment_size"
        case createdAt = "created_at"
        case readAt = "read_at"
""", "Decode message read timestamp")

replace("CarbyneStore.swift", """    func signedAttachmentURL(path: String) async throws -> URL {
""", """    func markMessagesRead(from peer: CarbyneProfile) async {
        guard let userID = session?.user.id else { return }
        let unreadIDs = messages
            .filter { $0.senderID == peer.id && $0.recipientID == userID && $0.readAt == nil }
            .map(\.id)
        guard !unreadIDs.isEmpty else { return }
        do {
            let timestamp = ISO8601DateFormatter().string(from: Date())
            for messageID in unreadIDs {
                try await supabase.from("messages")
                    .update(["read_at": timestamp])
                    .eq("id", value: messageID.uuidString)
                    .eq("recipient_id", value: userID.uuidString)
                    .execute()
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func signedAttachmentURL(path: String) async throws -> URL {
""", "Add mark-read database operation")

replace("CarbyneStore.swift", """        let _ = channel.onPostgresChange(InsertAction.self, schema: "public", table: "messages") { [weak self] _ in
            Task { @MainActor [weak self] in
                guard let self else { return }
                await self.loadConversations()
                if let peer = self.activeChatProfile { await self.loadMessages(with: peer) }
            }
        }
""", """        let _ = channel.onPostgresChange(InsertAction.self, schema: "public", table: "messages") { [weak self] _ in
            Task { @MainActor [weak self] in
                guard let self else { return }
                await self.loadConversations()
                if let peer = self.activeChatProfile { await self.loadMessages(with: peer) }
            }
        }
        let _ = channel.onPostgresChange(UpdateAction.self, schema: "public", table: "messages") { [weak self] _ in
            Task { @MainActor [weak self] in
                guard let self else { return }
                await self.loadConversations()
                if let peer = self.activeChatProfile { await self.loadMessages(with: peer) }
            }
        }
""", "Refresh chats when read receipts change")

replace("ContentView.swift", """    @State private var threadMessages: [CarbyneMessage] = []

    var body: some View {
""", """    @State private var threadMessages: [CarbyneMessage] = []
    @AppStorage("carbyne.readReceiptsEnabled") private var readReceiptsEnabled = true

    var body: some View {
""", "Share read receipt preference with chat")
replace("ContentView.swift", """        .task {
            store.activeChatProfile = profile
            await store.loadMessages(with: profile)
            threadMessages = store.messages
            await store.startMessagesRealtime()
        }
""", """        .task {
            store.activeChatProfile = profile
            await store.loadMessages(with: profile)
            threadMessages = store.messages
            if readReceiptsEnabled { await store.markMessagesRead(from: profile) }
            await store.startMessagesRealtime()
        }
""", "Mark existing incoming messages read")
replace("ContentView.swift", """        .onChange(of: store.messages) { _, updated in
            if store.activeChatProfile?.id == profile.id {
                threadMessages = updated
            }
        }
""", """        .onChange(of: store.messages) { _, updated in
            if store.activeChatProfile?.id == profile.id {
                threadMessages = updated
                if readReceiptsEnabled {
                    Task { await store.markMessagesRead(from: profile) }
                }
            }
        }
        .onChange(of: readReceiptsEnabled) { _, enabled in
            if enabled { Task { await store.markMessagesRead(from: profile) } }
        }
""", "Mark new incoming messages read")

replace("ContentView.swift", """            }
        }
        .padding(.horizontal, isImageAttachment ? 0 : 13)
""", """            }
            if isOutgoing, message.readAt != nil {
                Text("Seen")
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .trailing)
            }
        }
        .padding(.horizontal, isImageAttachment ? 0 : 13)
""", "Show read status on outgoing messages")

replace("AccountSheets.swift", """struct SettingsPrivacyView: View {
    var body: some View {
        List {
""", """struct SettingsPrivacyView: View {
    @AppStorage("carbyne.readReceiptsEnabled") private var readReceiptsEnabled = true

    var body: some View {
        List {
            Section("Direct Messages") {
                Toggle("Read Receipts", isOn: $readReceiptsEnabled)
                Text(readReceiptsEnabled
                     ? "People can see when you’ve read their messages."
                     : "Read receipts are off. People won’t see when you’ve read their messages.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
""", "Add Direct Messages read receipt setting")
