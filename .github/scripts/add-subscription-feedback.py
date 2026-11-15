from pathlib import Path

content_path = Path("ios/Carbyne/Sources/ContentView.swift")
store_path = Path("ios/Carbyne/Sources/CarbyneStore.swift")
content = content_path.read_text()
store = store_path.read_text()

# Give the Subscribe/Subscribed symbol a quick springy response when its
# server-confirmed state changes. The replace transition morphs plus/checkmark.
label = """                        Label(store.isSubscribed ? "Subscribed" : "Subscribe",
                              systemImage: store.isSubscribed ? "checkmark" : "plus")
                            .font(.system(size: 12, weight: .semibold))
"""
animated_label = """                        Label(store.isSubscribed ? "Subscribed" : "Subscribe",
                              systemImage: store.isSubscribed ? "checkmark" : "plus")
                            .font(.system(size: 12, weight: .semibold))
                            .contentTransition(.symbolEffect(.replace))
                            .symbolEffect(.bounce, value: store.isSubscribed)
                            .animation(.spring(response: 0.34, dampingFraction: 0.68), value: store.isSubscribed)
"""
if animated_label not in content:
    if label not in content:
        raise SystemExit("Could not find the public-profile Subscribe label to animate.")
    content = content.replace(label, animated_label, 1)

# Trigger a subtle UIKit haptic only after Supabase confirms the subscription
# change and the refreshed state actually differs from the previous state.
old = """        isLoading = true
        defer { isLoading = false }
        do {
            if isSubscribed {
"""
new = """        let wasSubscribed = isSubscribed
        let feedback = UIImpactFeedbackGenerator(style: wasSubscribed ? .soft : .medium)
        feedback.prepare()
        isLoading = true
        defer { isLoading = false }
        do {
            if isSubscribed {
"""
if old not in store:
    raise SystemExit("Could not find toggleSubscription's loading/action block.")
store = store.replace("        isLoading = true\n        defer { isLoading = false }\n        do {\n            if isSubscribed {", new, 1)

old_refresh = """            await refreshSubscription(for: channel)
        } catch { errorMessage = error.localizedDescription }
"""
new_refresh = """            await refreshSubscription(for: channel)
            if isSubscribed != wasSubscribed {
                feedback.impactOccurred()
            }
        } catch { errorMessage = error.localizedDescription }
"""
if new_refresh not in store:
    if old_refresh not in store:
        raise SystemExit("Could not find toggleSubscription's refresh completion.")
    store = store.replace(old_refresh, new_refresh, 1)

# Animate the actual capsule width and the identity-row layout together so
# the button glides into its new size instead of snapping/repositioning.
old_surface = """                            .foregroundStyle(store.isSubscribed ? Color.primary : Color(uiColor: .systemBackground))
                            .background {
                                Capsule().fill(store.isSubscribed
                                    ? Color(uiColor: .secondarySystemBackground)
                                    : Color.primary)
                            }
                            .overlay {
                                Capsule().strokeBorder(Color.primary.opacity(store.isSubscribed ? 0.16 : 0))
                            }
"""
new_surface = """                            .foregroundStyle(.primary)
                            .background {
                                Capsule().fill(.ultraThinMaterial)
                                    .overlay {
                                        Capsule().fill(Color.primary.opacity(store.isSubscribed ? 0.035 : 0.08))
                                    }
                            }
                            .overlay {
                                Capsule().strokeBorder(Color.primary.opacity(0.14))
                            }
"""
if old_surface in content:
    content = content.replace(old_surface, new_surface, 1)
elif new_surface not in content:
    raise SystemExit("Could not find Subscribe capsule surface to convert to material blur.")

old_button_modifiers = """                    .buttonStyle(.plain)
                    .fixedSize(horizontal: true, vertical: false)
"""
new_button_modifiers = """                    .buttonStyle(.plain)
                    .frame(width: store.isSubscribed ? 100 : 88)
                    .animation(.spring(response: 0.42, dampingFraction: 0.78), value: store.isSubscribed)
"""
if old_button_modifiers in content:
    content = content.replace(old_button_modifiers, new_button_modifiers, 1)
elif new_button_modifiers not in content:
    raise SystemExit("Could not find Subscribe button sizing modifiers.")

row_padding = """                    .padding(.horizontal, 16)
                    .padding(.bottom, 12)
"""
row_animated = """                    .padding(.horizontal, 16)
                    .padding(.bottom, 12)
                    .animation(.spring(response: 0.42, dampingFraction: 0.78), value: store.isSubscribed)
"""
if row_padding in content:
    content = content.replace(row_padding, row_animated, 1)
elif row_animated not in content:
    raise SystemExit("Could not find public-profile identity row padding.")

content_path.write_text(content)
store_path.write_text(store)
print("Added animated capsule resizing, smooth identity-row layout movement, material blur, and success-only haptics.")
