"""Regression tests for the actual standalone page, using Chromium's DOM."""

from pathlib import Path
import unittest

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUBJECTS = {
    "biological": "full human body",
    "mechanical": "complex engine",
    "architectural": "modern skyscraper",
    "cybernetic": "android prototype",
}
BASE_NEGATIVE = (
    "cluttered background, random scenery, sloppy labels, unreadable text, "
    "cartoon style, messy effects, opaque exterior blocking internals"
)
DOMAIN_NEGATIVES = {
    "biological": "gore, blood, exposed flesh, horror, injury, deformed anatomy, body horror",
    "mechanical": "broken parts, impossible mechanisms, floating unrelated components, warped geometry",
    "architectural": "people blocking view, messy construction, warped perspective, impossible stairs, illogical floorplans",
    "cybernetic": "messy wires, organic decay, rust, unorganized cabling, grotesque fusion",
}


class PromptGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.page_errors = []
        self.page.on("pageerror", lambda error: self.page_errors.append(str(error)))
        self.page.goto((ROOT / "index.html").as_uri())

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.page_errors, [], "Unexpected uncaught browser errors")

    def output(self):
        return self.page.locator("#promptOutput").text_content()

    def toast(self):
        return self.page.locator("#toast").text_content()

    def configure_clipboard(self, api="missing", fallback="success", secure=True):
        """Stub browser clipboard boundaries, leaving DOM and application code real."""
        self.page.evaluate("""({api, fallback, secure}) => {
          window.copyCalls = {api: [], fallback: []};
          Object.defineProperty(window, 'isSecureContext', {configurable: true, value: secure});
          Object.defineProperty(navigator, 'clipboard', {configurable: true, value:
            api === 'missing' ? undefined : {writeText: async text => {
              window.copyCalls.api.push(text);
              if (api === 'reject') throw new Error('Clipboard access denied');
            }}
          });
          document.execCommand = command => {
            window.copyCalls.fallback.push({command, text: document.activeElement.value});
            if (fallback === 'throw') throw new Error('Legacy copy failed');
            return fallback === 'success';
          };
        }""", {"api": api, "fallback": fallback, "secure": secure})

    def assert_fallback_cleaned_up(self):
        self.assertEqual(self.page.locator("textarea").count(), 1)
        self.assertEqual(self.page.evaluate("document.activeElement.id"), "copyPrompt")

    def test_initial_prompt_matches_approved_format(self):
        expected = (ROOT / "tests" / "fixtures" / "default-prompt.txt").read_text().rstrip("\n")
        self.assertEqual(self.output(), expected)
        self.assertEqual(self.page.evaluate("buildPrompt()"), expected)

    def test_build_prompt_defaults_for_every_domain_and_blank_input(self):
        for domain, subject in DEFAULT_SUBJECTS.items():
            for blank in ["", "   "]:
                with self.subTest(domain=domain, blank=blank):
                    self.page.select_option("#subjectType", domain)
                    self.page.fill("#subjectInput", blank)
                    result = self.page.evaluate("buildPrompt()")
                    self.assertIn(f"of a {subject} ({domain} subject)", result)
                    self.assertIn(DOMAIN_NEGATIVES[domain], result)
                    self.assertEqual(result, self.output())

    def test_build_prompt_uses_all_form_fields_and_live_events(self):
        self.page.select_option("#subjectType", "mechanical")
        self.page.fill("#subjectInput", "  gas turbine  ")
        selections = {
            "sourceUse": "Use as loose inspiration for silhouette and composition.",
            "visualMode": "cutaway illustration",
            "cameraAngle": "isometric 3/4 angle",
            "detailFocus": "Prioritize fluid pathways, energy routing, or nervous systems.",
            "lightingStyle": "cool radiographic glow with high contrast",
            "backgroundStyle": "dark blueprint grid with measurement lines",
            "paletteStyle": "high-contrast grayscale with bright single-color focal points",
        }
        for field, selected in selections.items():
            before = self.output()
            self.page.select_option(f"#{field}", selected)
            self.assertNotEqual(self.output(), before, field)
            self.assertIn(selected, self.output(), field)
        self.page.fill("#extraNotes", "  Highlight fuel injectors\nKeep labels readable  ")
        result = self.output()
        self.assertTrue(result.startswith("[CONCEPT]: cutaway illustration of a gas turbine (mechanical subject)\n"))
        self.assertIn("[CUSTOM NOTES]:\nHighlight fuel injectors\nKeep labels readable\n\n[NEGATIVE PROMPT]:", result)
        self.assertNotIn("  gas turbine  ", result)

    def test_whitespace_only_notes_are_omitted(self):
        self.page.fill("#extraNotes", " \n\t ")
        self.assertNotIn("[CUSTOM NOTES]", self.output())

    def test_user_markup_is_literal_text_and_unicode_and_spacing_survive(self):
        subject = '<img src=x onerror="window.injected=true">'
        notes = "Español: válvula → 35 °C\n\n\n\t<script>window.injected=true</script>"
        self.page.fill("#subjectInput", subject)
        self.page.fill("#extraNotes", notes)
        self.assertIn(subject, self.output())
        self.assertIn(notes, self.output())
        self.assertEqual(self.page.locator("#promptOutput *").count(), 0)
        self.assertFalse(self.page.evaluate("Boolean(window.injected)"))

    def test_negative_prompt_all_domains_and_exploded_modifier(self):
        for domain, negative in DOMAIN_NEGATIVES.items():
            for mode in ["cutaway illustration", "exploded-view diagram"]:
                with self.subTest(domain=domain, mode=mode):
                    result = self.page.evaluate("([domain, mode]) => getNegativePrompt(domain, mode)", [domain, mode])
                    expected = f"{BASE_NEGATIVE}, {negative}"
                    if mode == "exploded-view diagram":
                        expected += ", messy explosion, chaotic scatter, unorganized spacing"
                    self.assertEqual(result, expected)

    def test_subject_switch_updates_presets_and_preserves_custom_subjects(self):
        for domain, subject in DEFAULT_SUBJECTS.items():
            self.page.select_option("#subjectType", domain)
            self.assertEqual(self.page.input_value("#subjectInput"), subject)
        self.page.fill("#subjectInput", "  COMPLEX ENGINE  ")
        self.page.select_option("#subjectType", "architectural")
        self.assertEqual(self.page.input_value("#subjectInput"), "modern skyscraper")
        self.page.fill("#subjectInput", "My custom turbine")
        self.page.select_option("#subjectType", "biological")
        self.assertEqual(self.page.input_value("#subjectInput"), "My custom turbine")
        self.assertIn("My custom turbine (biological subject)", self.output())

    def test_reset_restores_every_control_and_prompt(self):
        baseline = self.output()
        defaults = self.page.locator("select, input, textarea").evaluate_all("nodes => nodes.map(n => [n.id, n.value])")
        for control in self.page.locator("select").all():
            control.select_option(index=1)
        self.page.fill("#subjectInput", "custom subject")
        self.page.fill("#extraNotes", "custom notes")
        self.page.click("#resetForm")
        self.assertEqual(self.output(), baseline)
        self.assertEqual(self.page.locator("select, input, textarea").evaluate_all("nodes => nodes.map(n => [n.id, n.value])"), defaults)
        self.assertEqual(self.toast(), "Systems Rebooted.")

    def test_modern_clipboard_copies_current_prompt_without_fallback(self):
        self.configure_clipboard(api="success", fallback="throw")
        self.page.locator("#subjectInput").evaluate("node => node.value = 'Latest subject'")
        self.page.click("#copyPrompt")
        self.assertEqual(self.toast(), "Data Copied (API)")
        calls = self.page.evaluate("window.copyCalls")
        self.assertEqual(calls["api"], [self.output()])
        self.assertIn("Latest subject", calls["api"][0])
        self.assertEqual(calls["fallback"], [])
        self.assertEqual(self.page.locator("textarea").count(), 1)

    def test_modern_clipboard_rejection_uses_fallback(self):
        self.configure_clipboard(api="reject")
        self.page.click("#copyPrompt")
        self.assertEqual(self.toast(), "Data Copied (Fallback)")
        calls = self.page.evaluate("window.copyCalls")
        self.assertEqual(calls["api"], [self.output()])
        self.assertEqual(calls["fallback"], [{"command": "copy", "text": self.output()}])
        self.assert_fallback_cleaned_up()

    def test_missing_clipboard_uses_fallback(self):
        self.configure_clipboard()
        self.page.click("#copyPrompt")
        self.assertEqual(self.toast(), "Data Copied (Fallback)")
        self.assertEqual(self.page.evaluate("window.copyCalls.fallback"), [{"command": "copy", "text": self.output()}])
        self.assert_fallback_cleaned_up()

    def test_insecure_context_skips_modern_clipboard(self):
        self.configure_clipboard(api="success", secure=False)
        self.page.click("#copyPrompt")
        self.assertEqual(self.toast(), "Data Copied (Fallback)")
        self.assertEqual(self.page.evaluate("window.copyCalls.api"), [])
        self.assert_fallback_cleaned_up()

    def test_fallback_false_reports_failure_and_cleans_up(self):
        self.configure_clipboard(fallback="false")
        self.page.click("#copyPrompt")
        self.assertEqual(self.toast(), "Copy Failed.")
        self.assert_fallback_cleaned_up()

    def test_exec_command_exception_is_caught_and_cleans_up_on_repeated_attempts(self):
        self.configure_clipboard(api="reject", fallback="throw")
        errors = []
        self.page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        for _ in range(2):
            self.page.click("#copyPrompt")
            self.assertEqual(self.toast(), "Copy Error.")
            self.assert_fallback_cleaned_up()
        self.assertEqual(len(self.page.evaluate("window.copyCalls.fallback")), 2)
        self.assertEqual(len(errors), 2)
        self.assertTrue(all("Fallback copy failed" in error for error in errors))

    def test_toast_stays_visible_for_two_seconds_after_latest_message(self):
        self.page.clock.install()
        self.page.evaluate("showToast('First message')")
        self.page.clock.run_for(1500)
        self.page.evaluate("showToast('Second message')")
        self.page.clock.run_for(500)
        self.assertEqual(self.toast(), "Second message")
        self.assertTrue(self.page.locator("#toast").evaluate("node => node.classList.contains('show')"))
        self.page.clock.run_for(1499)
        self.assertTrue(self.page.locator("#toast").evaluate("node => node.classList.contains('show')"))
        self.page.clock.run_for(1)
        self.assertFalse(self.page.locator("#toast").evaluate("node => node.classList.contains('show')"))


if __name__ == "__main__":
    unittest.main()
