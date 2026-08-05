"""
Project settings.

Settings answer "what should this project do by default". Three things matter:
the plugin works with no settings file at all, a written file wins over the
defaults, and a command can tell "you configured this" from "this is just the
default" — which is what keeps it from asking twice.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS = Path(__file__).parent.parent / 'plugins' / 'chapterwise' / 'scripts'
SCRIPT = SCRIPTS / 'settings.py'
sys.path.insert(0, str(SCRIPTS))

from settings import (  # noqa: E402
    DEFAULTS,
    SETTINGS_VERSION,
    action_get,
    action_resolve,
    action_set,
    find_project_root,
    load,
    resolve_report_dir,
    validate,
)


@pytest.fixture
def project(tmp_path):
    """A project with a manuscript one folder down."""
    (tmp_path / '.git').mkdir()
    book = tmp_path / 'book'
    book.mkdir()
    src = book / 'chapter-01.codex.yaml'
    src.write_text('id: c1\ntype: chapter\nname: One\nbody: x\n', encoding='utf-8')
    return tmp_path, src


def write_settings(root: Path, payload: dict) -> Path:
    path = root / '.chapterwise' / 'settings.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding='utf-8')
    return path


class TestDefaults:
    def test_codex_into_an_analysis_folder(self):
        assert DEFAULTS['analysis']['report_format'] == 'codex'
        assert DEFAULTS['analysis']['output_dir'] == 'analysis'

    def test_no_settings_file_still_yields_usable_settings(self, project):
        root, src = project
        effective, sources, path, found = load(src)
        assert found is False
        assert effective['analysis']['report_format'] == 'codex'
        assert sources['analysis.report_format'] == 'default'
        assert not path.exists()

    def test_nothing_is_written_just_by_reading(self, project):
        root, src = project
        load(src)
        assert not (root / '.chapterwise').exists()


class TestProjectRoot:
    def test_chapterwise_folder_wins(self, project):
        root, src = project
        (root / 'book' / '.chapterwise').mkdir()
        assert find_project_root(src) == root / 'book'

    def test_falls_back_to_the_index(self, tmp_path):
        (tmp_path / 'index.codex.yaml').write_text('id: i\n', encoding='utf-8')
        deep = tmp_path / 'a' / 'b'
        deep.mkdir(parents=True)
        assert find_project_root(deep) == tmp_path

    def test_a_loose_manuscript_is_its_own_project(self, tmp_path):
        src = tmp_path / 'loose.codex.yaml'
        src.write_text('id: l\n', encoding='utf-8')
        assert find_project_root(src) == tmp_path


class TestReportDir:
    def test_relative_lands_beside_the_analyzed_file(self, project):
        _root, src = project
        assert resolve_report_dir(src, 'analysis') == src.parent / 'analysis'

    def test_dot_slash_is_the_same_thing(self, project):
        _root, src = project
        assert resolve_report_dir(src, './reports') == src.parent / 'reports'

    def test_leading_slash_means_project_root_not_filesystem_root(self, project):
        root, src = project
        assert resolve_report_dir(src, '/reports') == root / 'reports'

    def test_tilde_is_a_literal_path(self, project):
        _root, src = project
        assert resolve_report_dir(src, '~/somewhere') == Path.home() / 'somewhere'

    def test_empty_falls_back_to_the_default(self, project):
        _root, src = project
        assert resolve_report_dir(src, '') == src.parent / 'analysis'


class TestReadingWhatIsWritten:
    def test_a_written_setting_beats_the_default(self, project):
        root, src = project
        write_settings(root, {'version': 1, 'analysis': {'report_format': 'markdown'}})
        effective, sources, _path, found = load(src)
        assert found is True
        assert effective['analysis']['report_format'] == 'markdown'
        assert sources['analysis.report_format'] == 'settings'

    def test_unwritten_keys_still_come_from_defaults(self, project):
        root, src = project
        write_settings(root, {'version': 1, 'analysis': {'report_format': 'markdown'}})
        effective, sources, _p, _f = load(src)
        assert effective['analysis']['output_dir'] == 'analysis'
        assert sources['analysis.output_dir'] == 'default'

    def test_a_corrupt_file_does_not_take_the_project_down(self, project):
        root, src = project
        path = root / '.chapterwise' / 'settings.json'
        path.parent.mkdir(parents=True)
        path.write_text('{ not json', encoding='utf-8')
        effective, _s, _p, found = load(src)
        assert found is False
        assert effective['analysis']['report_format'] == 'codex'


class TestWriting:
    def test_set_creates_the_file(self, project):
        root, src = project
        result = action_set({'path': str(src),
                             'updates': {'analysis': {'report_format': 'both'}}})
        assert result['written'] is True
        written = json.loads(Path(result['path']).read_text(encoding='utf-8'))
        assert written['analysis']['report_format'] == 'both'
        assert written['version'] == SETTINGS_VERSION

    def test_set_merges_rather_than_replaces(self, project):
        root, src = project
        action_set({'path': str(src), 'updates': {'analysis': {'output_dir': 'reports'}}})
        action_set({'path': str(src), 'updates': {'analysis': {'report_format': 'markdown'}}})
        effective, _s, _p, _f = load(src)
        assert effective['analysis']['output_dir'] == 'reports'
        assert effective['analysis']['report_format'] == 'markdown'

    def test_an_invalid_value_is_refused(self, project):
        _root, src = project
        with pytest.raises(ValueError, match='report_format'):
            action_set({'path': str(src),
                        'updates': {'analysis': {'report_format': 'pdf'}}})

    def test_a_refused_write_leaves_no_file(self, project):
        root, src = project
        with pytest.raises(ValueError):
            action_set({'path': str(src), 'updates': {'analysis': {'report_format': 'pdf'}}})
        assert not (root / '.chapterwise' / 'settings.json').exists()

    def test_empty_updates_are_refused(self, project):
        _root, src = project
        with pytest.raises(ValueError, match='updates'):
            action_set({'path': str(src), 'updates': {}})


class TestRecipeInheritance:
    """A choice saved by an earlier version must not be lost."""

    def _recipe(self, root: Path, payload: dict):
        path = root / '.chapterwise' / 'analysis-recipe' / 'recipe.yaml'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(payload), encoding='utf-8')

    def test_an_old_recipe_choice_is_honoured(self, project):
        root, src = project
        self._recipe(root, {'type': 'analysis', 'report_format': 'markdown'})
        effective, sources, _p, found = load(src)
        assert found is False                      # no settings.json yet
        assert effective['analysis']['report_format'] == 'markdown'
        assert sources['analysis.report_format'] == 'recipe'

    def test_settings_win_over_the_recipe(self, project):
        root, src = project
        self._recipe(root, {'type': 'analysis', 'report_format': 'markdown'})
        write_settings(root, {'version': 1, 'analysis': {'report_format': 'both'}})
        effective, sources, _p, _f = load(src)
        assert effective['analysis']['report_format'] == 'both'
        assert sources['analysis.report_format'] == 'settings'

    def test_writing_settings_carries_the_recipe_choice_forward(self, project):
        root, src = project
        self._recipe(root, {'type': 'analysis', 'report_format': 'markdown',
                            'depth': 'root,leaf'})
        action_set({'path': str(src), 'updates': {'analysis': {'output_dir': 'out'}}})
        effective, _s, _p, _f = load(src)
        assert effective['analysis']['report_format'] == 'markdown'
        assert effective['analysis']['depth'] == 'root,leaf'
        assert effective['analysis']['output_dir'] == 'out'


class TestAskOnce:
    """
    The first run offers to save; later runs must not ask again.

    `configured` is what the command checks — it lists the settings that came
    from somewhere other than the plugin defaults.
    """

    def test_nothing_configured_on_a_fresh_project(self, project):
        _root, src = project
        assert action_get({'path': str(src)})['configured'] == []

    def test_configured_after_a_save(self, project):
        _root, src = project
        action_set({'path': str(src), 'updates': {'analysis': {'report_format': 'both'}}})
        result = action_get({'path': str(src)})
        assert result['found'] is True
        assert 'analysis.report_format' in result['configured']


class TestResolve:
    def test_resolve_gives_the_analysis_path_everything_it_needs(self, project):
        root, src = project
        write_settings(root, {'version': 1,
                              'analysis': {'report_format': 'both', 'output_dir': '/out'}})
        result = action_resolve({'source': str(src)})
        assert result['report_format'] == 'both'
        assert result['output_dir'] == str(root / 'out')
        assert result['report'] is True

    def test_validate_flags_a_bad_format(self):
        assert validate({'analysis': {'report_format': 'pdf'}})

    def test_validate_passes_the_defaults(self):
        assert validate(DEFAULTS) == []


class TestCLI:
    def _run(self, action, payload):
        proc = subprocess.run([sys.executable, str(SCRIPT), action],
                              input=json.dumps(payload), capture_output=True, text=True)
        return proc, json.loads(proc.stdout)

    def test_get_returns_json_on_stdout(self, project):
        _root, src = project
        proc, out = self._run('get', {'path': str(src)})
        assert proc.returncode == 0 and out['settings']['analysis']['report_format'] == 'codex'

    def test_unknown_action_exits_nonzero(self):
        proc, out = self._run('frobnicate', {})
        assert proc.returncode == 1 and 'Unknown action' in out['error']

    def test_invalid_value_exits_nonzero(self, project):
        _root, src = project
        proc, out = self._run('set', {'path': str(src),
                                      'updates': {'analysis': {'report_format': 'pdf'}}})
        assert proc.returncode == 1 and 'report_format' in out['error']


class TestReportHonoursSettings:
    """The report generator reads settings without being told to."""

    @pytest.fixture
    def analyzed(self, project):
        from analysis_writer import add_analysis_result
        root, src = project
        add_analysis_result(src, 'summary', {'body': 'b', 'summary': 's'},
                            model='claude-opus-5')
        return root, src

    def test_default_is_codex_beside_the_file(self, analyzed):
        from analysis_report import build
        _root, src = analyzed
        result = build({'source': str(src), 'module': 'summary', 'generated': '2026-08-05'})
        out = Path(result['path'])
        assert out.suffix == '.yaml' and out.parent == src.parent / 'analysis'

    def test_settings_move_the_folder(self, analyzed):
        from analysis_report import build
        root, src = analyzed
        write_settings(root, {'version': 1, 'analysis': {'output_dir': '/reports'}})
        result = build({'source': str(src), 'module': 'summary', 'generated': '2026-08-05'})
        assert Path(result['path']).parent == root / 'reports'

    def test_settings_change_the_format(self, analyzed):
        from analysis_report import build
        root, src = analyzed
        write_settings(root, {'version': 1, 'analysis': {'report_format': 'markdown'}})
        result = build({'source': str(src), 'module': 'summary', 'generated': '2026-08-05'})
        assert Path(result['path']).suffix == '.md'

    def test_an_explicit_format_still_wins(self, analyzed):
        from analysis_report import build
        root, src = analyzed
        write_settings(root, {'version': 1, 'analysis': {'report_format': 'markdown'}})
        result = build({'source': str(src), 'module': 'summary',
                        'format': 'codex', 'generated': '2026-08-05'})
        assert Path(result['path']).name.endswith('.codex.yaml')

    def test_a_one_off_run_does_not_rewrite_settings(self, analyzed):
        from analysis_report import build
        root, src = analyzed
        build({'source': str(src), 'module': 'summary',
               'format': 'markdown', 'generated': '2026-08-05'})
        assert not (root / '.chapterwise' / 'settings.json').exists()


class TestEverySectionObeysSettings:
    """
    Settings belong to the project, so every route must honour them.

    v2.6.0 shipped the settings layer wired into the single-file route only.
    The course picker and the batch routes never exported a report at all, so
    `report_format` was universal in the script and not in the command — which
    is the kind of gap that reads as "configured" and behaves as "ignored".
    """

    COMMAND = (Path(__file__).parent.parent / 'plugins' / 'chapterwise' /
               'commands' / 'analysis.md')

    @pytest.fixture(scope='class')
    def doc(self):
        return self.COMMAND.read_text(encoding='utf-8')

    def test_a_shared_preflight_section_exists(self, doc):
        assert '## Section 0: Preflight' in doc
        for step in ('### Step 0a', '### Step 0b', '### Step 0c', '### Step 0d'):
            assert step in doc, step

    def test_the_course_picker_exports_and_offers(self, doc):
        section = doc.split('## Section 1:')[1].split('## Section 2:')[0]
        assert 'Step 0c' in section, 'course runs must export reports'
        assert 'Step 0d' in section, 'course runs must offer to save settings'

    def test_the_single_file_route_defers_to_preflight(self, doc):
        section = doc.split('## Section 2:')[1].split('## Section 3:')[0]
        assert 'Step 0a' in section and 'Step 0d' in section

    def test_the_batch_routes_obey_settings(self, doc):
        section = doc.split('## Section 6:')[1].split('## Section 7:')[0]
        for step in ('Step 0a', 'Step 0c', 'Step 0d'):
            assert step in section, f'batch runs must honour {step}'

    def test_the_plan_route_obeys_settings(self, doc):
        section = doc.split('## Section 5:')[1].split('## Section 6:')[0]
        assert 'Step 0c' in section and 'Step 0d' in section

    def test_the_save_offer_is_once_per_project(self, doc):
        assert 'Once per project, not once per file' in doc

    def test_the_documented_defaults_match_the_code(self, doc):
        """A settings block in the docs that drifts from DEFAULTS is a lie."""
        block = doc.split('```json', 1)[1].split('```', 1)[0]
        documented = json.loads(block)['analysis']
        assert documented == DEFAULTS['analysis']


class TestAtlasAndReaderSections:
    """
    One settings file, one section per command.

    The alternative — a config file per command — is how a project ends up with
    four places to look. `section` selects which command is asking.
    """

    def test_defaults_exist_for_every_section(self):
        assert set(DEFAULTS) == {'version', 'analysis', 'atlas', 'reader', 'research'}
        assert DEFAULTS['atlas']['output_dir'] == 'atlas'
        assert DEFAULTS['reader']['output_dir'] == 'reader'
        assert DEFAULTS['reader']['template'] == 'minimal'

    def test_resolve_defaults_to_analysis(self, project):
        _root, src = project
        assert action_resolve({'source': str(src)})['section'] == 'analysis'

    def test_atlas_output_is_project_relative_not_file_relative(self, project):
        """An atlas is built once for the project, not beside one chapter."""
        root, src = project
        result = action_resolve({'source': str(src), 'section': 'atlas'})
        assert result['output_dir'] == str(root / 'atlas')
        assert result['output_dir'] != str(src.parent / 'atlas')

    def test_reader_output_is_project_relative(self, project):
        root, src = project
        result = action_resolve({'source': str(src), 'section': 'reader'})
        assert result['output_dir'] == str(root / 'reader')

    def test_analysis_output_stays_beside_the_file(self, project):
        _root, src = project
        result = action_resolve({'source': str(src)})
        assert result['output_dir'] == str(src.parent / 'analysis')

    def test_a_section_only_reports_its_own_provenance(self, project):
        root, src = project
        write_settings(root, {'version': 1, 'reader': {'theme': 'dark'}})
        result = action_resolve({'source': str(src), 'section': 'reader'})
        assert result['configured'] == ['reader.theme']
        assert all(k.startswith('reader.') for k in result['sources'])

    def test_configuring_one_section_leaves_the_others_asking(self, project):
        root, src = project
        action_set({'path': str(src), 'updates': {'reader': {'theme': 'dark'}}})
        assert action_resolve({'source': str(src), 'section': 'reader'})['configured']
        assert action_resolve({'source': str(src), 'section': 'atlas'})['configured'] == []

    def test_reader_template_is_validated(self, project):
        _root, src = project
        with pytest.raises(ValueError, match='reader.template'):
            action_set({'path': str(src), 'updates': {'reader': {'template': 'fancy'}}})

    def test_reader_theme_is_validated(self, project):
        _root, src = project
        with pytest.raises(ValueError, match='reader.theme'):
            action_set({'path': str(src), 'updates': {'reader': {'theme': 'sepia'}}})

    def test_atlas_sections_round_trip(self, project):
        _root, src = project
        action_set({'path': str(src),
                    'updates': {'atlas': {'sections': ['characters', 'themes']}}})
        assert action_resolve({'source': str(src),
                               'section': 'atlas'})['sections'] == ['characters', 'themes']

    def test_an_unknown_section_is_refused(self, project):
        _root, src = project
        with pytest.raises(ValueError, match='Unknown section'):
            action_resolve({'source': str(src), 'section': 'kitchen'})

    def test_a_reader_recipe_from_an_older_version_is_honoured(self, project):
        root, src = project
        recipe = root / '.chapterwise' / 'reader-recipe' / 'recipe.yaml'
        recipe.parent.mkdir(parents=True)
        recipe.write_text(yaml.safe_dump(
            {'design': {'template': 'academic', 'theme': 'dark'}}), encoding='utf-8')
        result = action_resolve({'source': str(src), 'section': 'reader'})
        assert result['template'] == 'academic' and result['theme'] == 'dark'
        assert result['sources']['reader.template'] == 'recipe'

    def test_an_atlas_recipe_section_list_is_honoured(self, project):
        root, src = project
        recipe = root / '.chapterwise' / 'atlas-recipe' / 'recipe.yaml'
        recipe.parent.mkdir(parents=True)
        recipe.write_text(yaml.safe_dump({'sections': ['characters']}), encoding='utf-8')
        assert action_resolve({'source': str(src),
                               'section': 'atlas'})['sections'] == ['characters']

    def test_project_dir_honours_the_same_three_path_forms(self, project):
        from settings import resolve_project_dir
        root, src = project
        assert resolve_project_dir(src, 'atlas') == root / 'atlas'
        assert resolve_project_dir(src, '/build/atlas') == root / 'build' / 'atlas'
        assert resolve_project_dir(src, '~/atlases') == Path.home() / 'atlases'


class TestAtlasAndReaderCommandsObeySettings:
    """Every command that has a durable choice must read and offer to save it."""

    COMMANDS = Path(__file__).parent.parent / 'plugins' / 'chapterwise' / 'commands'

    @pytest.mark.parametrize('command,section', [('atlas', 'atlas'), ('reader', 'reader')])
    def test_the_command_reads_settings_before_asking(self, command, section):
        doc = (self.COMMANDS / f'{command}.md').read_text(encoding='utf-8')
        assert 'settings.py resolve' in doc, f'/{command} must read settings'
        assert f'"section": "{section}"' in doc

    @pytest.mark.parametrize('command', ['atlas', 'reader'])
    def test_the_command_offers_to_save(self, command):
        doc = (self.COMMANDS / f'{command}.md').read_text(encoding='utf-8')
        assert 'settings.py set' in doc, f'/{command} must offer to save settings'

    @pytest.mark.parametrize('command', ['atlas', 'reader'])
    def test_the_command_does_not_ask_what_is_configured(self, command):
        doc = (self.COMMANDS / f'{command}.md').read_text(encoding='utf-8')
        assert 'never ask' in doc.lower() or 'do not ask' in doc.lower()


class TestResearchSection:
    """
    Research had its own preference file in its own format.

    `.claude/chapterwise.local.md` was a second configuration surface — YAML
    frontmatter, different keys, different folder — for one command. It is
    retired; research is a section like everything else.
    """

    def test_research_has_defaults(self):
        assert DEFAULTS['research'] == {
            'output_dir': 'research',
            'format': 'codex-md',
            'depth': 'standard',
        }

    def test_every_section_uses_the_same_key_vocabulary(self):
        """One pattern: every section says output_dir, and depth means depth."""
        for section in ('analysis', 'atlas', 'reader', 'research'):
            assert 'output_dir' in DEFAULTS[section], section
        for section in ('analysis', 'research'):
            assert 'depth' in DEFAULTS[section], section

    def test_research_output_is_project_relative(self, project):
        root, src = project
        result = action_resolve({'source': str(src), 'section': 'research'})
        assert result['output_dir'] == str(root / 'research')

    def test_no_section_is_hidden_by_default(self):
        """
        Visible or hidden is the user's call, per section — a value, not a rule.

        Research used to default into `.chapterwise/` on the argument that it is
        an input rather than a deliverable. That reasoning is fine as a default
        *someone might choose*, and wrong as a shape only one section has.
        """
        for section in ('analysis', 'atlas', 'reader', 'research'):
            assert not DEFAULTS[section]['output_dir'].startswith('.chapterwise'), section

    def test_research_format_is_validated(self, project):
        _root, src = project
        with pytest.raises(ValueError, match='research.format'):
            action_set({'path': str(src), 'updates': {'research': {'format': 'pdf'}}})

    def test_research_depth_is_validated(self, project):
        _root, src = project
        with pytest.raises(ValueError, match='research.depth'):
            action_set({'path': str(src), 'updates': {'research': {'depth': 'shallow'}}})

    def test_research_round_trips(self, project):
        _root, src = project
        action_set({'path': str(src), 'updates': {'research': {'format': 'codex-json',
                                                              'depth': 'deep'}}})
        result = action_resolve({'source': str(src), 'section': 'research'})
        assert result['format'] == 'codex-json' and result['depth'] == 'deep'
        assert result['configured'] == ['research.format', 'research.depth']


class TestOneConfigurationSurface:
    """`.claude/chapterwise.local.md` is retired — one file, or it isn't consistent."""

    ROOT = Path(__file__).parent.parent

    def _text_files(self):
        for pattern in ('README.md', 'CLAUDE.md', 'plugins/chapterwise/commands/*.md',
                        'plugins/chapterwise/references/*.md', '.claude/context/*.md'):
            for path in self.ROOT.glob(pattern):
                yield path

    def test_no_command_or_doc_still_points_at_the_old_file(self):
        offenders = [str(p.relative_to(self.ROOT)) for p in self._text_files()
                     if 'chapterwise.local.md' in p.read_text(encoding='utf-8')
                     and 'v2.8.0' not in p.read_text(encoding='utf-8')]
        assert offenders == [], offenders

    def test_the_research_command_reads_settings(self):
        doc = (self.ROOT / 'plugins' / 'chapterwise' / 'commands' /
               'research.md').read_text(encoding='utf-8')
        assert 'settings.py resolve' in doc and '"section": "research"' in doc
        assert 'settings.py set' in doc

    def test_the_principles_reference_names_settings_json(self):
        doc = (self.ROOT / 'plugins' / 'chapterwise' / 'references' /
               'principles.md').read_text(encoding='utf-8')
        assert '.chapterwise/settings.json' in doc

    def test_every_documented_section_exists_in_code(self):
        doc = (self.ROOT / 'plugins' / 'chapterwise' / 'references' /
               'principles.md').read_text(encoding='utf-8')
        block = doc.split('```json', 1)[1].split('```', 1)[0]
        assert set(json.loads(block)) == set(DEFAULTS)


