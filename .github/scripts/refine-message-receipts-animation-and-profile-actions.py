from pathlib import Path

ROOT = Path("ios/Carbyne/Sources")
content_path = ROOT / "ContentView.swift"
source = content_path.read_text()

def replace_once(old, new, label):
    global source
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    source = source.replace(old, new, 1)

replace_once(
"""    @AppStorage("carbyne.readReceiptsEnabled") private var readReceiptsEnabled = true

    var body: some View {
""",
"""    @AppStorage("carbyne.readReceiptsEnabled") private var readReceiptsEnabled = true

    private var lastSeenMessageID: UUID? {
        guard let currentUserID = store.session?.user.id else { return nil }
        return threadMessages.last(where: { $0.senderID == currentUserID && $0.readAt != nil })?.id
    }

    var body: some View {
""",
"Compute the latest seen outgoing message"
)

replace_once(
"""                        ForEach(threadMessages) { message in
                            HStack {
                                if message.senderID == store.session?.user.id { Spacer(minLength: 42) }
                                MessageBubble(message: message, isOutgoing: message.senderID == store.session?.user.id)
                                if message.senderID != store.session?.user.id { Spacer(minLength: 42) }
                            }
                            .id(message.id)
                        }
""",
"""                        ForEach(threadMessages) { message in
                            let outgoing = message.senderID == store.session?.user.id
                            VStack(alignment: outgoing ? .trailing : .leading, spacing: 3) {
                                HStack {
                                    if outgoing { Spacer(minLength: 42) }
                                    MessageBubble(message: message, isOutgoing: outgoing)
                                    if !outgoing { Spacer(minLength: 42) }
                                }
                                if outgoing && message.id == lastSeenMessageID {
                                    Text("Seen")
                                        .font(.system(size: 11, weight: .medium))
                                        .foregroundStyle(.secondary)
                                        .padding(.horizontal, 4)
                                        .transition(.opacity.combined(with: .move(edge: .bottom)))
                                }
                            }
                            .frame(maxWidth: .infinity, alignment: outgoing ? .trailing : .leading)
                            .transition(
                                .asymmetric(
                                    insertion: .scale(
                                        scale: 0.88,
                                        anchor: outgoing ? .bottomTrailing : .bottomLeading
                                    ).combined(with: .opacity),
                                    removal: .opacity
                                )
                            )
                            .id(message.id)
                        }
""",
"Move Seen outside bubbles and animate new message rows"
)

replace_once(
"""            if isOutgoing, message.readAt != nil {
                Text("Seen")
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .trailing)
            }
""",
"",
"Remove Seen from inside the message bubble"
)

replace_once(
"""                                        Button { showEditProfile = true } label: {
                                            Image(systemName: "pencil")
                                                .font(.system(size: 17, weight: .semibold))
                                                .frame(width: 40, height: 40)
                                                .background(.ultraThinMaterial, in: Circle())
                                        }
                                        .buttonStyle(.plain)
                                        .accessibilityLabel("Edit profile")
""",
"",
"Remove duplicate profile banner edit button"
)

replace_once(
"""                threadMessages = updated
                if readReceiptsEnabled {
""",
"""                withAnimation(.spring(response: 0.34, dampingFraction: 0.82)) {
                    threadMessages = updated
                }
                if readReceiptsEnabled {
""",
"Animate newly received messages"
)

content_path.write_text(source)
print("Moved the Seen receipt below the bubble, limited it to the newest seen outgoing message, added a spring pop-in send/receive transition, and removed the duplicate profile-banner pencil.")
