#if DEBUG
import WebKit

/// Debug builds only (the cloud build uses them for simulator screenshots); release builds have none of this.
/// Launch arguments:
///   -KUSDemo YES          skip the sign-in screen (a local flag only; no account is used)
///   -KUSRoute "#/p/ID"    open that page after the first load
///   -KUSAddress "..."     enter the address on the Voter tab, then open the sample ballot
///   -KUSTapSave YES       with -KUSAddress: tap "Download sample ballot" (tests saving to Files)
/// A trace goes to tmp/kus-debug.txt in the app's container (the cloud build prints it).
enum DebugHooks {
    static var defaults: UserDefaults { .standard }
    static let logURL = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("kus-debug.txt")

    static func log(_ line: String) {
        let text = ISO8601DateFormatter().string(from: Date()) + " " + line + "\n"
        if let h = try? FileHandle(forWritingTo: logURL) {
            h.seekToEndOfFile(); h.write(text.data(using: .utf8)!); try? h.close()
        } else {
            try? text.data(using: .utf8)!.write(to: logURL)
        }
    }

    static let hideGate = "document.documentElement.classList.remove('gated');var g=document.getElementById('gate');if(g)g.style.display='none';"

    static func install(on ucc: WKUserContentController) {
        log("launch demo=\(defaults.bool(forKey: "KUSDemo")) route=\(defaults.string(forKey: "KUSRoute") ?? "-") addr=\(defaults.string(forKey: "KUSAddress") ?? "-") tap=\(defaults.bool(forKey: "KUSTapSave"))")
        guard defaults.bool(forKey: "KUSDemo") else { return }
        let early = "try{localStorage.setItem('kus_session','1');}catch(e){}"
        ucc.addUserScript(WKUserScript(source: early, injectionTime: .atDocumentStart, forMainFrameOnly: true))
        let late = "(function(){var n=0;var t=setInterval(function(){" + hideGate + "if(++n>240)clearInterval(t);},500);})();"
        ucc.addUserScript(WKUserScript(source: late, injectionTime: .atDocumentEnd, forMainFrameOnly: true))
    }

    static func afterFirstLoad(_ web: WKWebView) {
        let probe = "JSON.stringify({href:location.href,bridge:!!window.KnowUSiOS,gate:(function(){var g=document.getElementById('gate');return g?getComputedStyle(g).display:'none';})(),cls:document.documentElement.className,dbg:(window.__kusdbg||[]).slice(-6),toast:((document.getElementById('kustoast')||{}).textContent||'')})"
        for i in 0..<12 {
            DispatchQueue.main.asyncAfter(deadline: .now() + Double(i) * 10.0 + 1.0) {
                web.evaluateJavaScript(probe) { r, e in log("probe \(i): " + ((r as? String) ?? "error \(String(describing: e))")) }
            }
        }
        if let route = defaults.string(forKey: "KUSRoute"), !route.isEmpty {
            let js = "location.hash=" + WebViewController.jsString(route) + ";"
            DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) { web.evaluateJavaScript(js, completionHandler: nil) }
        }
        if let addr = defaults.string(forKey: "KUSAddress"), !addr.isEmpty {
            let tap = defaults.bool(forKey: "KUSTapSave")
                ? "var m=0;var u=setInterval(function(){m++;var b=document.querySelector('section.bal [data-pdfblank]');if(b||m>60){clearInterval(u);D('save button '+!!b);if(b){b.scrollIntoView({block:'center'});setTimeout(function(){b.click();D('clicked');},800);}}},1000);"
                : ""
            let js = """
            (function(){var A=\(WebViewController.jsString(addr));window.__kusdbg=[];function D(x){window.__kusdbg.push(x);}
            location.hash='#/voter';
            function go(k){var i=document.getElementById('vaddr'),g=document.getElementById('vgo');
              if(!i||!g){if(k<30)setTimeout(function(){go(k+1);},1000);else D('no address box');return;}
              i.focus();i.value=A;i.dispatchEvent(new Event('input',{bubbles:true}));i.dispatchEvent(new Event('change',{bubbles:true}));g.click();D('address sent');
              var n=0;var t=setInterval(function(){n++;var app=document.getElementById('app')||document.body;
                var ok=/district/i.test(app.innerText)&&!document.querySelector('#vgo[disabled]');
                if(ok||n>45){clearInterval(t);D(ok?'districts found':'districts timeout');location.hash='#/voter/ballot';\(tap)}},1000);}
            setTimeout(function(){go(0);},2500);})();
            """
            DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) {
                web.evaluateJavaScript(js) { _, e in if let e = e { log("address script error \(e)") } }
            }
        }
    }
}
#endif
