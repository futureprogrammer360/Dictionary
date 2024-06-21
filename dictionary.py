import re
import urllib
import json

import sublime
import sublime_plugin


class Dictionary:
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean text"""
        # Extract alphanumeric characters
        try:
            text = re.compile(r"[a-zA-Z0-9]+").search(text).group()
        except AttributeError:  # No match in text
            return ""
        return text

    @staticmethod
    def define(text: str, language: str, num_definitions: int = None) -> dict:
        """Get definitions of text and return dictionary of definitions"""
        url = "https://api.dictionaryapi.dev/api/v2/entries/%s/%s" % (language, text)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})) as f:
                response = f.read().decode("utf-8")
        except urllib.error.HTTPError:
            sublime.status_message("No definition found for %s" % text)
            return {}
        except urllib.error.URLError:
            sublime.status_message("Error when defining %s" % text)
            return {}

        response = json.loads(response)[0]
        definitions = {}

        definitions["word"] = response.get("word")
        definitions["phonetic"] = response.get("phonetic")

        meanings = response.get("meanings")

        total_definitions = sum([len(meaning.get("definitions")) for meaning in meanings])
        if num_definitions is None or num_definitions > total_definitions:
            num_definitions = total_definitions

        definitions["meanings"] = []
        for meaning in meanings:
            for i in range(len(meaning.get("definitions"))):
                if len(definitions["meanings"]) < num_definitions:
                    definitions["meanings"].append({
                        "PoS": meaning.get("partOfSpeech"),
                        "definition": meaning.get("definitions")[i].get("definition"),
                        "example": meaning.get("definitions")[i].get("example")
                    })

        return definitions

    @staticmethod
    def show_popup(view: sublime.View, text: str, location: int = -1) -> None:
        """Show popup with definition of text"""
        settings = sublime.load_settings("Dictionary.sublime-settings")
        num_definitions = settings.get("num_definitions", None)
        language = settings.get("language", "en")

        text = Dictionary.clean_text(text)
        if not text:
            return
        definitions = Dictionary.define(text, language, num_definitions)
        if not definitions:
            return

        # Create HTML for definitions
        content = ""
        content += "<h1>%s</h1>" % definitions.get("word")
        content += "<h2>%s</h2>\n" % definitions.get("phonetic")
        for meaning in definitions.get("meanings", []):
            content += """<h2>%s<a href="%s">Copy definition</a></h2>""" % (meaning.get("PoS"), meaning.get("definition"))
            content += "<p>%s</p>" % meaning.get("definition")
            if meaning.get("example"):
                content += "<p><em>%s</em></p>" % meaning.get("example")

        content = """
            <body>
                <style>
                    h1 {
                        font-size: 1.1rem;
                        font-weight: 500;
                        margin: 0 0 0.25em 0;
                        font-family: system;
                    }
                    h2 {
                        font-size: 0.85rem;
                        font-weight: 400;
                        margin: 0 0 0.5em 0;
                    }
                    p {
                        font-size: 0.7rem;
                        margin-top: 0;
                    }
                    a {
                        font-weight: normal;
                        font-style: italic;
                        padding-left: 0.5em;
                        font-size: 0.8rem;
                    }
                </style>
                %s
            </body>
        """ % (content)
        view.show_popup(
            content,
            location=location,
            max_width=1024,
            max_height=512,
            on_navigate=lambda x: Dictionary.copy(view, x)
        )

    @staticmethod
    def copy(view: sublime.View, text: str) -> None:
        """Copy text to clipboard and hide popup"""
        sublime.set_clipboard(text)
        view.hide_popup()
        sublime.status_message("Definition copied to clipboard")


class DictionaryDefineCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        region = self.view.sel()[0]
        if region.begin() == region.end():  # No selection
            selection = self.view.substr(self.view.word(region))  # Text under cursor
        else:
            selection = self.view.substr(region)  # Text selected
        if not selection:
            return

        Dictionary.show_popup(self.view, selection)


class DictionaryEventListener(sublime_plugin.EventListener):
    def on_hover(self, view, point, hover_zone):
        settings = sublime.load_settings("Dictionary.sublime-settings")
        if not settings.get("hover_mode", False):
            return

        word = view.substr(view.word(point))
        if not word:
            return

        Dictionary.show_popup(view, word, location=point)


class DictionaryToggleHoverMode(sublime_plugin.ApplicationCommand):
    def run(self):
        settings = sublime.load_settings("Dictionary.sublime-settings")
        current = settings.get("hover_mode", False)
        settings.set("hover_mode", not current)
        sublime.save_settings("Dictionary.sublime-settings")
        sublime.status_message("Dictionary Hover Mode is %s" % ("on" if not current else "off"))
