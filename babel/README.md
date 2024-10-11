# Babel Multilanguage Support

### "Wrapping" text for translation
All you have to do in your code is wrap each piece of English text with the `gettext` shorthand `_()`:
* Wrap python strings: `error="No device was selected."` becomes `error=_("No device was selected.")`
* Use `.format()` to wrap strings with variable injections:
    ```
    mystr = f"My dad's name is {dad.name} and my name is {self.name}."
    mystr = _("My dad's name is {} and my name is {}").format(dad.name, self.name)
    ```

    If there are a lot of variables to inject, placeholder names can be used:
    ```
    mystr = _("My dad's name is {dad_name} and my name is {my_name}").format(dad_name=dad.name, my_name=self.name)
    ```


## Set up `babel`
Install the additional dependency in your local dev environment
```bash
pip install -r babel/requirements-babel.txt
```

Make sure that your local repo has fetched the `seedsigner-translations` submodule. It's configured to add it in src/seedsigner/resources.
```bash
# Need --remote in order to respect the target branch listed in .gitmodules
git submodule update --remote
```


### Pre-configured `babel` commands
The `setup.cfg` file in the project root specifies params for the various `babel` commands discussed below.


### Rescanning for text that needs translations
Re-generate the `messages.pot` file:

```bash
python setup.py extract_messaages
```

This will rescan all wrapped text, picking up new strings as well as updating existings strings that have been edited.

_TODO: Github Action to auto-generate messages.pot and fail a PR update if the PR has an out of date messages.pot._



### Making new text available to translators
Upload the master `messages.pot` to Transifex. It will automatically update each language with the new or changed source strings.

_TODO: Look into Transifex options to automatically pull updates._



### Once new translations are complete
The translation file for each language will need to be downloaded via Transifex's "Download for use" option (sends you a `messages.po` file for that language).

This updated `messages.po` will need to be added to the seedsigner-translations repo in l10n/`{TARGET_LOCALE}`/LC_MESSAGES.


### Compile all the translations
The `messages.po` files must be compiled into `*.mo` files:

```bash
python compile_messages

# Or target a specific language code:
python compile_messages -l es
```


## Keep the seedsigner-translations repo up to date
The *.po files for each language and their compiled *.mo files should all be kept up to date in the seedsigner-translations repo.

_TODO: Github Actions automation to regenerate / verify that the *.mo files have been updated after *.po changes._