class TestOnePatternForOutput:
    """
    Every section that writes output has an `output_dir`, and they behave alike.

    v2.9.0 gave research a hidden default on the argument that it is an input
    rather than a deliverable. That is a reasonable thing for a *user* to
    choose and a bad thing for the tool to decide — it made one section a
    special case, which is exactly what a settings schema is supposed to avoid.
    """

    SECTIONS = ('analysis', 'atlas', 'reader', 'research')

    def test_every_section_names_the_key_the_same_way(self):
        assert all('output_dir' in DEFAULTS[s] for s in self.SECTIONS)
        assert not any('report_dir' in DEFAULTS[s] for s in self.SECTIONS)

    def test_every_section_resolves_paths_by_the_same_rules(self, project):
        root, src = project
        for section in self.SECTIONS:
            write_settings(root, {'version': 1, section: {'output_dir': '/shared'}})
            result = action_resolve({'source': str(src), 'section': section})
            assert result['output_dir'] == str(root / 'shared'), section

    def test_any_section_can_be_hidden_by_the_user(self, project):
        root, src = project
        for section in self.SECTIONS:
            write_settings(root, {'version': 1,
                                  section: {'output_dir': f'.chapterwise/{section}'}})
            result = action_resolve({'source': str(src), 'section': section})
            assert result['output_dir'].endswith(f'.chapterwise/{section}'), section

    def test_a_settings_file_written_before_the_rename_still_works(self, project):
        """`report_dir` was renamed to `output_dir`; do not silently ignore it."""
        root, src = project
        write_settings(root, {'version': 1, 'analysis': {'report_dir': 'old-reports'}})
        result = action_resolve({'source': str(src)})
        assert result['output_dir'] == str(src.parent / 'old-reports')

    def test_the_rename_is_normalised_on_the_next_write(self, project):
        root, src = project
        path = write_settings(root, {'version': 1, 'analysis': {'report_dir': 'kept'}})
        action_set({'path': str(src), 'updates': {'analysis': {'depth': 'leaf'}}})
        written = json.loads(path.read_text(encoding='utf-8'))
        assert written['analysis']['output_dir'] == 'kept'
        assert 'report_dir' not in written['analysis']

    def test_the_report_generator_honours_the_renamed_key(self, project):
        from analysis_report import build
        from analysis_writer import add_analysis_result
        root, src = project
        add_analysis_result(src, 'summary', {'body': 'b', 'summary': 's'},
                            model='claude-opus-5')
        write_settings(root, {'version': 1, 'analysis': {'output_dir': '/out'}})
        result = build({'source': str(src), 'module': 'summary', 'generated': '2026-08-05'})
        assert Path(result['path']).parent == root / 'out'


