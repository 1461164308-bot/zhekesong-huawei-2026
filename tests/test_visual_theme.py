"""Liquid glass identity stays present without undoing the step workspace."""
from html.parser import HTMLParser
import unittest

from visual_theme import DESKTOP_HTML


class ThemeElements(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.elements = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class LiquidThemeTests(unittest.TestCase):
    def test_clock_runtime_ticks_pauses_and_reinitializes_without_duplicate_timers(self):
        import json
        import shutil
        import subprocess
        from visual_theme import DESKTOP_JS
        if not shutil.which('node'):
            self.skipTest('Node is required to exercise the browser clock runtime')
        script = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
let now = 1800000000000, serial = 0;
const timers = new Map(), documentEvents = {}, windowEvents = {};
const fields = Object.fromEntries(['data-zh-date','data-zh-hours','data-zh-minutes','data-zh-seconds'].map(k => ['['+k+']', {textContent:'--'}]));
const time = {setAttribute() {}};
const root = {dataset:{ready:'false'},isConnected:true,querySelector: s => s === 'time' ? time : fields[s]};
const document = {hidden:false,documentElement:{dataset:{},style:{setProperty(){}}},getElementById: () => root,
  addEventListener:(k,f)=>documentEvents[k]=f,removeEventListener:(k)=>delete documentEvents[k]};
const window = {matchMedia:()=>({matches:false}),addEventListener:(k,f)=>windowEvents[k]=f,removeEventListener:(k)=>delete windowEvents[k]};
class ClockDate extends Date { constructor(...args) {super(...(args.length ? args : [now]));} static now(){return now;} }
const ctx = {window,document,Date:ClockDate,Intl,MutationObserver:class {observe(){} disconnect(){}},
 setTimeout:f=>{const id=++serial;timers.set(id,f);return id;},clearTimeout:id=>timers.delete(id)};
const initialize = vm.runInNewContext('('+SOURCE+')',ctx);
initialize();
assert.equal(root.dataset.ready,'true');
assert.notEqual(fields['[data-zh-date]'].textContent,'--');
assert.equal(timers.size,1);
const seconds = fields['[data-zh-seconds]'].textContent;
now += 1000;
const [id,callback] = timers.entries().next().value; timers.delete(id); callback();
assert.notEqual(fields['[data-zh-seconds]'].textContent,seconds);
assert.equal(timers.size,1);
initialize(); assert.equal(timers.size,1,'reinitialize must dispose the old timer');
document.hidden=true; documentEvents.visibilitychange(); assert.equal(timers.size,0);
document.hidden=false; documentEvents.visibilitychange(); assert.equal(timers.size,1);
window.__zhihengDesktopRuntime.dispose(); assert.equal(timers.size,0);
console.log('clock runtime OK');
""".replace('SOURCE', json.dumps(DESKTOP_JS))
        result = subprocess.run(['node', '-e', script], text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_glass_surfaces_keep_readable_controls_and_reduced_motion(self):
        from visual_theme import DESKTOP_CSS
        for token in ('backdrop-filter:blur(', 'radial-gradient(', '.zh-liquid-clock',
                      '.zh-liquid-aurora', '@media(prefers-reduced-motion:reduce)',
                      '#zh-nav-buttons', 'overflow:visible !important'):
            self.assertIn(token, DESKTOP_CSS)
        self.assertIn('background:#fff !important', DESKTOP_CSS, 'input and dropdown surfaces must remain readable')

    def test_pointer_micro_interactions_follow_cursor_and_respect_reduced_motion(self):
        from visual_theme import DESKTOP_CSS, DESKTOP_JS
        for token in ('@media (hover:hover)', 'transform:translateY(-1px)', 'transform:scale(1.055)',
                      'transform:rotate(45deg)', 'transition:transform .16s ease'):
            self.assertIn(token, DESKTOP_CSS, token)
        for token in ('pointermove', 'pointerout', 'requestAnimationFrame', '--zh-mx', 'cancelAnimationFrame',
                      '--zh-rx', '--zh-ry', 'IntersectionObserver', 'data-zh-reveal', 'zh-reveal'):
            self.assertIn(token, DESKTOP_JS, token)
        for token in ("classList.remove('zh-reveal'", "setTimeout", "disposed"):
            self.assertIn(token, DESKTOP_JS, token)
        for token in ('rotateX(var(--zh-rx', 'rotateY(var(--zh-ry', 'data-zh-reveal=\"on\"', 'translate:0 12px'):
            self.assertIn(token, DESKTOP_CSS, token)
        self.assertIn('@media(prefers-reduced-motion:reduce)', DESKTOP_CSS)
        self.assertIn('transition:none !important', DESKTOP_CSS, '减弱动效时必须关掉过渡')

    def test_header_restores_accessible_clock_and_date_without_duplicate_steps(self):
        elements = ThemeElements(DESKTOP_HTML).elements
        for attribute in ('data-zh-date', 'data-zh-hours', 'data-zh-minutes', 'data-zh-seconds'):
            self.assertTrue(any(attribute in attrs for _, attrs in elements), attribute)
        self.assertTrue(any(tag == 'time' and attrs.get('aria-label') for tag, attrs in elements))
        self.assertFalse(any(tag == 'a' for tag, _ in elements), 'step navigation must use existing sidebar, not dead anchors')


if __name__ == '__main__':
    unittest.main()
