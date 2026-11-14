from pathlib import Path
import re
p=Path('ios/Carbyne/Sources/ContentView.swift')
s=p.read_text()
start=s.index('struct ContentView: View {')
end=s.index('struct UploadScreen: View {')
new='''import SwiftUI
import UIKit
import PhotosUI

struct ContentView: View {
 @EnvironmentObject private var store: CarbyneStore
 @Environment(\\.horizontalSizeClass) private var sizeClass
 @State private var selectedTab: CarbyneTab = .home
 @State private var showDirectory = false
 @State private var showAuth = false
 @State private var showProfileEditor = false
 @State private var showSecurity = false
 @State private var showAlert = false
 private var isPad: Bool { sizeClass == .regular }
 var body: some View {
  VStack(spacing:0) {
   if isPad { HStack { Text("Carbyne").font(.system(size:29,weight:.semibold,design:.rounded)); Spacer(); nav("Home",.home); nav("Moments",.moments); nav("+",.upload); nav("Chat",.messages); nav("Profile",.channel); Button { showDirectory=true } label: { Image(systemName:"magnifyingglass").padding(12) } }.padding(.horizontal,32).padding(.vertical,10).background(.ultraThinMaterial,in:Capsule()).modifier(CarbyneGlass()).padding(.horizontal,32).padding(.top,8) }
   Group { switch selectedTab { case .home: HomeScreen(showDirectory:$showDirectory,selectChannel:openChannel); case .moments: ContentUnavailableView("Moments",systemImage:"circle.dashed",description:Text("Moments will appear here.")); case .messages: MessagesScreen(openAuth:{showAuth=true}); case .upload: UploadScreen(openAuth:{showAuth=true}); case .channel: ChannelScreen(openAuth:{showAuth=true},openEditor:{showProfileEditor=true},openSecurity:{showSecurity=true}) } }.frame(maxWidth:.infinity,maxHeight:.infinity)
   if !isPad { HStack(spacing:0) { phoneTab("house.fill","Home",.home); phoneTab("circle.fill","Moments",.moments); phoneTab("triangle.fill","Upload",.upload); phoneTab("gearshape.fill","Chat",.messages); Button { openOwnProfile() } label: { VStack(spacing:4) { AvatarView(url:store.publicImageURL(path:store.profile?.avatarPath),size:27); Text("Profile").font(.system(size:10,weight:.medium)) }.foregroundStyle(selectedTab == .channel ? Color.accentColor : Color.primary).frame(maxWidth:.infinity) }.buttonStyle(.plain) }.padding(8).background(.ultraThinMaterial,in:Capsule()).modifier(CarbyneGlass()).padding(.horizontal,22).padding(.bottom,5) }
  }.background(Color(uiColor:.systemBackground).ignoresSafeArea())
   .sheet(isPresented:$showAuth){AuthenticationSheet()}.sheet(isPresented:$showProfileEditor){ProfileEditorSheet()}.sheet(isPresented:$showSecurity){MFASettingsSheet()}.sheet(isPresented:$showDirectory){ChannelDirectorySheet(selectChannel:openChannel)}
   .onChange(of:store.errorMessage){_,v in showAlert = v != nil}.alert("Carbyne",isPresented:$showAlert){Button("OK"){store.errorMessage=nil}} message:{Text(store.errorMessage ?? "Something went wrong.")}
 }
 private func nav(_ title:String,_ tab:CarbyneTab)->some View { Button { selectedTab=tab; if tab == .channel { openOwnProfile() } } label:{ Text(title).font(.system(size:14,weight:selectedTab == tab ? .semibold : .medium)).foregroundStyle(selectedTab == tab ? Color.accentColor : Color.primary).padding(.horizontal,13).padding(.vertical,10).background(selectedTab == tab ? Color.primary.opacity(0.08) : .clear,in:Capsule()) }.buttonStyle(.plain) }
 private func phoneTab(_ icon:String,_ title:String,_ tab:CarbyneTab)->some View { Button { selectedTab=tab; if tab == .home { Task{await store.loadChannels()} } } label:{ VStack(spacing:4){Image(systemName:icon).font(.system(size:20));Text(title).font(.system(size:10,weight:.medium))}.foregroundStyle(selectedTab == tab ? Color.accentColor : Color.primary).frame(maxWidth:.infinity) }.buttonStyle(.plain) }
 private func openOwnProfile(){ guard store.session != nil else {showAuth=true;return};selectedTab = .channel;Task{await store.showOwnChannel()} }
 private func openChannel(_ profile:CarbyneProfile){Task{await store.viewChannel(profile);selectedTab = .channel}}
}
private struct CarbyneGlass: ViewModifier { func body(content:Content)->some View { if #available(iOS 26.0,*) { content.glassEffect(.regular.interactive(),in:Capsule()) } else { content.background(.ultraThinMaterial,in:Capsule()).overlay(Capsule().strokeBorder(Color.primary.opacity(0.08))) } } }

struct HomeScreen: View {
 @EnvironmentObject private var store:CarbyneStore
 @Environment(\\.horizontalSizeClass) private var sizeClass
 @Binding var showDirectory:Bool
 let selectChannel:(CarbyneProfile)->Void
 private var isPad:Bool {sizeClass == .regular}
 private let cards=[("I asked 7 AIs to remake Mario Kart and…","2M Views","Habib"),("BIG ROBLOX NEWS!!","8M Views","KreekCraft")]
 var body:some View { ScrollView { VStack(alignment:.leading,spacing:22) { if !isPad { HStack { Text("Carbyne").font(.system(size:34,weight:.semibold,design:.rounded)).tracking(-1.3);Spacer();Button{showDirectory=true}label:{Image(systemName:"magnifyingglass").font(.system(size:18)).frame(width:46,height:46).background(.thinMaterial,in:Circle()).overlay(Circle().strokeBorder(Color.primary.opacity(0.08)))}.accessibilityLabel("Search") } }
 LazyVGrid(columns:isPad ? [GridItem(.flexible()),GridItem(.flexible())] : [GridItem(.flexible())],spacing:28){ForEach(cards,id:\\.0){card in VStack(alignment:.leading,spacing:9){RoundedRectangle(cornerRadius:24).fill(Color(uiColor:.systemGray5)).aspectRatio(isPad ? 1.55 : 1.32,contentMode:.fit).overlay(Image(systemName:"play.rectangle").font(.system(size:28,weight:.light)).foregroundStyle(.tertiary));HStack(spacing:12){Circle().fill(Color(uiColor:.systemGray4)).frame(width:isPad ? 38:58,height:isPad ? 38:58);VStack(alignment:.leading,spacing:2){Text(card.0).font(.system(size:isPad ? 14:17,weight:.semibold)).lineLimit(1);Text(card.1).foregroundStyle(.secondary);Text(card.2).foregroundStyle(.tertiary)}.font(.system(size:isPad ? 12:14));Spacer(minLength:0)} } } }
 if !store.channels.isEmpty { Text("Channels").font(.system(size:21,weight:.semibold));ForEach(store.channels){channel in Button{selectChannel(channel)}label:{ChannelRow(profile:channel,imageURL:store.publicImageURL(path:channel.avatarPath))}.buttonStyle(.plain)} }
 }.padding(.horizontal,isPad ? 34:20).padding(.top,12).padding(.bottom,30).frame(maxWidth:1200).frame(maxWidth:.infinity) }.task{await store.loadChannels()}.refreshable{await store.loadChannels()} }
}
struct MessagesScreen: View {
 @EnvironmentObject private var store: CarbyneStore
 let openAuth: () -> Void
 var body: some View {
  NavigationStack {
   ContentUnavailableView {
    Label("Chat is coming soon", systemImage:"bubble.left.and.bubble.right")
   } description: {
    Text(store.session == nil ? "Sign in to your Carbyne account. Messaging will appear here when the chat service is connected." : "Your Carbyne account is connected. Messaging is not yet available in the current backend.")
   } actions: {
    if store.session == nil { Button("Log in", action:openAuth).buttonStyle(.borderedProminent) }
   }
   .navigationTitle("Chat")
   .navigationBarTitleDisplayMode(.inline)
  }
 }
}

'''
s=s[:start]+new+s[end:]
p.write_text(s)
m=Path('ios/Carbyne/Sources/CarbyneModels.swift'); t=m.read_text().replace('case home, messages, upload, channel','case home, moments, messages, upload, channel');m.write_text(t)