class TestHidingMeansTheSamePlaceEverywhere:
    """
    `.chapterwise/x` is the project's `.chapterwise/x`, whatever the section.

    Analysis output is file-relative, so the literal rule would put
    `.chapterwise/reports` *inside the chapter folder* — a second marker folder
    beside the manuscript, from the same string that means the project's
    `.chapterwise/` in every other section. One pattern has to mean one place.
    """

    def test_hiding_analysis_uses_the_projects_chapterwise(self, project):
        root, src = project
        write_settings(root, {'version': 1,
                              'analysis': {'output_dir': '.chapterwise/reports'}})
        result = action_resolve({'source': str(src)})
        assert result['output_dir'] == str(root / '.chapterwise' / 'reports')
        assert '.chapterwise' not in str(src.parent.relative_to(root))

    def test_the_same_string_means_the_same_place_in_every_section(self, project):
        root, src = project
        for section in ('analysis', 'atlas', 'reader', 'research'):
            write_settings(root, {'version': 1,
                                  section: {'output_dir': '.chapterwise/out'}})
            result = action_resolve({'source': str(src), 'section': section})
            assert result['output_dir'] == str(root / '.chapterwise' / 'out'), section

    def test_a_plain_relative_path_is_still_file_relative_for_analysis(self, project):
        root, src = project
        write_settings(root, {'version': 1, 'analysis': {'output_dir': 'notes'}})
        assert action_resolve({'source': str(src)})['output_dir'] == str(src.parent / 'notes')
