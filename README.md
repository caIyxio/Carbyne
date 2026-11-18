# Carbyne

Carbyne's repository now contains a GitHub Actions deployment pipeline and a native SwiftUI iOS client.

## Website deployment

The provided web export and SwiftUI source are preserved in the ordered base64 chunks under `.github/source-bundle/`. The website workflow extracts that source, validates it, copies the static production output into `dist/` on a GitHub-hosted Ubuntu runner, then sends the already-built `dist/` directory to the existing Netlify site with the Netlify CLI. That CLI invocation is a direct deploy; it does not ask Netlify to run the website build.

Add these GitHub repository or `production` environment secrets before the first production deploy:

- `NETLIFY_AUTH_TOKEN` — a Netlify personal access token.
- `NETLIFY_SITE_ID` — the existing Carbyne site ID.

The workflow intentionally fails before deployment if either secret is missing. It never prints their values. Pull requests build and validate the static site but do not publish production.

## Native iOS app

The native SwiftUI project is under `ios/Carbyne/` after extracting the source bundle. It uses the existing Carbyne Supabase project and the public publishable key already used by the website. Auth sessions use the iOS Keychain through Supabase's Swift SDK.

The iOS workflow applies `.github/scripts/patch-supabase-storage-api.py` after extracting the bundle so the avatar/banner upload calls match the pinned Supabase Swift 2.55.x Storage API. When unpacking locally, apply the same compatibility patch before opening the Xcode project:

```sh
cat .github/source-bundle/part-*.b64 | base64 --decode > /tmp/carbyne-project-source.tar.gz
tar -xzf /tmp/carbyne-project-source.tar.gz -C .
python3 .github/scripts/patch-supabase-storage-api.py
```

On GitHub Actions, the iOS workflow runs XcodeGen and Xcode on a macOS runner, compiles for a generic iOS device without code signing, packages the resulting app as `Carbyne-unsigned.ipa`, and uploads it as the `Carbyne-unsigned-IPA` workflow artifact. The IPA is deliberately unsigned; it must be signed with a sideloading tool and a device-compatible provisioning profile before it can be installed on an iPhone.

## Backend scope discovered during the port

The connected production schema currently exposes `profiles` and `subscriptions`. Its only storage bucket is public `avatars`, limited to JPEG/PNG/AVIF images up to 5 MB. The native app implements those real surfaces: sign-in/sign-up, TOTP MFA, account switching, public channel discovery, profile editing, subscriptions, and avatar/banner upload.

There is currently no conversations/messages table, posts/video table, or video storage bucket in this Supabase project, and the supplied website export does not implement direct messages or a populated feed. The DMs destination therefore states that messaging is not yet backed by the existing platform; the Home feed renders a genuine empty state rather than invented posts. Video publishing cannot be made functional without a backend data model and storage policy.

## Source bundle

The compressed source bundle is stored as ordered text chunks so it can be committed through GitHub's text-file API without altering the original bytes. To unpack it locally from the repository root, use the commands above.

The `Carbyne.png` logo mentioned in the project brief was not present in the supplied ZIP or the repository's original `main` tree, so the app currently uses a native text wordmark rather than substituting an unrelated image.

## Profile likes and future video API

The iOS profile now reads its aggregate likes count from the `profile_like_counts` view. It totals likes across both supported content types: `video` and `spotlight`. A profile with no registered content naturally reports zero.

The shared API is intentionally content-table agnostic so the future video implementation can use it without replacing the profile counter:

1. After creating a video or Spotlight row, register its UUID with `CarbyneStore.registerContent(id:type:)` using `.video` or `.spotlight`.
2. Like it with `CarbyneStore.likeContent(id:creatorID:)`.
3. Remove a like with `CarbyneStore.unlikeContent(id:creatorID:)`.
4. Refresh the profile aggregate with `refreshProfileLikes(for:)`.

The corresponding REST resources are `content_items`, `content_likes`, and `profile_like_counts`. The content registry stores the owner and type; the likes table stores one like per user/content pair. RLS restricts content registration to the signed-in creator, prevents self-likes, and allows users to remove only their own likes. When the future video and Spotlight tables are added, their row UUIDs should be used as the registry IDs.

The production migration is recorded at `supabase/migrations/202611180001_add_content_likes_api.sql`.
