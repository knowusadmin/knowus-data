import UIKit
import WebKit
import QuickLook
import UserNotifications

/// KnowUS for iPhone: a native shell around the KnowUS web app (same idea as the Android app).
/// - loads https://knowus.sites.tab.bot/ (falls back to https://whosinoffice.sites.tab.bot/)
/// - files the page saves (sample ballot "Save PDF") go to Files > On My iPhone > KnowUS, with a "Download complete" notice
/// - links to other sites open in Safari; mail/phone links open their apps
/// - offline: the saved copy (the site's own offline cache), else an offline screen with "Try again"
/// - pull-to-refresh is the site's own (ptr.js), which works in this web view
final class WebViewController: UIViewController, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate, QLPreviewControllerDataSource {

    static let startURL = URL(string: "https://knowus.sites.tab.bot/")!
    static let fallbackURL = URL(string: "https://whosinoffice.sites.tab.bot/")!
    static let appHosts: Set<String> = ["knowus.sites.tab.bot", "whosinoffice.sites.tab.bot"]
    static let authHosts: Set<String> = ["knowus-6b767.firebaseapp.com", "accounts.google.com"]
    static let navy = UIColor(red: 0x14 / 255.0, green: 0x23 / 255.0, blue: 0x3c / 255.0, alpha: 1)
    static let paper = UIColor(red: 0xf4 / 255.0, green: 0xf6 / 255.0, blue: 0xfa / 255.0, alpha: 1)

    private var webView: WKWebView!
    private let offlineView = UIView()
    private let spinner = UIActivityIndicatorView(style: .large)
    private var triedCache = false
    private var triedFallback = false
    private var firstPageDone = false
    private var previewURL: URL?
    private var downloadTargets: [ObjectIdentifier: URL] = [:]

    private var appVersion: String {
        (Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String) ?? "1.0"
    }

    override var preferredStatusBarStyle: UIStatusBarStyle { .lightContent }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = Self.navy

        let config = WKWebViewConfiguration()
        config.websiteDataStore = .default()
        config.allowsInlineMediaPlayback = true
        config.applicationNameForUserAgent = "Mobile/15E148 Safari/604.1 KnowUS-iOS/" + appVersion

        let ucc = WKUserContentController()
        let bridge = WebViewController.bridgeJS.replacingOccurrences(of: "__VERSION__", with: appVersion)
        ucc.addUserScript(WKUserScript(source: bridge, injectionTime: .atDocumentStart, forMainFrameOnly: true))
        ucc.add(ScriptProxy(self), name: "kus")
        #if DEBUG
        DebugHooks.install(on: ucc)
        #endif
        config.userContentController = ucc

        webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.allowsBackForwardNavigationGestures = true
        webView.isOpaque = false
        webView.backgroundColor = Self.paper
        webView.scrollView.backgroundColor = Self.navy
        webView.scrollView.contentInsetAdjustmentBehavior = .never   // the page pads itself with env(safe-area-inset-*)
        webView.scrollView.bounces = false                          // the site's own pull-to-refresh (ptr.js) handles the pull
        #if DEBUG
        if #available(iOS 16.4, *) { webView.isInspectable = true }
        #endif
        webView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(webView)
        NSLayoutConstraint.activate([
            webView.topAnchor.constraint(equalTo: view.topAnchor),
            webView.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            webView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            webView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
        ])

        spinner.color = .white
        spinner.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(spinner)
        NSLayoutConstraint.activate([
            spinner.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            spinner.centerYAnchor.constraint(equalTo: view.centerYAnchor),
        ])
        spinner.startAnimating()

