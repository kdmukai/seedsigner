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


### Rescanning for text that needs translations
Re-generate the `messages.pot` file:
```
# -c TRANSLATOR_NOTE: will extract translator hints identified as comments starting with "# NOTE"
# -s will strip the "NOTE:" part of the translator hint out
# -F specifies the config file
# --add-location=file will include filename but not line-number of msgid
# -o is our target output file
pybabel extract -c TRANSLATOR_NOTE: -s -F babel/babel.cfg --add-location=file -o babel/messages.pot .
```
This will rescan all wrapped text, picking up new strings as well as updating existings strings that have been edited.

Then run `update`:
```
pybabel update -N --no-wrap -i babel/messages.pot -d src/seedsigner/resources/babel

# Or target a specific language code:
pybabel update -N --no-wrap -i babel/messages.pot -d src/seedsigner/resources/babel -l es
```
_note: the `-N` flag prevents babel from trying to use fuzzy matching to re-use existing translations for new strings. The fuzzy matching does not seem to do what we would want so we keep it disabled._

Any newly wrapped text strings will be added to each `messages.po` file. Altered strings will be flagged as needing review to see if the existing translations can still be used.

Once the next round of translations is complete, recompile the results:
```
pybabel compile -d src/seedsigner/resources/babel

# Or target a specific language code:
pybabel compile -d src/seedsigner/resources/babel -l es
```


### Adding support for another language
Assuming you have `extract`ed an updated `messages.pot`, all you have to do is generate the initial version of each new language file:
```
pybabel init -i babel/messages.pot -d src/seedsigner/resources/babel -l es
pybabel init -i babel/messages.pot -d src/seedsigner/resources/babel -l fr
pybabel init -i babel/messages.pot -d src/seedsigner/resources/babel -l de
```

Then `update` and `compile` as above.

The only other step is to add the new language to the LOCALES list in `SettingsDefinition`.


## For Packagers:
The *.mo files are not checked into the repository as (large) binary (large) objects ("BLOBs") should not be checked into git to reduce repo bloat. So they need to be generated after fetching the code:

```
# -f allow fuzzy translations
# -d DIRECTORY points to the root dir for our translation files
pybabel compile -f -d src/seedsigner/resources/babel
```

Note: We don't expect to see any fuzzy translations, but the `extract` step above marks the `messages.pot` file's metadata as `#, fuzzy` which will cause `compile` to ignore the entire file unless `-f` is specified.

<!-- 
In order to make that as transparent as possible, that procedure has been integrated into the setup-process. So it will be executed by:

```
python3 setup.py install
```

Unfortunately, it won't be executed by `pip3 install -e .` even though that has been propagated very long to be the developement-env installation procedure. -->
