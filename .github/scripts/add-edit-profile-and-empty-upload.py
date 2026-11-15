from pathlib import Path

root = Path("ios/Carbyne/Sources")
content_path = root / "ContentView.swift"
models_path = root / "CarbyneModels.swift"
content = content_path.read_text()
models = models_path.read_text()

def replace_once(source, old, new, label):
    if new in source:
        return source
    if old not in source:
        raise SystemExit(f"Could not find {label}; refusing to patch the wrong source.")
    return source.replace(old, new, 1)

# Expose the server-enforced username cooldown timestamp on decoded profiles.
models = replace_once(
    models,
    """    var bio: String?

    enum CodingKeys""",
    """    var bio: String?
    var usernameUpdatedAt: String?

    enum CodingKeys""",
    "profile username cooldown property"
)
models = replace_once(
    models,
    """        case bio
    }

    var title""",
    """        case bio
        case usernameUpdatedAt = "username_updated_at"
    }

    var title""",
    "profile username cooldown coding key"
)
models_path.write_text(models)

# Turn the banner pencil into a peer destination alongside Settings.
content = replace_once(
    content,
    """    @State private var showSettings = false""",
    """    @State private var showSettings = false
    @State private var showEditProfile = false""",
    "own profile edit navigation state"
)
pencil_button = """                                    Button { showEditProfile = true } label: {
                                        Image(systemName: "pencil")
                                            .font(.system(size: 17, weight: .semibold))
                                            .frame(width: 40, height: 40)
                                            .background {
                                                if #available(iOS 26.0, *) {
                                                    Circle().fill(.clear).glassEffect(.regular.interactive(), in: Circle())
                                                } else {
                                                    Circle().fill(.ultraThinMaterial)
                                                        .overlay(Circle().strokeBorder(Color.primary.opacity(0.12)))
                                                }
                                            }
                                    }
                                    .buttonStyle(.plain)
                                    .accessibilityLabel("Edit profile")
"""
content = replace_once(
    content,
    """                                    .accessibilityLabel("Settings & Privacy")
                                }
                                .padding(.horizontal, 16)""",
    """                                    .accessibilityLabel("Settings & Privacy")

""" + pencil_button + """                                }
                                .padding(.horizontal, 16)""",
    "profile banner edit pencil button"
)
content = replace_once(
    content,
    """            .navigationDestination(isPresented: $showSettings) {
                SettingsPrivacyView()
            }
            .toolbar(.hidden, for: .navigationBar)""",
    """            .navigationDestination(isPresented: $showSettings) {
                SettingsPrivacyView()
            }
            .navigationDestination(isPresented: $showEditProfile) {
                EditProfileView()
            }
            .toolbar(.hidden, for: .navigationBar)""",
    "edit profile navigation destination"
)

# A dedicated profile-shaped editor; nothing is persisted until Apply is pressed.
edit_view = """
struct EditProfileView: View {
    @EnvironmentObject private var store: CarbyneStore
    @Environment(\\.dismiss) private var dismiss
    @State private var displayName = ""
    @State private var username = ""
    @State private var bio = ""
    @State private var isApplying = false
    @State private var errorText: String?

    private var hasChanges: Bool {
        displayName != (store.profile?.displayName ?? "")
            || username != (store.profile?.username ?? "")
            || bio != (store.profile?.bio ?? "")
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                ProfileBannerView(url: store.publicImageURL(path: store.profile?.bannerPath))
                HStack(alignment: .bottom, spacing: 14) {
                    AvatarView(url: store.publicImageURL(path: store.profile?.avatarPath), size: 92)
                        .overlay(Circle().stroke(Color(uiColor: .systemBackground), lineWidth: 4))
                        .offset(y: -24)
                        .padding(.bottom, -24)
                    VStack(alignment: .leading, spacing: 3) {
                        Text(displayName.isEmpty ? "Display name" : displayName)
                            .font(.system(size: 22, weight: .bold))
                            .lineLimit(1)
                        Text(username.isEmpty ? "@username" : "@\\(username)")
                            .font(.system(size: 14))
                            .foregroundStyle(.secondary)
                    }
                    .padding(.bottom, 4)
                    Spacer(minLength: 0)
                }
                .padding(.horizontal, 18)
                .padding(.top, 4)

                VStack(alignment: .leading, spacing: 18) {
                    Group {
                        Text("Display name")
                            .font(.system(size: 13, weight: .semibold))
                        TextField("Display name", text: $displayName)
                            .textInputAutocapitalization(.words)
                            .padding(13)
                            .background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 12))
                    }
                    Group {
                        Text("Username")
                            .font(.system(size: 13, weight: .semibold))
                        TextField("username", text: $username)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .padding(13)
                            .background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 12))
                        Text("Usernames can only be changed once every 14 days.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    Group {
                        HStack {
                            Text("Bio")
                                .font(.system(size: 13, weight: .semibold))
                            Spacer()
                            Text("\\(bio.count)/160")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        TextEditor(text: $bio)
                            .frame(minHeight: 100)
                            .padding(6)
                            .background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 12))
                            .onChange(of: bio) { _, value in
                                if value.count > 160 { bio = String(value.prefix(160)) }
                            }
                    }
                    if let errorText {
                        Text(errorText)
                            .font(.footnote)
                            .foregroundStyle(.red)
                    }
                    Button {
                        Task {
                            isApplying = true
                            errorText = nil
                            do {
                                try await store.saveProfile(displayName: displayName, username: username, bio: bio)
                                dismiss()
                            } catch {
                                errorText = error.localizedDescription
                            }
                            isApplying = false
                        }
                    } label: {
                        HStack {
                            if isApplying { ProgressView().tint(.white) }
                            else { Text("Apply").fontWeight(.semibold) }
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 13)
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(isApplying || !hasChanges || displayName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
                .padding(18)
            }
        }
        .background(Color(uiColor: .systemBackground))
        .navigationTitle("Edit profile")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            displayName = store.profile?.displayName ?? ""
            username = store.profile?.username ?? ""
            bio = store.profile?.bio ?? ""
        }
    }
}

"""
if "struct EditProfileView: View {" not in content:
    marker = "\nstruct UploadScreen: View {"
    if marker not in content:
        raise SystemExit("Could not find UploadScreen insertion point.")
    content = content.replace(marker, "\n" + edit_view + marker, 1)

# Upload is intentionally a blank placeholder until its feature is designed.
start = content.index("struct UploadScreen: View {")
next_struct = content.find("\nstruct ", start + len("struct UploadScreen: View {"))
if next_struct == -1:
    raise SystemExit("Could not find the end of UploadScreen.")
content = content[:start] + """struct UploadScreen: View {
    let openAuth: () -> Void

    var body: some View {
        Color.clear
            .ignoresSafeArea()
    }
}
""" + content[next_struct:]

content_path.write_text(content)
print("Added the banner Edit Profile destination, explicit Apply flow, 14-day username cooldown UI, and emptied the Upload tab.")