        buildOfflineView()
        webView.load(URLRequest(url: Self.startURL))
    }

    // MARK: - Navigation

    private func isAppHost(_ url: URL?) -> Bool {
        guard let url = url, let scheme = url.scheme?.lowercased(), scheme == "https" || scheme == "http",
              let host = url.host?.lowercased() else { return false }
        return Self.appHosts.contains(host)
    }

    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = navigationAction.request.url else { decisionHandler(.cancel); return }
        let scheme = url.scheme?.lowercased() ?? ""
        if #available(iOS 14.5, *), navigationAction.shouldPerformDownload {
            decisionHandler(.download); return
        }
        if ["about", "blob", "data"].contains(scheme) { decisionHandler(.allow); return }
        if ["mailto", "tel", "sms", "facetime", "maps"].contains(scheme) {
            UIApplication.shared.open(url); decisionHandler(.cancel); return
        }
        // sub-frames (embeds, the sign-in helper frame) load in place
        if let frame = navigationAction.targetFrame, !frame.isMainFrame { decisionHandler(.allow); return }
        if isAppHost(url) { decisionHandler(.allow); return }
        if scheme == "http" || scheme == "https" {
            UIApplication.shared.open(url)   // other websites open in Safari
        }
        decisionHandler(.cancel)
    }

    func webView(_ webView: WKWebView, decidePolicyFor navigationResponse: WKNavigationResponse,
                 decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
        if #available(iOS 14.5, *), !navigationResponse.canShowMIMEType {
            decisionHandler(.download); return
        }
        if navigationResponse.isForMainFrame, let http = navigationResponse.response as? HTTPURLResponse,
           http.statusCode >= 500, !triedFallback, http.url?.host == Self.startURL.host {
            triedFallback = true
            decisionHandler(.cancel)
            webView.load(URLRequest(url: Self.fallbackURL))
            return
        }
        decisionHandler(.allow)
    }

    func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) {
        offlineView.isHidden = true
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        if !firstPageDone {
            firstPageDone = true
            spinner.stopAnimating()
            #if DEBUG
            DebugHooks.afterFirstLoad(webView)
            #endif
        }
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        handleLoadError(error)
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        handleLoadError(error)
    }

    private func handleLoadError(_ error: Error) {
        let ns = error as NSError
        if ns.domain == NSURLErrorDomain && ns.code == NSURLErrorCancelled { return }
        if ns.domain == "WebKitErrorDomain" && ns.code == 102 { return }   // frame load interrupted (a download)
        let offline = [NSURLErrorNotConnectedToInternet, NSURLErrorNetworkConnectionLost,
                       NSURLErrorDataNotAllowed, NSURLErrorInternationalRoamingOff].contains(ns.code)
        if !offline && !triedFallback {
            triedFallback = true
            webView.load(URLRequest(url: Self.fallbackURL))
            return
        }
        if !triedCache {
            // Offline or flaky: try the saved copy.
            triedCache = true
            let url = webView.url ?? Self.startURL
            webView.load(URLRequest(url: url, cachePolicy: .returnCacheDataDontLoad, timeoutInterval: 20))
            return
        }
        spinner.stopAnimating()
        offlineView.isHidden = false
    }

    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        webView.reload()
    }

    @objc private func retry() {
        triedCache = false
        triedFallback = false
        offlineView.isHidden = true
        spinner.startAnimating()
        webView.load(URLRequest(url: Self.startURL))
    }

    private func buildOfflineView() {
        offlineView.backgroundColor = Self.navy
        offlineView.isHidden = true
        offlineView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(offlineView)
        NSLayoutConstraint.activate([
            offlineView.topAnchor.constraint(equalTo: view.topAnchor),
            offlineView.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            offlineView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            offlineView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
        ])
        let title = UILabel()
        title.text = "You\u{2019}re offline"
        title.font = .systemFont(ofSize: 24, weight: .bold)
        title.textColor = .white
        title.textAlignment = .center
        let body = UILabel()
        body.text = "KnowUS couldn\u{2019}t reach the internet and has no saved copy yet. Connect and try again."
        body.font = .systemFont(ofSize: 16)
        body.textColor = UIColor.white.withAlphaComponent(0.8)
        body.textAlignment = .center
        body.numberOfLines = 0
        let button = UIButton(type: .system)
        button.setTitle("Try again", for: .normal)
        button.titleLabel?.font = .systemFont(ofSize: 17, weight: .semibold)
        button.setTitleColor(Self.navy, for: .normal)
        button.backgroundColor = .white
        button.layer.cornerRadius = 12
        button.contentEdgeInsets = UIEdgeInsets(top: 12, left: 28, bottom: 12, right: 28)
        button.addTarget(self, action: #selector(retry), for: .touchUpInside)
        let stack = UIStackView(arrangedSubviews: [title, body, button])
        stack.axis = .vertical
        stack.spacing = 16
        stack.alignment = .center
        stack.translatesAutoresizingMaskIntoConstraints = false
        offlineView.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.centerYAnchor.constraint(equalTo: offlineView.centerYAnchor),
            stack.leadingAnchor.constraint(equalTo: offlineView.leadingAnchor, constant: 32),
            stack.trailingAnchor.constraint(equalTo: offlineView.trailingAnchor, constant: -32),
        ])
    }

    // MARK: - Pop-ups (target=_blank, window.open)

    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                 for navigationAction: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        guard let url = navigationAction.request.url else { return nil }
        if isAppHost(url) {
            webView.load(navigationAction.request)
        } else if let host = url.host?.lowercased(), Self.authHosts.contains(host) {
            let a = UIAlertController(title: "Google sign-in",
                                      message: "Google sign-in isn\u{2019}t available in the iPhone app yet. Sign in with your email and password, or open KnowUS in Safari to use Google.",
                                      preferredStyle: .alert)
            a.addAction(UIAlertAction(title: "Open in Safari", style: .default) { _ in UIApplication.shared.open(Self.startURL) })
            a.addAction(UIAlertAction(title: "OK", style: .cancel))
            present(a, animated: true)
        } else if url.scheme == "https" || url.scheme == "http" {
            UIApplication.shared.open(url)
        }
        return nil
    }

    func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) {
        let a = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        a.addAction(UIAlertAction(title: "OK", style: .default) { _ in completionHandler() })
        present(a, animated: true)
    }

    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        let a = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        a.addAction(UIAlertAction(title: "Cancel", style: .cancel) { _ in completionHandler(false) })
        a.addAction(UIAlertAction(title: "OK", style: .default) { _ in completionHandler(true) })
        present(a, animated: true)
    }

    // MARK: - Files from the page (bridge)

    func handleBridge(_ body: Any) {
        guard isAppHost(webView.url), let m = body as? [String: Any], let op = m["op"] as? String else { return }
        #if DEBUG
        DebugHooks.log("bridge op=\(op) name=\((m["name"] as? String) ?? "-") bytes=\(((m["data"] as? String) ?? "").count)")
        #endif
        switch op {
        case "save", "share":
            let raw = (m["data"] as? String) ?? ""
            let name = (m["name"] as? String) ?? "KnowUS-file"
            let mime = (m["mime"] as? String) ?? ""
            guard let data = Self.decode(raw) else { pageToast("Couldn\u{2019}t save the file"); return }
            do {
                let url = try Self.write(data, name: name, mime: mime)
                if op == "share" { share(url) } else { saved(url) }
            } catch {
                pageToast("Couldn\u{2019}t save the file")
            }
        default:
            pageToast("Couldn\u{2019}t save the file")
        }
    }

    static func decode(_ raw: String) -> Data? {
        if raw.hasPrefix("data:"), let comma = raw.firstIndex(of: ",") {
            let header = raw[..<comma]
            let payload = String(raw[raw.index(after: comma)...])
            if header.contains(";base64") { return Data(base64Encoded: payload, options: .ignoreUnknownCharacters) }
            return payload.removingPercentEncoding?.data(using: .utf8)
        }
        return Data(base64Encoded: raw, options: .ignoreUnknownCharacters)
    }

    static func documentsDir() -> URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
    }

    static func safeName(_ name: String, mime: String) -> String {
        var n = name.components(separatedBy: CharacterSet(charactersIn: "/\\:?%*|\"<>\n\r")).joined(separator: "-")
        n = n.trimmingCharacters(in: .whitespacesAndNewlines)
        if n.isEmpty { n = "KnowUS-file" }
        if !n.contains("."), mime == "application/pdf" { n += ".pdf" }
        return String(n.prefix(120))
    }

    static func uniqueURL(_ name: String) -> URL {
        let dir = documentsDir()
        var url = dir.appendingPathComponent(name)
        let base = url.deletingPathExtension().lastPathComponent
        let ext = url.pathExtension
        var i = 2
        while FileManager.default.fileExists(atPath: url.path) {
            url = dir.appendingPathComponent(ext.isEmpty ? "\(base) (\(i))" : "\(base) (\(i)).\(ext)")
            i += 1
        }
        return url
    }

    static func write(_ data: Data, name: String, mime: String) throws -> URL {
        let url = uniqueURL(safeName(name, mime: mime))
        try data.write(to: url, options: .atomic)
        return url
    }

    private func saved(_ url: URL) {
        #if DEBUG
        DebugHooks.log("saved \(url.lastPathComponent)")
        #endif
        pageToast("Saved \u{2713} \u{2014} in Files \u{203A} On My iPhone \u{203A} KnowUS", delay: 1.0)
        notifyDownload(url)
    }

    private func share(_ url: URL) {
        let vc = UIActivityViewController(activityItems: [url], applicationActivities: nil)
        vc.popoverPresentationController?.sourceView = view
        present(vc, animated: true)
    }

    private func pageToast(_ text: String, delay: Double = 0) {
        let js = "if(window.KUS_TOAST){KUS_TOAST(\(Self.jsString(text)),true);}"
        DispatchQueue.main.asyncAfter(deadline: .now() + delay) { [weak self] in
            guard let self = self, self.isAppHost(self.webView.url) else { return }
            self.webView.evaluateJavaScript(js, completionHandler: nil)
        }
    }

    static func jsString(_ s: String) -> String {
        let data = try? JSONSerialization.data(withJSONObject: [s], options: [])
        let arr = data.flatMap { String(data: $0, encoding: .utf8) } ?? "[\"\"]"
        return String(arr.dropFirst().dropLast())
    }

    private func notifyDownload(_ url: URL) {
        let center = UNUserNotificationCenter.current()
        center.requestAuthorization(options: [.alert, .sound]) { granted, _ in
            guard granted else { return }
            let content = UNMutableNotificationContent()
            content.title = "Download complete"
            content.body = url.lastPathComponent + " \u{2014} saved to Files \u{203A} KnowUS. Tap to open."
            content.sound = .default
            content.userInfo = ["path": url.path]
            center.add(UNNotificationRequest(identifier: "kus-dl-" + UUID().uuidString, content: content, trigger: nil))
        }
    }

    func preview(_ url: URL) {
        guard FileManager.default.fileExists(atPath: url.path) else { return }
        previewURL = url
        let q = QLPreviewController()
        q.dataSource = self
        if presentedViewController != nil { dismiss(animated: false) }
        present(q, animated: true)
    }

    func numberOfPreviewItems(in controller: QLPreviewController) -> Int { previewURL == nil ? 0 : 1 }

    func previewController(_ controller: QLPreviewController, previewItemAt index: Int) -> QLPreviewItem {
        (previewURL ?? Self.documentsDir()) as NSURL
    }

    // MARK: - WKDownload (links the page marks as downloads, files the web view can't show)

    @available(iOS 14.5, *)
    func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) {
        download.delegate = self
    }

    @available(iOS 14.5, *)
    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) {
        download.delegate = self
    }

    @available(iOS 14.5, *)
    func download(_ download: WKDownload, decideDestinationUsing response: URLResponse,
                  suggestedFilename: String, completionHandler: @escaping (URL?) -> Void) {
        let url = Self.uniqueURL(Self.safeName(suggestedFilename, mime: response.mimeType ?? ""))
        downloadTargets[ObjectIdentifier(download)] = url
        completionHandler(url)
    }

    @available(iOS 14.5, *)
    func downloadDidFinish(_ download: WKDownload) {
        if let url = downloadTargets.removeValue(forKey: ObjectIdentifier(download)) { saved(url) }
    }

    @available(iOS 14.5, *)
    func download(_ download: WKDownload, didFailWithError error: Error, resumeData: Data?) {
        downloadTargets.removeValue(forKey: ObjectIdentifier(download))
        pageToast("Couldn\u{2019}t save the file")
    }

    // MARK: - Bridge script

    static let bridgeJS = """
(function(){
'use strict';
var HOSTS=['knowus.sites.tab.bot','whosinoffice.sites.tab.bot'];
if(HOSTS.indexOf(location.hostname)<0||window.KnowUSiOS)return;
/* Google blocks its sign-in page inside apps: hide the Google button here (email sign-in works) */
try{var st=document.createElement('style');st.textContent='#gbtn{display:none!important}';(document.head||document.documentElement).appendChild(st);}catch(e){}
function post(m){try{window.webkit.messageHandlers.kus.postMessage(m);return true;}catch(e){return false;}}
function isFile(a){return !!a&&!!a.hasAttribute&&a.hasAttribute('download')&&/^(blob|data):/i.test(a.href||'');}
function send(href,name){
  fetch(href).then(function(r){return r.blob();}).then(function(b){return new Promise(function(res,rej){
    var fr=new FileReader();fr.onload=function(){res({d:String(fr.result),t:b.type||''});};fr.onerror=function(){rej(fr.error);};fr.readAsDataURL(b);});})
  .then(function(x){post({op:'save',data:x.d,name:name||'KnowUS-file',mime:x.t});})
  .catch(function(e){post({op:'error',message:String(e&&e.message||e)});});
}
/* the page saves files by clicking a hidden <a download href="blob:..."> (ballot.js): hand those to the app */
var click=HTMLAnchorElement.prototype.click;
HTMLAnchorElement.prototype.click=function(){if(isFile(this)){send(this.href,this.getAttribute('download')||'');return;}return click.apply(this,arguments);};
document.addEventListener('click',function(e){var a=e.target&&e.target.closest&&e.target.closest('a[download]');
  if(isFile(a)){e.preventDefault();e.stopPropagation();send(a.href,a.getAttribute('download')||'');}},true);
window.KnowUSiOS={
  version:function(){return '__VERSION__';},
  capabilities:function(){return 'files,share';},
  saveFile:function(d,n,m){return post({op:'save',data:String(d),name:String(n||'KnowUS-file'),mime:String(m||'')})?'pending':'error';},
  shareFile:function(d,n,m){return post({op:'share',data:String(d),name:String(n||'KnowUS-file'),mime:String(m||'')})?'pending':'error';}
};
})();
"""
}

/// Breaks the retain cycle between the content controller and the view controller.
final class ScriptProxy: NSObject, WKScriptMessageHandler {
    weak var target: WebViewController?
    init(_ target: WebViewController) { self.target = target }
    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        target?.handleBridge(message.body)
    }
}
