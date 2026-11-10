#if DEBUG
import WebKit

/// Debug builds only (the cloud build uses them for simulator screenshots); release builds have none of this.
/// Launch arguments:
///   -KUSDemo YES          skip the sign-in screen (a local flag only; no account is used)
///   -KUSRoute "#/p/ID"    open that page after the first load
///   -KUSAddress "..."     enter the address on the Voter tab, then open the sample ballot
///   -KUSTapSave YES       with -KUSAddress: tap "Download sample ballot" (tests saving to Files)
enum DebugHooks {
    static var defaults: UserDefaults { .standard }

    static func install(on ucc: WKUserContentController) {
        guard defaults.bool(forKey: "KUSDemo") else { return }
        let early = "try{localStorage.setItem('kus_session','1');}catch(e){}"
        ucc.addUserScript(WKUserScript(source: early, injectionTime: .atDocumentStart, forMainFrameOnly: true))
        let late = "(function(){var n=0;var t=setInterval(function(){document.documentElement.classList.remove('gated');if(++n>40)clearInterval(t);},500);})();"
        ucc.addUserScript(WKUserScript(source: late, injectionTime: .atDocumentEnd, forMainFrameOnly: true))
    }

    static func afterFirstLoad(_ web: WKWebView) {
        if let route = defaults.string(forKey: "KUSRoute"), !route.isEmpty {
            let js = "location.hash=" + WebViewController.jsString(route) + ";"
            DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) { web.evaluateJavaScript(js, completionHandler: nil) }
        }
        if let addr = defaults.string(forKey: "KUSAddress"), !addr.isEmpty {
            let tap = defaults.bool(forKey: "KUSTapSave")
                ? "var m=0;var u=setInterval(function(){m++;var b=document.querySelector('section.bal [data-pdfblank]');if(b||m>60){clearInterval(u);if(b){b.scrollIntoView({block:'center'});setTimeout(function(){b.click();},800);}}},1000);"
                : ""
            let js = """
            (function(){var A=\(WebViewController.jsString(addr));
            location.hash='#/voter';
            function go(k){var i=document.getElementById('vaddr'),g=document.getElementById('vgo');
              if(!i||!g){if(k<30)setTimeout(function(){go(k+1);},1000);return;}
              i.focus();i.value=A;i.dispatchEvent(new Event('input',{bubbles:true}));i.dispatchEvent(new Event('change',{bubbles:true}));g.click();
              var n=0;var t=setInterval(function(){n++;var app=document.getElementById('app')||document.body;
                if((/district/i.test(app.innerText)&&!document.querySelector('#vgo[disabled]'))||n>45){clearInterval(t);location.hash='#/voter/ballot';\(tap)}},1000);}
            setTimeout(function(){go(0);},2500);})();
            """
            DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) { web.evaluateJavaScript(js, completionHandler: nil) }
        }
    }
}
#endif
