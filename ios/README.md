# KnowUS for iPhone

A native iOS app (Swift, WKWebView) around the KnowUS web app, the same idea as the Android app.
It opens https://knowus.sites.tab.bot/ and falls back to https://whosinoffice.sites.tab.bot/.

## What the app does
- **Save PDF / Download sample ballot**: the file is saved to *Files › On My iPhone › KnowUS*. The page shows
  "Saved ✓", and a "Download complete" notification appears. Tapping it opens the file.
- **Links**: links to other websites open in Safari. Mail and phone links open their apps.
- **Offline**: the app shows the saved copy (the site's own offline cache). With no saved copy, it shows an offline screen with **Try again**.
- **Pull to refresh**: works on every page. It is the site's own pull-to-refresh.
- **Display**: the screen runs edge to edge under the notch, with the app icon and the navy flag launch screen.
- **Sign-in**: email and password work. Google sign-in is hidden in 1.0, because Google blocks its sign-in page inside apps.
  Native Google sign-in comes in 1.1. Apple then also requires *Sign in with Apple*.
- **Bundle ID**: `bot.tab.knowus`, iPhone only, iOS 15+.

## Builds (free)
- `.github/workflows/ios.yml` runs on every change under `ios/` on GitHub's free macOS runner (free for public repos). It:
  - builds for the iOS Simulator;
  - compiles an unsigned Release build for real iPhones;
  - installs the app on a simulator and takes screenshots;
  - checks that "Download sample ballot" really saves a PDF into the app's Files folder.
- Artifacts: `KnowUS-ios-simulator` (the .app and build logs) and `KnowUS-ios-screenshots`.
- `.github/workflows/ios-release.yml` (run by hand) signs the app and uploads it to App Store Connect / TestFlight.
  It needs the four secrets listed in the file.

## Getting it onto a real iPhone and the App Store (Shmuel)
1. **Join the Apple Developer Program** in your own name: https://developer.apple.com/programs/enroll/
   - Sign in with your Apple ID. Two-factor authentication must be on.
   - Choose *Individual*. Your name shows as the seller.
   - The fee is Apple's: US$99 a year. Approval usually takes a day or two.
2. **Send Tab your Team ID.** It's at developer.apple.com › Account › Membership details: 10 letters and numbers.
   It is not secret.
3. **Make an App Store Connect API key** at appstoreconnect.apple.com › Users and Access › Integrations ›
   App Store Connect API › Team Keys › **+**.
   - Name it "KnowUS CI" and give it **Admin** access, so the cloud build can create the signing certificate.
   - **Download the .p8 file.** Apple lets you download it only once.
   - Send Tab the **Key ID** and the **Issuer ID** (shown above the list). They are not secret.
4. **Save the .p8 key through the secure link Tab sends you.** Open the .p8 in a text editor, copy all of it,
   and paste it as the password. Never put the key in a chat.
   Tab stores it as GitHub repository secrets, never in the code.
5. **Create the app record**: App Store Connect › Apps › **+** › New App.
   - Platform: iOS. Name: KnowUS (pick another name if it's taken). Language: English (U.S.).
   - Bundle ID: `bot.tab.knowus`. Tab can register it with your key first, so it shows in the list. SKU: `knowus-ios`.
6. **Tab runs `ios-release`.** About 15 minutes later the build is in TestFlight. Install the free **TestFlight** app
   on your iPhone and test KnowUS on your own phone.
7. **The App Store page.** Tab can draft and prepare all of this:
   - description, keywords and category (Reference or News);
   - screenshots (6.9-inch iPhone, from the simulator);
   - support URL (https://knowus.sites.tab.bot/) and privacy policy URL (https://knowus.sites.tab.bot/privacy/);
   - the age rating and the App Privacy answers (email for the account; Google Analytics usage data).
   You review it and press **Submit for Review**. Apple's review usually takes 1–3 days.
8. **A review login for Apple.** The app opens on a sign-in screen, so Apple needs a working email and password for
   a test account. Save it through a secure link as well.

### Review risks to know about
- Apple rejects apps that are "just a website" (guideline 4.2). KnowUS 1.0 adds file saving to Files, notifications,
  offline mode and native links. Adding the Android app's bill and executive-order alerts as native iPhone
  notifications before submitting makes approval more likely.
- Apple doesn't let an app force sign-in for content that isn't personal (5.1.1). Apple may ask that browsing work
  without an account.
- If Google sign-in is added, Sign in with Apple must be added too (4.8).

## Free today: add KnowUS to the home screen
In Safari, open knowus.sites.tab.bot › Share › **Add to Home Screen**. It opens full-screen with its own icon and
launch screen. "Save PDF" opens the share sheet, where *Save to Files* keeps the PDF.
